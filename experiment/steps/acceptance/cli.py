"""CLI acceptance helpers for SCBench visible scenarios."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path

from experiment.steps.acceptance.results import ProductError
from experiment.steps.acceptance.results import ScenarioFailureError


class JsonLinesError(ScenarioFailureError):
    """JSON Lines output was malformed or semantically unexpected."""


class ExitStatusError(ProductError):
    """Command returned an unexpected exit status."""


class CommandTimeoutError(ProductError):
    """Command exceeded its timeout."""


class CommandResult:
    def __init__(
        self,
        *,
        args: list[str],
        cwd: Path,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: float,
        stdout_path: Path,
        stderr_path: Path,
    ) -> None:
        self.args = args
        self.cwd = cwd
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def run_command(
    args: list[str],
    *,
    cwd: Path,
    artifact_dir: Path,
    name: str,
    timeout_s: float = 10.0,
    env: Mapping[str, str] | None = None,
    stdin: str | None = None,
) -> CommandResult:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = artifact_dir / f"{name}.stdout.txt"
    stderr_path = artifact_dir / f"{name}.stderr.txt"
    started = time.perf_counter()
    try:
        completed = subprocess.run(  # noqa: S603
            args,
            cwd=cwd,
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
            env=None if env is None else dict(env),
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = (time.perf_counter() - started) * 1000
        stdout = _coerce_text(exc.stdout)
        stderr = _coerce_text(exc.stderr)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        raise CommandTimeoutError(
            f"command timed out after {timeout_s:.1f}s: {' '.join(args)}"
        ) from exc

    duration_ms = (time.perf_counter() - started) * 1000
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return CommandResult(
        args=args,
        cwd=cwd,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_ms=duration_ms,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )


def assert_exit_status(result: CommandResult, expected: int) -> None:
    if result.exit_code != expected:
        raise ExitStatusError(
            f"expected exit status {expected}, got {result.exit_code}; "
            f"stderr artifact: {result.stderr_path}"
        )


def assert_stdout_empty(result: CommandResult) -> None:
    if result.stdout:
        raise ScenarioFailureError(f"expected empty stdout, got {result.stdout!r}")


def assert_stderr_empty(result: CommandResult) -> None:
    if result.stderr:
        raise ScenarioFailureError(f"expected empty stderr, got {result.stderr!r}")


def parse_json_lines(text: str) -> list[object]:
    rows: list[object] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise JsonLinesError(f"line {line_no} is not valid JSON") from exc
    return rows


def assert_json_lines_equal(actual_text: str, expected: list[object]) -> None:
    actual = parse_json_lines(actual_text)
    if actual != expected:
        raise JsonLinesError(f"JSON Lines mismatch: expected {expected!r}, got {actual!r}")


def assert_any_json_line(actual_text: str, expected_subset: dict[str, object]) -> None:
    for row in parse_json_lines(actual_text):
        if isinstance(row, dict) and _contains_subset(row, expected_subset):
            return
    raise JsonLinesError(f"no JSONL row contained subset {expected_subset!r}")


def _contains_subset(row: dict[str, object], expected_subset: dict[str, object]) -> bool:
    return all(row.get(key) == value for key, value in expected_subset.items())


def _coerce_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
