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


def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


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


def assert_no_json_line(text: str, forbidden_subset: dict[str, Any]) -> None:
    for row in parse_json_lines(text):
        if not isinstance(row, dict):
            continue
        if all(row.get(key) == value for key, value in forbidden_subset.items()):
            raise ScenarioFailureError(
                f"unexpected JSONL event subset: {forbidden_subset}"
            )


def assert_json_line_count(text: str, expected_count: int) -> list[dict[str, Any]]:
    rows = parse_json_lines(text)
    dict_rows = [row for row in rows if isinstance(row, dict)]
    if len(dict_rows) != expected_count:
        raise ScenarioFailureError(
            f"expected {expected_count} JSONL rows, got {len(dict_rows)}"
        )
    return dict_rows


def assert_output_sorted_by_file_position(rows: list[dict[str, Any]]) -> None:
    sort_key = lambda row: (
        row.get("file"),
        row.get("start", {}).get("line"),
        row.get("start", {}).get("col"),
        row.get("rule_id"),
    )
    if rows != sorted(rows, key=sort_key):
        raise ScenarioFailureError("JSONL matches must be sorted by file and position")


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


def scenario_code_search_cp2(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "code_search.py")
    artifact_dir = artifact_root / "code_search" / "checkpoint_2"

    with TemporaryDirectory(prefix="code-search-acceptance-") as tmp:
        scratch = Path(tmp)
        write_text(
            scratch / "rules.json",
            json.dumps(
                [
                    {"id": "todo", "kind": "exact", "pattern": "TODO:"},
                    {
                        "id": "printf",
                        "kind": "regex",
                        "pattern": r"\bprintf\s*\(",
                        "languages": ["cpp"],
                    },
                    {
                        "id": "console-log",
                        "kind": "regex",
                        "pattern": r"console\.log\s*\(",
                        "languages": ["javascript"],
                    },
                ]
            ),
        )
        write_text(scratch / "repo" / "main.py", "# TODO: python work\n")
        write_text(
            scratch / "repo" / "app.js",
            """
function run() {
  console.log("ready");
}
""".lstrip(),
        )
        write_text(
            scratch / "repo" / "src" / "engine.cpp",
            """
void run() {
  printf("ready");
}
""".lstrip(),
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
            name="code_search_cp002",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    rows = assert_json_line_count(result["stdout"], 3)
    assert_output_sorted_by_file_position(rows)
    assert_any_json_line(
        result["stdout"],
        {
            "rule_id": "console-log",
            "file": "app.js",
            "language": "javascript",
            "match": "console.log(",
        },
    )
    assert_any_json_line(
        result["stdout"],
        {
            "rule_id": "printf",
            "file": "src/engine.cpp",
            "language": "cpp",
            "match": "printf(",
        },
    )
    assert_any_json_line(
        result["stdout"],
        {
            "rule_id": "todo",
            "file": "main.py",
            "language": "python",
            "match": "TODO:",
        },
    )
    return result["stdout_path"], result["stderr_path"]


def scenario_code_search_cp3(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "code_search.py")
    artifact_dir = artifact_root / "code_search" / "checkpoint_3"

    with TemporaryDirectory(prefix="code-search-acceptance-") as tmp:
        scratch = Path(tmp)
        write_text(
            scratch / "rules.json",
            """
[
  {"id":"py-print","kind":"pattern","pattern":"print($GREETING)","languages":["python"]},
  {"id":"same-tag","kind":"pattern","pattern":"console.log($TAG, $TAG)","languages":["javascript"]}
]
""".strip(),
        )
        write_text(
            scratch / "repo" / "main.py",
            """
def run():
    print("hello")
    print(greeting())
""".lstrip(),
        )
        write_text(
            scratch / "repo" / "web.js",
            """
console.log("user", "user");
console.log("user", id);
""".lstrip(),
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
            name="code_search_cp003",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    rows = parse_json_lines(result["stdout"])
    py_prints = [
        row for row in rows if isinstance(row, dict) and row.get("rule_id") == "py-print"
    ]
    if len(py_prints) != 2:
        raise ScenarioFailureError("expected two py-print pattern matches")
    py_matches = {str(row.get("match")) for row in py_prints}
    if py_matches != {'print("hello")', "print(greeting())"}:
        raise ScenarioFailureError("py-print pattern matches do not match examples")
    for row in py_prints:
        captures = row.get("captures")
        if not isinstance(captures, dict) or "$GREETING" not in captures:
            raise ScenarioFailureError("py-print matches must include $GREETING captures")

    same_tag_rows = [
        row for row in rows if isinstance(row, dict) and row.get("rule_id") == "same-tag"
    ]
    if len(same_tag_rows) != 1:
        raise ScenarioFailureError("expected one same-tag match")
    same_tag = same_tag_rows[0]
    if same_tag.get("match") != 'console.log("user", "user")':
        raise ScenarioFailureError("same-tag match must require identical arguments")
    captures = same_tag.get("captures")
    if not isinstance(captures, dict):
        raise ScenarioFailureError("same-tag match must include captures")
    tag_capture = captures.get("$TAG")
    if not isinstance(tag_capture, dict) or tag_capture.get("text") != '"user"':
        raise ScenarioFailureError("same-tag $TAG capture must bind to the repeated text")
    ranges = tag_capture.get("ranges")
    if not isinstance(ranges, list) or len(ranges) != 2:
        raise ScenarioFailureError("same-tag $TAG capture must include both ranges")
    assert_no_json_line(
        result["stdout"],
        {"rule_id": "same-tag", "match": 'console.log("user", id)'},
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
    destination: backup://
    exclude: ["A/*", "*.py", "**/*.bin"]
    when:
      kind: daily
      at: "03:30"
  - id: job-subdir
    source: mount://A/B
    destination: backup://
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


def run_backup_scheduler(
    *,
    workspace: Path,
    script_path: Path,
    scratch: Path,
    artifact_dir: Path,
    name: str,
    schedule: Path,
    mount: Path,
    backup: Path | None = None,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(script_path),
        "--now",
        "2025-09-10T03:30:00Z",
        "--schedule",
        str(schedule),
        "--duration",
        "1",
        "--mount",
        str(mount),
    ]
    if backup is not None:
        command.extend(["--backup", str(backup)])
    return run_command(
        command,
        cwd=workspace,
        artifact_dir=artifact_dir,
        name=name,
    )


def scenario_file_backup_cp2(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "backup_scheduler.py")
    artifact_dir = artifact_root / "file_backup" / "checkpoint_2"

    with TemporaryDirectory(prefix="file-backup-acceptance-") as tmp:
        scratch = Path(tmp)
        files_root = scratch / "files"
        write_text(files_root / "docs" / "a.txt", "alpha")
        write_text(files_root / "docs" / "b.md", "beta")
        write_text(
            scratch / "full.yaml",
            """
version: 1
timezone: UTC
jobs:
  - id: docs-full
    source: mount://
    destination: backup://
    when: {kind: daily, at: "03:30"}
    strategy: {kind: full}
""".strip(),
        )
        full_result = run_backup_scheduler(
            workspace=workspace,
            script_path=script_path,
            scratch=scratch,
            artifact_dir=artifact_dir,
            name="file_backup_cp002_full",
            schedule=scratch / "full.yaml",
            mount=files_root,
        )
        write_text(
            scratch / "verify.yaml",
            """
version: 1
timezone: UTC
jobs:
  - id: docs-verify
    source: mount://
    destination: backup://
    when: {kind: daily, at: "03:30"}
    strategy: {kind: verify}
""".strip(),
        )
        verify_result = run_backup_scheduler(
            workspace=workspace,
            script_path=script_path,
            scratch=scratch,
            artifact_dir=artifact_dir,
            name="file_backup_cp002_verify",
            schedule=scratch / "verify.yaml",
            mount=files_root,
        )

        pack_root = scratch / "pack-files"
        for name, size in {
            "file1": 28,
            "file2": 4,
            "file3": 31,
            "file4": 33,
            "file5": 10,
        }.items():
            write_bytes(pack_root / name, b"x" * size)
        write_text(
            scratch / "pack.yaml",
            """
version: 1
timezone: UTC
jobs:
  - id: complete-archive
    source: mount://
    destination: backup://
    when: {kind: daily, at: "03:30"}
    strategy:
      kind: pack
      options:
        max_pack_bytes: 32
""".strip(),
        )
        pack_result = run_backup_scheduler(
            workspace=workspace,
            script_path=script_path,
            scratch=scratch,
            artifact_dir=artifact_dir,
            name="file_backup_cp002_pack",
            schedule=scratch / "pack.yaml",
            mount=pack_root,
        )

    for result in [full_result, verify_result, pack_result]:
        assert_exit_status(result, 0)
    assert_any_json_line(
        full_result["stdout"],
        {"event": "STRATEGY_SELECTED", "job_id": "docs-full", "kind": "full"},
    )
    assert_any_json_line(
        full_result["stdout"],
        {
            "event": "FILE_BACKED_UP",
            "job_id": "docs-full",
            "path": "docs/a.txt",
            "size": 5,
        },
    )
    assert_any_json_line(
        full_result["stdout"],
        {
            "event": "JOB_COMPLETED",
            "job_id": "docs-full",
            "selected": 2,
            "total_size": 9,
        },
    )
    assert_any_json_line(
        verify_result["stdout"],
        {"event": "STRATEGY_SELECTED", "job_id": "docs-verify", "kind": "verify"},
    )
    assert_any_json_line(
        verify_result["stdout"],
        {
            "event": "FILE_VERIFIED",
            "job_id": "docs-verify",
            "path": "docs/b.md",
            "size": 4,
        },
    )
    for subset in [
        {"event": "FILE_PACKED", "job_id": "complete-archive", "path": "file1", "pack_id": 1},
        {"event": "FILE_PACKED", "job_id": "complete-archive", "path": "file2", "pack_id": 1},
        {"event": "PACK_CREATED", "job_id": "complete-archive", "name": "pack-1.tar", "size": 32},
        {"event": "FILE_PACKED", "job_id": "complete-archive", "path": "file4", "pack_id": 3},
        {"event": "PACK_CREATED", "job_id": "complete-archive", "name": "pack-4.tar", "size": 10},
        {"event": "JOB_COMPLETED", "job_id": "complete-archive", "packs": 4, "total_size": 106},
    ]:
        assert_any_json_line(pack_result["stdout"], subset)
    return pack_result["stdout_path"], pack_result["stderr_path"]


def assert_file_exists(path: Path) -> None:
    if not path.is_file():
        raise ScenarioFailureError(f"expected file to exist: {path}")


def scenario_file_backup_cp3(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "backup_scheduler.py")
    artifact_dir = artifact_root / "file_backup" / "checkpoint_3"

    with TemporaryDirectory(prefix="file-backup-acceptance-") as tmp:
        scratch = Path(tmp)
        files_root = scratch / "files"
        write_text(files_root / "A" / "K.html", "<h1>first</h1>")
        write_text(files_root / "A" / "L.md", "changed")
        write_text(files_root / "A" / "I.py", "print('excluded')\n")
        write_text(files_root / "O.md", "stable")
        write_text(
            scratch / "schedule.yaml",
            """
version: 1
timezone: UTC
jobs:
  - id: daily-docs
    source: mount://
    destination: backup://
    exclude: ["**/*.py", "**/*.bin"]
    when: {kind: daily, at: "03:30"}
    strategy: {kind: full}
""".strip(),
        )
        backup_root = scratch / "backup"
        write_text(backup_root / "daily-docs" / "A" / "K.html", "<h1>first</h1>")
        write_text(backup_root / "daily-docs" / "A" / "L.md", "initial")
        write_text(backup_root / "daily-docs" / "O.md", "stable")
        result = run_backup_scheduler(
            workspace=workspace,
            script_path=script_path,
            scratch=scratch,
            artifact_dir=artifact_dir,
            name="file_backup_cp003_incremental",
            schedule=scratch / "schedule.yaml",
            mount=files_root,
            backup=backup_root,
        )

    assert_exit_status(result, 0)
    assert_any_json_line(
        result["stdout"],
        {"event": "DEST_STATE_LOADED", "job_id": "daily-docs", "files_total": 3},
    )
    assert_any_json_line(
        result["stdout"],
        {
            "event": "FILE_SKIPPED_UNCHANGED",
            "job_id": "daily-docs",
            "path": "A/K.html",
        },
    )
    assert_any_json_line(
        result["stdout"],
        {
            "event": "FILE_BACKED_UP",
            "job_id": "daily-docs",
            "path": "A/L.md",
        },
    )
    assert_any_json_line(
        result["stdout"],
        {
            "event": "FILE_SKIPPED_UNCHANGED",
            "job_id": "daily-docs",
            "path": "O.md",
        },
    )
    assert_any_json_line(
        result["stdout"],
        {
            "event": "JOB_COMPLETED",
            "job_id": "daily-docs",
            "files_skipped_unchanged": 2,
            "dest_state_files": 3,
        },
    )
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
        "problem_id": "code_search",
        "checkpoint_index": 2,
        "scenario_id": "code_search.cp002.multi-language-filters",
        "scenario_name": "Workspace product searches Python, JavaScript, and C++ with language filters",
        "tags": ["problem:code_search", "checkpoint:2", "core", "positive", "cli"],
        "scenario_func": scenario_code_search_cp2,
    },
    {
        "problem_id": "code_search",
        "checkpoint_index": 3,
        "scenario_id": "code_search.cp003.pattern-metavariables",
        "scenario_name": "Workspace product matches pattern rules with metavariable captures",
        "tags": ["problem:code_search", "checkpoint:3", "core", "positive", "cli"],
        "scenario_func": scenario_code_search_cp3,
    },
    {
        "problem_id": "file_backup",
        "checkpoint_index": 1,
        "scenario_id": "file_backup.cp001.workspace-cli-events",
        "scenario_name": "Workspace product emits due-job JSONL event history",
        "tags": ["problem:file_backup", "checkpoint:1", "core", "positive", "cli"],
        "scenario_func": scenario_file_backup_cp1,
    },
    {
        "problem_id": "file_backup",
        "checkpoint_index": 2,
        "scenario_id": "file_backup.cp002.strategy-events",
        "scenario_name": "Workspace product emits strategy events for full, verify, and pack backups",
        "tags": ["problem:file_backup", "checkpoint:2", "core", "positive", "cli", "file_io"],
        "scenario_func": scenario_file_backup_cp2,
    },
    {
        "problem_id": "file_backup",
        "checkpoint_index": 3,
        "scenario_id": "file_backup.cp003.incremental-destination",
        "scenario_name": "Workspace product writes destinations and skips unchanged full backups",
        "tags": ["problem:file_backup", "checkpoint:3", "core", "positive", "cli", "file_io"],
        "scenario_func": scenario_file_backup_cp3,
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
