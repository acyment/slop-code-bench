#!/usr/bin/env python3
"""Standalone visible acceptance runner copied into C2 agent workspaces."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ScenarioFunc = Callable[[Path, Path], tuple[str | None, str | None]]


class AcceptanceError(AssertionError):
    """Base class for visible acceptance failures."""


class ScenarioFailureError(AcceptanceError):
    """Behavior was observable but did not match the scenario."""


class ProductError(AcceptanceError):
    """The product command failed or crashed."""


class HarnessError(AcceptanceError):
    """The acceptance harness could not run the scenario."""


def checkpoint_index(checkpoint_id: str) -> int:
    try:
        return int(checkpoint_id.rsplit("_", 1)[1])
    except (IndexError, ValueError) as exc:
        raise HarnessError(f"unsupported checkpoint id: {checkpoint_id}") from exc


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def run_command(
    command: list[str], *, cwd: Path, artifact_dir: Path, name: str
) -> dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    duration_ms = (time.perf_counter() - started) * 1000
    stdout_path = artifact_dir / f"{name}.stdout"
    stderr_path = artifact_dir / f"{name}.stderr"
    write_text(stdout_path, completed.stdout)
    write_text(stderr_path, completed.stderr)
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "duration_ms": duration_ms,
    }


def parse_json_lines(text: str) -> list[Any]:
    rows: list[Any] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ScenarioFailureError(
                f"stdout line {line_number} is not valid JSON"
            ) from exc
    return rows


def assert_exit_status(result: dict[str, Any], expected: int) -> None:
    if result["exit_code"] != expected:
        raise ProductError(
            f"expected exit status {expected}, got {result['exit_code']}"
        )


def assert_stderr_empty(result: dict[str, Any]) -> None:
    if result["stderr"].strip():
        raise ScenarioFailureError("stderr must be empty")


def assert_json_lines_equal(text: str, expected: list[dict[str, Any]]) -> None:
    actual = parse_json_lines(text)
    if actual != expected:
        raise ScenarioFailureError(
            "JSONL output did not match expected observable events"
        )


def assert_any_json_line(text: str, expected_subset: dict[str, Any]) -> None:
    for row in parse_json_lines(text):
        if not isinstance(row, dict):
            continue
        if all(row.get(key) == value for key, value in expected_subset.items()):
            return
    raise ScenarioFailureError(f"missing JSONL event subset: {expected_subset}")


def product_script(workspace: Path, filename: str) -> Path:
    path = workspace / filename
    if not path.is_file():
        raise HarnessError(f"missing product entry file: {path}")
    return path


def scenario_code_search_cp1(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "code_search.py")
    artifact_dir = artifact_root / "code_search" / "checkpoint_1"

    with TemporaryDirectory(prefix="code-search-acceptance-") as tmp:
        scratch = Path(tmp)
        write_text(
            scratch / "rules.json",
            """
