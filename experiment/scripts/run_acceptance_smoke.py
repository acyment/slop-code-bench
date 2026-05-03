#!/usr/bin/env python3
"""Run cheap acceptance harness smoke scenarios against reference solutions."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiment.steps.acceptance.api import start_python_server
from experiment.steps.acceptance.cli import assert_any_json_line
from experiment.steps.acceptance.cli import assert_exit_status
from experiment.steps.acceptance.cli import assert_json_lines_equal
from experiment.steps.acceptance.cli import assert_stderr_empty
from experiment.steps.acceptance.cli import parse_json_lines
from experiment.steps.acceptance.cli import run_command
from experiment.steps.acceptance.cli import write_text
from experiment.steps.acceptance.results import FailureType
from experiment.steps.acceptance.results import HarnessError
from experiment.steps.acceptance.results import ProductError
from experiment.steps.acceptance.results import ScenarioFailureError
from experiment.steps.acceptance.results import ScenarioResult
from experiment.steps.acceptance.results import ScenarioStatus
from experiment.steps.acceptance.results import write_jsonl

ScenarioFunc = Callable[[Path, Path], tuple[str | None, str | None]]


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def checkpoint_id(index: int) -> str:
    return f"checkpoint_{index}"


def feature_path(problem_id: str, checkpoint_index: int) -> str:
    return (
        Path("experiment")
        / "features"
        / problem_id
        / f"checkpoint_{checkpoint_index:03d}.feature"
    ).as_posix()


def run_scenario(
    *,
    run_id: str,
    problem_id: str,
    checkpoint_index: int,
    scenario_id: str,
    scenario_name: str,
    tags: list[str],
    scenario_func: ScenarioFunc,
    problems_root: Path,
    artifact_root: Path,
) -> ScenarioResult:
    started = time.perf_counter()
    stdout_path: str | None = None
    stderr_path: str | None = None
    status: ScenarioStatus = "passed"
    failure_type: FailureType | None = None

    try:
        stdout_path, stderr_path = scenario_func(problems_root, artifact_root)
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
    return ScenarioResult(
        schema_version=1,
        run_id=run_id,
        problem_id=problem_id,
        checkpoint_id=checkpoint_id(checkpoint_index),
        scenario_id=scenario_id,
        feature_path=feature_path(problem_id, checkpoint_index),
        scenario_name=scenario_name,
        tags=tags,
        status=status,
        failure_type=failure_type,
        duration_ms=duration_ms,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )


def smoke_code_search_checkpoint_1(
    problems_root: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    solution_dir = problems_root / "code_search" / "solutions" / "checkpoint_1"
    script_path = solution_dir / "code_search.py"
    artifact_dir = artifact_root / "code_search" / "checkpoint_1"

    with TemporaryDirectory(prefix="code-search-smoke-") as tmp:
        workspace = Path(tmp)
        write_text(
            workspace / "rules.json",
            """
[
  {"id":"plaintext","kind":"exact","pattern":"plaintext:"},
  {"id":"regex_rule","kind":"regex","pattern":"^hello.*$","regex_flags":["i","m"]}
]
""".strip(),
        )
        write_text(
            workspace / "repo" / "A.py",
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
                str(workspace / "repo"),
                "--rules",
                str(workspace / "rules.json"),
            ],
            cwd=solution_dir,
            artifact_dir=artifact_dir,
            name="code_search_cp001",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    assert_json_lines_equal(
        result.stdout,
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
    return str(result.stdout_path), str(result.stderr_path)


def smoke_file_backup_checkpoint_1(
    problems_root: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    solution_dir = problems_root / "file_backup" / "solutions" / "checkpoint_1"
    script_path = solution_dir / "backup_scheduler.py"
    artifact_dir = artifact_root / "file_backup" / "checkpoint_1"

    with TemporaryDirectory(prefix="file-backup-smoke-") as tmp:
        workspace = Path(tmp)
        files_root = workspace / "files"
        for rel_path in [
            "A/B/C/D.py",
            "A/B/E.bin",
            "A/I.py",
            "M.py",
            "O.md",
        ]:
            write_text(files_root / rel_path, "")
        write_text(
            workspace / "schedule.yaml",
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
                str(workspace / "schedule.yaml"),
                "--duration",
                "1",
                "--mount",
                str(files_root),
            ],
            cwd=solution_dir,
            artifact_dir=artifact_dir,
            name="file_backup_cp001",
        )

    assert_exit_status(result, 0)
    events = parse_json_lines(result.stdout)
    if not events or not isinstance(events[0], dict):
        raise ScenarioFailureError("expected at least one JSONL event")
    if events[0].get("event") != "SCHEDULE_PARSED":
        raise ScenarioFailureError("first event must be SCHEDULE_PARSED")
    assert_any_json_line(result.stdout, {"event": "JOB_ELIGIBLE", "job_id": "job-root"})
    assert_any_json_line(result.stdout, {"event": "JOB_ELIGIBLE", "job_id": "job-subdir"})
    assert_any_json_line(result.stdout, {"event": "JOB_COMPLETED", "job_id": "job-root"})
    assert_any_json_line(result.stdout, {"event": "JOB_COMPLETED", "job_id": "job-subdir"})
    return str(result.stdout_path), str(result.stderr_path)


def smoke_textdrop_checkpoint_1(
    problems_root: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    solution_dir = problems_root / "textdrop" / "solutions" / "checkpoint_1"
    script_path = solution_dir / "textdrop.py"
    artifact_dir = artifact_root / "textdrop" / "checkpoint_1"

    with start_python_server(
        script=script_path,
        cwd=solution_dir,
        artifact_dir=artifact_dir,
        name="textdrop_cp001",
    ) as server:
        health = server.request("GET", "/health")
        if health.status_code != 200:
            raise ProductError(f"expected health 200, got {health.status_code}")
        if health.json().get("status") != "active":
            raise ScenarioFailureError("health JSON must report active status")

        submit = server.request(
            "POST",
            "/submit",
            data={"content": "Hello, world!", "mode": ""},
        )
        if submit.status_code != 302:
            raise ProductError(f"expected submit 302, got {submit.status_code}")
        location = submit.headers.get("Location", "")
        if not location.startswith("/n/"):
            raise ScenarioFailureError("submit response must include note Location")

        raw = server.request("GET", f"{location}/text")
        if raw.status_code != 200:
            raise ProductError(f"expected raw text 200, got {raw.status_code}")
        if raw.text != "Hello, world!":
            raise ScenarioFailureError(
                "raw text response did not preserve submitted content"
            )

        view = server.request("GET", location)
        if view.status_code != 200:
            raise ProductError(f"expected note view 200, got {view.status_code}")
        if "<pre><code>Hello, world!</code></pre>" not in view.text:
            raise ScenarioFailureError("note view did not include escaped text block")

        return str(server.stdout_path), str(server.stderr_path)


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--problems-root",
        type=Path,
        default=repo_root.parent / "scb-problems",
        help="Path to the pinned scb-problems checkout.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "experiment" / "results" / "acceptance_smoke",
        help="Directory for smoke artifacts and scenarios.jsonl.",
    )
    parser.add_argument(
        "--run-id",
        default="acceptance-smoke",
        help="Run id to write into scenario result records.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    problems_root = args.problems_root.resolve()
    output_dir = args.output_dir.resolve()
    artifact_root = output_dir / "artifacts"

    scenario_specs = [
        {
            "problem_id": "code_search",
            "checkpoint_index": 1,
            "scenario_id": "code_search.cp001.reference-cli-search",
            "scenario_name": "Reference solution searches Python exact and regex rules",
            "tags": ["problem:code_search", "checkpoint:1", "core", "positive", "cli"],
            "scenario_func": smoke_code_search_checkpoint_1,
        },
        {
            "problem_id": "file_backup",
            "checkpoint_index": 1,
            "scenario_id": "file_backup.cp001.reference-cli-events",
            "scenario_name": "Reference solution emits due-job JSONL event history",
            "tags": ["problem:file_backup", "checkpoint:1", "core", "positive", "cli"],
            "scenario_func": smoke_file_backup_checkpoint_1,
        },
        {
            "problem_id": "textdrop",
            "checkpoint_index": 1,
            "scenario_id": "textdrop.cp001.reference-api-note",
            "scenario_name": "Reference service creates and serves a plain text note",
            "tags": ["problem:textdrop", "checkpoint:1", "core", "positive", "api"],
            "scenario_func": smoke_textdrop_checkpoint_1,
        },
    ]

    results = [
        run_scenario(
            run_id=args.run_id,
            problem_id=str(spec["problem_id"]),
            checkpoint_index=int(spec["checkpoint_index"]),
            scenario_id=str(spec["scenario_id"]),
            scenario_name=str(spec["scenario_name"]),
            tags=list(spec["tags"]),
            scenario_func=spec["scenario_func"],
            problems_root=problems_root,
            artifact_root=artifact_root,
        )
        for spec in scenario_specs
    ]

    output_path = output_dir / "scenarios.jsonl"
    write_jsonl(output_path, results)
    for result in results:
        print(f"{result.status}: {result.scenario_id}")
    print(f"wrote: {output_path}")
    return 0 if all(result.status == "passed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