[
  {"id":"plaintext","kind":"exact","pattern":"plaintext:"},
  {"id":"regex_rule","kind":"regex","pattern":"^hello.*$","regex_flags":["i","m"]}
]
""".strip(),
        )
        write_text(
            scratch / "repo" / "A.py",
            "\n".join(
                [
                    'print("hello world")',
                    'print("plaintext")',
                    'print("plaintext:")',
                    'print("""',
                    "hello",
                    "hello world",
                    '""")',
                    "",
                ]
            ),
        )
        result = run_command(
            [
                sys.executable,
                str(script_path),
                str(scratch / "repo"),
                "--rules",
                str(scratch / "rules.json"),
            ],
            cwd=workspace,
            artifact_dir=artifact_dir,
            name="code_search_cp001",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    assert_json_lines_equal(
        result["stdout"],
        [
            {
                "rule_id": "plaintext",
                "file": "A.py",
                "language": "python",
                "start": {"line": 3, "col": 8},
                "end": {"line": 3, "col": 18},
                "match": "plaintext:",
            },
            {
                "rule_id": "regex_rule",
                "file": "A.py",
                "language": "python",
                "start": {"line": 5, "col": 1},
                "end": {"line": 5, "col": 6},
                "match": "hello",
            },
            {
                "rule_id": "regex_rule",
                "file": "A.py",
                "language": "python",
                "start": {"line": 6, "col": 1},
                "end": {"line": 6, "col": 12},
                "match": "hello world",
            },
        ],
    )
    return result["stdout_path"], result["stderr_path"]


def scenario_file_backup_cp1(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "backup_scheduler.py")
    artifact_dir = artifact_root / "file_backup" / "checkpoint_1"

    with TemporaryDirectory(prefix="file-backup-acceptance-") as tmp:
        scratch = Path(tmp)
        files_root = scratch / "files"
        for rel_path in [
            "A/B/C/D.py",
            "A/B/E.bin",
            "A/I.py",
            "M.py",
            "O.md",
        ]:
            write_text(files_root / rel_path, "")
        write_text(
            scratch / "schedule.yaml",
            """
version: 1
timezone: UTC
jobs:
  - id: job-root
    source: mount://
    exclude: ["A/*", "*.py", "**/*.bin"]
    when:
      kind: daily
      at: "03:30"
  - id: job-subdir
    source: mount://A/B
    exclude: ["*.py", "**/*.bin"]
    when:
      kind: daily
      at: "03:30"
""".strip(),
        )
        result = run_command(
            [
                sys.executable,
                str(script_path),
                "--now",
                "2025-09-10T03:30:00Z",
                "--schedule",
                str(scratch / "schedule.yaml"),
                "--duration",
                "1",
                "--mount",
                str(files_root),
            ],
            cwd=workspace,
            artifact_dir=artifact_dir,
            name="file_backup_cp001",
        )

    assert_exit_status(result, 0)
    events = parse_json_lines(result["stdout"])
    if not events or not isinstance(events[0], dict):
        raise ScenarioFailureError("expected at least one JSONL event")
    if events[0].get("event") != "SCHEDULE_PARSED":
        raise ScenarioFailureError("first event must be SCHEDULE_PARSED")
    assert_any_json_line(result["stdout"], {"event": "JOB_ELIGIBLE", "job_id": "job-root"})
    assert_any_json_line(result["stdout"], {"event": "JOB_ELIGIBLE", "job_id": "job-subdir"})
    assert_any_json_line(result["stdout"], {"event": "JOB_COMPLETED", "job_id": "job-root"})
    assert_any_json_line(result["stdout"], {"event": "JOB_COMPLETED", "job_id": "job-subdir"})
    return result["stdout_path"], result["stderr_path"]


SCENARIO_SPECS: list[dict[str, Any]] = [
    {
        "problem_id": "code_search",
        "checkpoint_index": 1,
        "scenario_id": "code_search.cp001.workspace-cli-search",
        "scenario_name": "Workspace product searches Python exact and regex rules",
        "tags": ["problem:code_search", "checkpoint:1", "core", "positive", "cli"],
        "scenario_func": scenario_code_search_cp1,
    },
    {
        "problem_id": "file_backup",
        "checkpoint_index": 1,
        "scenario_id": "file_backup.cp001.workspace-cli-events",
        "scenario_name": "Workspace product emits due-job JSONL event history",
        "tags": ["problem:file_backup", "checkpoint:1", "core", "positive", "cli"],
        "scenario_func": scenario_file_backup_cp1,
    },
]


def selected_scenarios(
    *, problem_id: str, checkpoint_id: str, through_checkpoint: bool
) -> list[dict[str, Any]]:
    target_index = checkpoint_index(checkpoint_id)
    result = []
    for spec in SCENARIO_SPECS:
        if spec["problem_id"] != problem_id:
            continue
        spec_index = int(spec["checkpoint_index"])
        if spec_index == target_index or (
            through_checkpoint and spec_index <= target_index
        ):
            result.append(spec)
    return result


def run_scenario(
    *,
    run_id: str,
    workspace: Path,
    artifact_root: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    status = "passed"
    failure_type: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    try:
        stdout_path, stderr_path = spec["scenario_func"](workspace, artifact_root)
    except ScenarioFailureError:
        status = "failed"
        failure_type = "scenario_failure"
    except ProductError:
        status = "failed"
        failure_type = "product_error"
    except HarnessError:
        status = "error"
        failure_type = "harness_error"
    except Exception:  # noqa: BLE001
        status = "error"
        failure_type = "harness_error"
    duration_ms = (time.perf_counter() - started) * 1000
    checkpoint = f"checkpoint_{int(spec['checkpoint_index'])}"
    return {
        "schema_version": 1,
        "run_id": run_id,
        "problem_id": spec["problem_id"],
        "checkpoint_id": checkpoint,
        "scenario_id": spec["scenario_id"],
        "feature_path": (
            f".scbench_acceptance/features/{spec['problem_id']}/"
            f"checkpoint_{int(spec['checkpoint_index']):03d}.feature"
        ),
        "scenario_name": spec["scenario_name"],
        "tags": spec["tags"],
        "status": status,
        "failure_type": failure_type,
        "duration_ms": duration_ms,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path())
    parser.add_argument("--problem-id", required=False)
    parser.add_argument("--checkpoint-id", required=False)
    parser.add_argument("--through-checkpoint", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(".scbench_acceptance/results"))
    parser.add_argument("--run-id", default="visible-acceptance")
    parser.add_argument("--list-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_json:
        payload = [
            {
                key: value
                for key, value in spec.items()
                if key != "scenario_func"
            }
            for spec in SCENARIO_SPECS
        ]
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if not args.problem_id or not args.checkpoint_id:
        raise HarnessError("--problem-id and --checkpoint-id are required")

    workspace = args.workspace.resolve()
    output_dir = args.output_dir.resolve()
    artifact_root = output_dir / "artifacts"
    specs = selected_scenarios(
        problem_id=args.problem_id,
        checkpoint_id=args.checkpoint_id,
        through_checkpoint=args.through_checkpoint,
    )
    if not specs:
        row = {
            "schema_version": 1,
            "run_id": args.run_id,
            "problem_id": args.problem_id,
            "checkpoint_id": args.checkpoint_id,
            "scenario_id": f"{args.problem_id}.{args.checkpoint_id}.no-visible-coverage",
            "feature_path": None,
            "scenario_name": "No locked visible acceptance coverage exists for this checkpoint",
            "tags": ["coverage:missing"],
            "status": "skipped",
            "failure_type": None,
            "duration_ms": 0.0,
            "stdout_path": None,
            "stderr_path": None,
        }
        write_jsonl(output_dir / "scenarios.jsonl", [row])
        print(f"skipped: {row['scenario_id']}")
        return 0

    results = [
        run_scenario(
            run_id=args.run_id,
            workspace=workspace,
            artifact_root=artifact_root,
            spec=spec,
        )
        for spec in specs
    ]
    write_jsonl(output_dir / "scenarios.jsonl", results)
    for result in results:
        print(f"{result['status']}: {result['scenario_id']}")
    return 0 if all(result["status"] == "passed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
