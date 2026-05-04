#!/usr/bin/env python3
"""Standalone visible acceptance runner copied into C2 agent workspaces."""

from __future__ import annotations

import argparse
import ast
import configparser
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml

ScenarioFunc = Callable[[Path, Path], tuple[str | None, str | None]]

ENTRYPOINT_TEMPLATE_BY_SCRIPT = {
    "code_search.py": "scbench_uv_run_code_search",
    "backup_scheduler.py": "scbench_uv_run_backup_scheduler",
    "migrate.py": "scbench_uv_run_migrate_configs",
}

LAST_COMMAND_RESULT: dict[str, Any] | None = None


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


def _literal_ast(value: Any) -> ast.expr:
    if isinstance(value, str | int | float | bool) or value is None:
        return ast.Constant(value=value)
    if isinstance(value, list):
        return ast.List(
            elts=[_literal_ast(item) for item in value],
            ctx=ast.Load(),
        )
    raise HarnessError(f"cannot serialize scoped runner literal: {value!r}")


def _scenario_specs_ast(specs: list[dict[str, Any]]) -> ast.List:
    spec_nodes: list[ast.Dict] = []
    for spec in specs:
        keys: list[ast.expr | None] = []
        values: list[ast.expr] = []
        for key, value in spec.items():
            keys.append(ast.Constant(value=key))
            if key == "scenario_func":
                values.append(ast.Name(id=value.__name__, ctx=ast.Load()))
            else:
                values.append(_literal_ast(value))
        spec_nodes.append(ast.Dict(keys=keys, values=values))
    return ast.List(elts=spec_nodes, ctx=ast.Load())


def write_scoped_runner(
    *,
    source_path: Path,
    output_path: Path,
    problem_id: str,
    checkpoint_id: str,
    through_checkpoint: bool,
) -> None:
    allowed_specs = selected_scenarios(
        problem_id=problem_id,
        checkpoint_id=checkpoint_id,
        through_checkpoint=through_checkpoint,
    )
    allowed_func_names = {
        spec["scenario_func"].__name__
        for spec in allowed_specs
    }
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    class ScopeTransformer(ast.NodeTransformer):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST | None:  # noqa: N802
            if node.name.startswith("scenario_") and node.name not in allowed_func_names:
                return None
            return self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST:  # noqa: N802
            if isinstance(node.target, ast.Name) and node.target.id == "SCENARIO_SPECS":
                node.value = _scenario_specs_ast(allowed_specs)
                return node
            return self.generic_visit(node)

    scoped = ScopeTransformer().visit(tree)
    ast.fix_missing_locations(scoped)
    output = (
        "#!/usr/bin/env python3\n"
        "# Generated checkpoint-scoped visible acceptance runner.\n"
        "# Future checkpoint scenarios are intentionally omitted.\n"
        f"# Scope: problem={problem_id} checkpoint={checkpoint_id} through={through_checkpoint}\n"
        + ast.unparse(scoped)
        + "\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")


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


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def benchmark_equivalent_command(
    command: list[str], *, cwd: Path
) -> tuple[list[str], str, str | None]:
    if len(command) < 2 or command[0] != sys.executable:
        return command, "custom", "not a product-script invocation"

    script_path = Path(command[1])
    script_name = script_path.name
    template_id = ENTRYPOINT_TEMPLATE_BY_SCRIPT.get(script_name)
    if template_id is None:
        return command, "custom", "product script has no benchmark entrypoint template"

    workspace_script = (cwd / script_name).resolve()
    try:
        resolved_script = script_path.resolve()
    except OSError:
        resolved_script = script_path
    if resolved_script != workspace_script:
        return command, "custom", "product script is not the workspace entrypoint"

    return ["uv", "run", script_name, *command[2:]], template_id, None


def run_command(
    command: list[str], *, cwd: Path, artifact_dir: Path, name: str
) -> dict[str, Any]:
    global LAST_COMMAND_RESULT
    artifact_dir.mkdir(parents=True, exist_ok=True)
    effective_command, command_template_id, waiver_reason = benchmark_equivalent_command(
        command,
        cwd=cwd,
    )
    env = None
    environment_overrides: dict[str, str | None] = {}
    if command_template_id.startswith("scbench_uv_run_"):
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)
        environment_overrides["VIRTUAL_ENV"] = None
    started = time.perf_counter()
    completed = subprocess.run(  # noqa: S603
        effective_command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    duration_ms = (time.perf_counter() - started) * 1000
    stdout_path = artifact_dir / f"{name}.stdout"
    stderr_path = artifact_dir / f"{name}.stderr"
    command_path = artifact_dir / f"{name}.command.json"
    command_log_path = artifact_dir / "commands.jsonl"
    write_text(stdout_path, completed.stdout)
    write_text(stderr_path, completed.stderr)
    command_metadata = {
        "schema_version": 1,
        "name": name,
        "command": effective_command,
        "original_command": command,
        "cwd": cwd.as_posix(),
        "runner_python": sys.executable,
        "uv_executable": shutil.which("uv"),
        "environment_overrides": environment_overrides,
        "command_template_id": command_template_id,
        "entrypoint_waiver_reason": waiver_reason,
        "exit_code": completed.returncode,
        "duration_ms": duration_ms,
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
    }
    write_text(command_path, json.dumps(command_metadata, indent=2, sort_keys=True) + "\n")
    append_jsonl(command_log_path, command_metadata)
    result = {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "command_path": command_path.as_posix(),
        "command_log_path": command_log_path.as_posix(),
        "command": effective_command,
        "original_command": command,
        "command_template_id": command_template_id,
        "entrypoint_waiver_reason": waiver_reason,
        "duration_ms": duration_ms,
    }
    LAST_COMMAND_RESULT = result
    return result


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


def assert_json_lines_match_subsets(
    text: str,
    expected_subsets: list[dict[str, Any]],
) -> None:
    actual = parse_json_lines(text)
    if len(actual) != len(expected_subsets):
        raise ScenarioFailureError(
            f"JSONL line count mismatch: got {len(actual)}, expected {len(expected_subsets)}"
        )
    for index, (row, subset) in enumerate(zip(actual, expected_subsets, strict=True)):
        if not isinstance(row, dict):
            raise ScenarioFailureError(f"JSONL line {index} is not an object")
        for key, expected_value in subset.items():
            if row.get(key) != expected_value:
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


def assert_no_json_events(text: str, forbidden_events: set[str]) -> None:
    for row in parse_json_lines(text):
        if not isinstance(row, dict):
            continue
        if row.get("event") in forbidden_events:
            raise ScenarioFailureError(
                f"unexpected JSONL event: {row.get('event')}"
            )


def assert_json_line_count(text: str, expected_count: int) -> list[dict[str, Any]]:
    rows = parse_json_lines(text)
    dict_rows = [row for row in rows if isinstance(row, dict)]
    if len(dict_rows) != expected_count:
        raise ScenarioFailureError(
            f"expected {expected_count} JSONL rows, got {len(dict_rows)}"
        )
    return dict_rows


def assert_stdout_empty(result: dict[str, Any]) -> None:
    if result["stdout"].strip():
        raise ScenarioFailureError("stdout must be empty")


def assert_path_value(data: Any, path: str, expected: Any) -> None:
    current = data
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            raise ScenarioFailureError(f"missing path {path}")
        current = current[segment]
    if current != expected:
        raise ScenarioFailureError(
            f"path {path} expected {expected!r}, got {current!r}"
        )


def load_json_config(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml_config(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_toml_config(path: Path) -> Any:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_ini_config(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return parser


def assert_file_updated_event(
    stdout: str,
    *,
    file_path: str,
    rules_applied: list[str] | None = None,
) -> dict[str, Any]:
    for row in parse_json_lines(stdout):
        if not isinstance(row, dict):
            continue
        if row.get("event") != "file_updated" or row.get("file") != file_path:
            continue
        if rules_applied is not None and row.get("rules_applied") != rules_applied:
            raise ScenarioFailureError(
                f"file_updated event for {file_path} had wrong rules_applied"
            )
        return row
    raise ScenarioFailureError(f"missing file_updated event for {file_path}")


def assert_no_file_updated_event(stdout: str, *, file_path: str) -> None:
    for row in parse_json_lines(stdout):
        if (
            isinstance(row, dict)
            and row.get("event") == "file_updated"
            and row.get("file") == file_path
        ):
            raise ScenarioFailureError(f"unexpected file_updated event for {file_path}")


def rows_for_rule(rows: list[Any], rule_id: str) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if isinstance(row, dict) and row.get("rule_id") == rule_id
    ]


def assert_capture_text(row: dict[str, Any], name: str, expected: str) -> None:
    captures = row.get("captures")
    if not isinstance(captures, dict):
        raise ScenarioFailureError(f"match must include captures for {name}")
    capture = captures.get(name)
    if not isinstance(capture, dict):
        raise ScenarioFailureError(f"match must include capture {name}")
    if capture.get("text") != expected:
        raise ScenarioFailureError(
            f"capture {name} text mismatch: expected {expected!r}, got {capture.get('text')!r}"
        )
    ranges = capture.get("ranges")
    if not isinstance(ranges, list) or not ranges:
        raise ScenarioFailureError(f"capture {name} must include at least one range")


def assert_output_sorted_by_file_position(rows: list[dict[str, Any]]) -> None:
    def sort_key(row: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
        return (
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
    assert_json_lines_match_subsets(
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


def scenario_code_search_cp3_nested_expression(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "code_search.py")
    artifact_dir = artifact_root / "code_search" / "checkpoint_3"

    with TemporaryDirectory(prefix="code-search-acceptance-") as tmp:
        scratch = Path(tmp)
        write_text(
            scratch / "rules.json",
            json.dumps(
                [
                    {
                        "id": "func-call",
                        "kind": "pattern",
                        "pattern": "$X($Y)",
                        "languages": ["python"],
                    }
                ]
            ),
        )
        write_text(scratch / "repo" / "nested.py", "f(g(h(z)))\n")
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
            name="code_search_cp003_nested_expression",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    rows = assert_json_line_count(result["stdout"], 1)
    row = rows[0]
    expected_subset = {
        "rule_id": "func-call",
        "file": "nested.py",
        "language": "python",
        "start": {"line": 1, "col": 1},
        "end": {"line": 1, "col": 11},
        "match": "f(g(h(z)))",
    }
    for key, expected_value in expected_subset.items():
        if row.get(key) != expected_value:
            raise ScenarioFailureError("nested-expression match did not match expected output")
    assert_capture_text(row, "$X", "f")
    assert_capture_text(row, "$Y", "g(h(z))")
    return result["stdout_path"], result["stderr_path"]


def scenario_code_search_cp3_pattern_edge_semantics(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "code_search.py")
    artifact_dir = artifact_root / "code_search" / "checkpoint_3"

    with TemporaryDirectory(prefix="code-search-acceptance-") as tmp:
        scratch = Path(tmp)
        write_text(
            scratch / "rules.json",
            json.dumps(
                [
                    {
                        "id": "optional-item",
                        "kind": "pattern",
                        "pattern": "[$X?]",
                        "languages": ["python"],
                    },
                    {
                        "id": "dollar-var",
                        "kind": "pattern",
                        "pattern": "$$price = $VAL",
                        "languages": ["python"],
                    },
                    {
                        "id": "js-func",
                        "kind": "pattern",
                        "pattern": "function $NAME($ARG) {}",
                        "languages": ["javascript"],
                    },
                    {
                        "id": "var-decl",
                        "kind": "pattern",
                        "pattern": "let $VAR = $VAL;",
                        "languages": ["javascript"],
                    },
                ]
            ),
        )
        write_text(
            scratch / "repo" / "items.py",
            "[]\n[value]\n$price = 100\n",
        )
        write_text(
            scratch / "repo" / "a.js",
            "let a = 1;\nlet b = 2;\nfunction greet(name) {}\n",
        )
        write_text(scratch / "repo" / "z.js", "let z = 3;\n")
        write_text(
            scratch / "repo" / "not_javascript.py",
            "function wrong(arg) {}\n",
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
            name="code_search_cp003_pattern_edge_semantics",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    rows = assert_json_line_count(result["stdout"], 7)
    assert_output_sorted_by_file_position(rows)

    optional_rows = rows_for_rule(rows, "optional-item")
    if [row.get("match") for row in optional_rows] != ["[]", "[value]"]:
        raise ScenarioFailureError("optional metavariable matches are missing")
    if "captures" in optional_rows[0]:
        raise ScenarioFailureError(
            "absent optional metavariable must omit the captures field"
        )
    assert_capture_text(optional_rows[1], "$X", "value")

    dollar_rows = rows_for_rule(rows, "dollar-var")
    if len(dollar_rows) != 1 or dollar_rows[0].get("match") != "$price = 100":
        raise ScenarioFailureError("literal dollar pattern did not match expected source")
    assert_capture_text(dollar_rows[0], "$VAL", "100")

    js_func_rows = rows_for_rule(rows, "js-func")
    if len(js_func_rows) != 1:
        raise ScenarioFailureError("expected one JavaScript function match")
    js_func = js_func_rows[0]
    if js_func.get("file") != "a.js" or js_func.get("match") != "function greet(name) {}":
        raise ScenarioFailureError("JavaScript function pattern matched the wrong file or text")
    captures = js_func.get("captures")
    if not isinstance(captures, dict) or list(captures) != ["$ARG", "$NAME"]:
        raise ScenarioFailureError("captures must be serialized in lexicographic order")
    assert_capture_text(js_func, "$NAME", "greet")
    assert_capture_text(js_func, "$ARG", "name")
    assert_no_json_line(result["stdout"], {"rule_id": "js-func", "file": "not_javascript.py"})

    var_rows = rows_for_rule(rows, "var-decl")
    observed_var_matches = [
        (row.get("file"), row.get("match"))
        for row in var_rows
    ]
    if observed_var_matches != [
        ("a.js", "let a = 1;"),
        ("a.js", "let b = 2;"),
        ("z.js", "let z = 3;"),
    ]:
        raise ScenarioFailureError("JavaScript variable matches are not deterministically ordered")
    return result["stdout_path"], result["stderr_path"]


def scenario_code_search_cp3_multiline_python_captures(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "code_search.py")
    artifact_dir = artifact_root / "code_search" / "checkpoint_3"

    with TemporaryDirectory(prefix="code-search-acceptance-") as tmp:
        scratch = Path(tmp)
        write_text(
            scratch / "rules.json",
            json.dumps(
                [
                    {
                        "id": "if-return",
                        "kind": "pattern",
                        "pattern": "if $COND:\n        return $VALUE",
                        "languages": ["python"],
                    }
                ]
            ),
        )
        write_text(
            scratch / "repo" / "app.py",
            (
                "def choose(flag):\n"
                "    if flag:\n"
                "        return result\n"
                "    return None\n"
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
            name="code_search_cp003_multiline_python_captures",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    rows = assert_json_line_count(result["stdout"], 1)
    row = rows[0]
    expected_subset = {
        "rule_id": "if-return",
        "file": "app.py",
        "language": "python",
        "start": {"line": 2, "col": 5},
        "end": {"line": 3, "col": 22},
        "match": "if flag:\n        return result",
    }
    for key, expected_value in expected_subset.items():
        if row.get(key) != expected_value:
            raise ScenarioFailureError("multiline Python pattern did not match expected output")
    assert_capture_text(row, "$COND", "flag")
    assert_capture_text(row, "$VALUE", "result")
    return result["stdout_path"], result["stderr_path"]


def scenario_code_search_cp3_expression_capture_boundaries(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "code_search.py")
    artifact_dir = artifact_root / "code_search" / "checkpoint_3"

    with TemporaryDirectory(prefix="code-search-acceptance-") as tmp:
        scratch = Path(tmp)
        write_text(
            scratch / "rules.json",
            json.dumps(
                [
                    {
                        "id": "py-print-value",
                        "kind": "pattern",
                        "pattern": "print($VALUE)",
                        "languages": ["python"],
                    },
                    {
                        "id": "cpp-return-value",
                        "kind": "pattern",
                        "pattern": "return $VALUE;",
                        "languages": ["cpp"],
                    },
                    {
                        "id": "js-label-value",
                        "kind": "pattern",
                        "pattern": "const label = $VALUE;",
                        "languages": ["javascript"],
                    },
                ]
            ),
        )
        write_text(
            scratch / "repo" / "calc.py",
            'print(99)\nprint(total + tax)\n',
        )
        write_text(
            scratch / "repo" / "engine.cpp",
            "int run() {\n  return total + fee;\n}\n",
        )
        write_text(
            scratch / "repo" / "labels.js",
            'const label = "alpha\\nbeta";\nconst label = `row1\nrow2`;\n',
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
            name="code_search_cp003_expression_capture_boundaries",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    rows = assert_json_line_count(result["stdout"], 5)
    assert_output_sorted_by_file_position(rows)

    py_rows = rows_for_rule(rows, "py-print-value")
    if [row.get("match") for row in py_rows] != ["print(99)", "print(total + tax)"]:
        raise ScenarioFailureError("Python print pattern must capture both simple and expression values")
    assert_capture_text(py_rows[0], "$VALUE", "99")
    assert_capture_text(py_rows[1], "$VALUE", "total + tax")

    cpp_rows = rows_for_rule(rows, "cpp-return-value")
    if len(cpp_rows) != 1 or cpp_rows[0].get("match") != "return total + fee;":
        raise ScenarioFailureError("C++ return pattern must capture the whole return expression")
    assert_capture_text(cpp_rows[0], "$VALUE", "total + fee")

    js_rows = rows_for_rule(rows, "js-label-value")
    if [row.get("match") for row in js_rows] != [
        'const label = "alpha\\nbeta";',
        "const label = `row1\nrow2`;",
    ]:
        raise ScenarioFailureError("JavaScript string captures must preserve quoted/backtick boundaries")
    assert_capture_text(js_rows[0], "$VALUE", '"alpha\\nbeta"')
    assert_capture_text(js_rows[1], "$VALUE", "`row1\nrow2`")
    return result["stdout_path"], result["stderr_path"]


def scenario_code_search_cp3_comprehension_and_cpp_blocks(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "code_search.py")
    artifact_dir = artifact_root / "code_search" / "checkpoint_3"

    with TemporaryDirectory(prefix="code-search-acceptance-") as tmp:
        scratch = Path(tmp)
        write_text(
            scratch / "rules.json",
            json.dumps(
                [
                    {
                        "id": "list-comp",
                        "kind": "pattern",
                        "pattern": "[$EXPR for $ITEM in $ITER]",
                        "languages": ["python"],
                    },
                    {
                        "id": "guard-return",
                        "kind": "pattern",
                        "pattern": "if ($COND) {\n    return $VALUE;\n  }",
                        "languages": ["cpp"],
                    },
                ]
            ),
        )
        write_text(
            scratch / "repo" / "views.py",
            (
                "names = [user.name for user in users]\n"
                "ids = [row.id for row in rows]\n"
            ),
        )
        write_text(
            scratch / "repo" / "guards.cpp",
            (
                "int choose(int count) {\n"
                "  if (count > 1) {\n"
                "    return count + 1;\n"
                "  }\n"
                "  if (count) {\n"
                "    return count;\n"
                "  }\n"
                "  return 0;\n"
                "}\n"
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
            name="code_search_cp003_comprehension_and_cpp_blocks",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    rows = assert_json_line_count(result["stdout"], 4)
    assert_output_sorted_by_file_position(rows)

    comp_rows = rows_for_rule(rows, "list-comp")
    if [row.get("match") for row in comp_rows] != [
        "[user.name for user in users]",
        "[row.id for row in rows]",
    ]:
        raise ScenarioFailureError("list comprehension patterns must capture both examples")
    assert_capture_text(comp_rows[0], "$EXPR", "user.name")
    assert_capture_text(comp_rows[0], "$ITEM", "user")
    assert_capture_text(comp_rows[0], "$ITER", "users")
    assert_capture_text(comp_rows[1], "$EXPR", "row.id")
    assert_capture_text(comp_rows[1], "$ITEM", "row")
    assert_capture_text(comp_rows[1], "$ITER", "rows")

    block_rows = rows_for_rule(rows, "guard-return")
    if [row.get("match") for row in block_rows] != [
        "if (count > 1) {\n    return count + 1;\n  }",
        "if (count) {\n    return count;\n  }",
    ]:
        raise ScenarioFailureError("multiline C++ block patterns must capture both guarded returns")
    assert_capture_text(block_rows[0], "$COND", "count > 1")
    assert_capture_text(block_rows[0], "$VALUE", "count + 1")
    assert_capture_text(block_rows[1], "$COND", "count")
    assert_capture_text(block_rows[1], "$VALUE", "count")
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
            "A/F/G.bin",
            "A/F/H.py",
            "A/I.py",
            "A/J.bin",
            "A/K.html",
            "A/L.md",
            "M.py",
            "N.py",
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
    assert_stderr_empty(result)
    assert_json_lines_match_subsets(
        result["stdout"],
        [
            {"event": "SCHEDULE_PARSED", "timezone": "UTC", "jobs_total": 2},
            {
                "event": "JOB_ELIGIBLE",
                "job_id": "job-root",
                "kind": "daily",
                "now_local": "2025-09-10T03:30:00Z",
            },
            {"event": "JOB_STARTED", "job_id": "job-root", "exclude_count": 3},
            {"event": "FILE_SELECTED", "job_id": "job-root", "path": "A/B/C/D.py"},
            {
                "event": "FILE_EXCLUDED",
                "job_id": "job-root",
                "path": "A/B/E.bin",
                "pattern": "**/*.bin",
            },
            {
                "event": "FILE_EXCLUDED",
                "job_id": "job-root",
                "path": "A/F/G.bin",
                "pattern": "**/*.bin",
            },
            {"event": "FILE_SELECTED", "job_id": "job-root", "path": "A/F/H.py"},
            {
                "event": "FILE_EXCLUDED",
                "job_id": "job-root",
                "path": "A/I.py",
                "pattern": "A/*",
            },
            {
                "event": "FILE_EXCLUDED",
                "job_id": "job-root",
                "path": "A/J.bin",
                "pattern": "A/*",
            },
            {
                "event": "FILE_EXCLUDED",
                "job_id": "job-root",
                "path": "A/K.html",
                "pattern": "A/*",
            },
            {
                "event": "FILE_EXCLUDED",
                "job_id": "job-root",
                "path": "A/L.md",
                "pattern": "A/*",
            },
            {
                "event": "FILE_EXCLUDED",
                "job_id": "job-root",
                "path": "M.py",
                "pattern": "*.py",
            },
            {
                "event": "FILE_EXCLUDED",
                "job_id": "job-root",
                "path": "N.py",
                "pattern": "*.py",
            },
            {"event": "FILE_SELECTED", "job_id": "job-root", "path": "O.md"},
            {
                "event": "JOB_COMPLETED",
                "job_id": "job-root",
                "selected": 3,
                "excluded": 8,
            },
            {
                "event": "JOB_ELIGIBLE",
                "job_id": "job-subdir",
                "kind": "daily",
                "now_local": "2025-09-10T03:30:00Z",
            },
            {"event": "JOB_STARTED", "job_id": "job-subdir", "exclude_count": 2},
            {"event": "FILE_SELECTED", "job_id": "job-subdir", "path": "C/D.py"},
            {
                "event": "FILE_EXCLUDED",
                "job_id": "job-subdir",
                "path": "E.bin",
                "pattern": "**/*.bin",
            },
            {
                "event": "JOB_COMPLETED",
                "job_id": "job-subdir",
                "selected": 1,
                "excluded": 1,
            },
        ],
    )
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
    now: str = "2025-09-10T03:30:00Z",
    duration: str = "1",
    backup: Path | None = None,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(script_path),
        "--now",
        now,
        "--schedule",
        str(schedule),
        "--duration",
        duration,
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


def assert_due_backup_run(
    result: dict[str, Any],
    *,
    job_id: str,
    kind: str,
) -> None:
    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    rows = parse_json_lines(result["stdout"])
    if not rows or not isinstance(rows[0], dict) or rows[0].get("event") != "SCHEDULE_PARSED":
        raise ScenarioFailureError("backup output must start with SCHEDULE_PARSED")
    assert_any_json_line(
        result["stdout"],
        {"event": "JOB_ELIGIBLE", "job_id": job_id, "kind": kind},
    )
    assert_any_json_line(
        result["stdout"],
        {"event": "JOB_STARTED", "job_id": job_id},
    )
    assert_any_json_line(
        result["stdout"],
        {"event": "FILE_SELECTED", "job_id": job_id, "path": "data.txt"},
    )
    assert_any_json_line(
        result["stdout"],
        {"event": "JOB_COMPLETED", "job_id": job_id, "selected": 1, "excluded": 0},
    )


def scenario_file_backup_cp1_due_windows(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "backup_scheduler.py")
    artifact_dir = artifact_root / "file_backup" / "checkpoint_1"

    with TemporaryDirectory(prefix="file-backup-acceptance-") as tmp:
        scratch = Path(tmp)
        files_root = scratch / "files"
        write_text(files_root / "data.txt", "data")
        cases = [
            {
                "name": "daily_exact_default_fields",
                "job_id": "daily-exact",
                "kind": "daily",
                "when": 'kind: daily\n      at: "03:30"',
                "now": "2025-09-10T03:30:00Z",
                "duration": "0",
            },
            {
                "name": "daily_inclusive_next_day",
                "job_id": "daily-window",
                "kind": "daily",
                "when": 'kind: daily\n      at: "03:30"',
                "now": "2025-09-10T03:31:00Z",
                "duration": "24",
            },
            {
                "name": "weekly_block_days",
                "job_id": "weekly-wed",
                "kind": "weekly",
                "when": 'kind: weekly\n      at: "03:30"\n      days:\n        - Wed',
                "now": "2025-09-10T03:30:00Z",
                "duration": "0",
            },
            {
                "name": "once_exact",
                "job_id": "once-exact",
                "kind": "once",
                "when": 'kind: once\n      at: "2025-09-10T03:30:00"',
                "now": "2025-09-10T03:30:00Z",
                "duration": "0",
            },
        ]
        last_result: dict[str, Any] | None = None
        for case in cases:
            schedule_path = scratch / f"{case['name']}.yaml"
            write_text(
                schedule_path,
                f"""
version: 1
jobs:
  - id: {case["job_id"]}
    source: mount://
    destination: backup://
    when:
      {case["when"]}
""".strip(),
            )
            last_result = run_backup_scheduler(
                workspace=workspace,
                script_path=script_path,
                scratch=scratch,
                artifact_dir=artifact_dir,
                name=f"file_backup_cp001_{case['name']}",
                schedule=schedule_path,
                mount=files_root,
                now=str(case["now"]),
                duration=str(case["duration"]),
            )
            assert_due_backup_run(
                last_result,
                job_id=str(case["job_id"]),
                kind=str(case["kind"]),
            )

    if last_result is None:
        raise HarnessError("no due-window cases executed")
    return last_result["stdout_path"], last_result["stderr_path"]


def scenario_file_backup_cp1_recurring_triggers(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "backup_scheduler.py")
    artifact_dir = artifact_root / "file_backup" / "checkpoint_1"

    with TemporaryDirectory(prefix="file-backup-acceptance-") as tmp:
        scratch = Path(tmp)
        files_root = scratch / "files"
        write_text(files_root / "data.txt", "data")
        schedule_path = scratch / "schedule.yaml"
        write_text(
            schedule_path,
            """
version: 1
timezone: UTC
jobs:
  - id: daily-repeat
    source: mount://
    destination: backup://
    when:
      kind: daily
      at: "03:30"
""".strip(),
        )
        result = run_backup_scheduler(
            workspace=workspace,
            script_path=script_path,
            scratch=scratch,
            artifact_dir=artifact_dir,
            name="file_backup_cp001_recurring_triggers",
            schedule=schedule_path,
            mount=files_root,
            now="2025-09-08T03:30:00Z",
            duration="48",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    rows = parse_json_lines(result["stdout"])
    due_times = [
        row.get("now_local")
        for row in rows
        if isinstance(row, dict)
        and row.get("event") == "JOB_ELIGIBLE"
        and row.get("job_id") == "daily-repeat"
    ]
    if due_times != [
        "2025-09-08T03:30:00Z",
        "2025-09-09T03:30:00Z",
        "2025-09-10T03:30:00Z",
    ]:
        raise ScenarioFailureError("daily recurring job must run once per trigger in window")
    completions = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("event") == "JOB_COMPLETED"
        and row.get("job_id") == "daily-repeat"
    ]
    if len(completions) != 3:
        raise ScenarioFailureError("daily recurring job must complete once per trigger")
    for row in completions:
        if row.get("selected") != 1 or row.get("excluded") != 0:
            raise ScenarioFailureError("recurring run completion counts are incorrect")
    return result["stdout_path"], result["stderr_path"]


def scenario_file_backup_cp1_disabled_jobs(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "backup_scheduler.py")
    artifact_dir = artifact_root / "file_backup" / "checkpoint_1"

    with TemporaryDirectory(prefix="file-backup-acceptance-") as tmp:
        scratch = Path(tmp)
        files_root = scratch / "files"
        write_text(files_root / "data.txt", "data")
        schedule_path = scratch / "schedule.yaml"
        write_text(
            schedule_path,
            """
version: 1
timezone: UTC
jobs:
  - id: disabled
    enabled: false
    source: mount://
    destination: backup://
    when:
      kind: daily
      at: "03:30"
""".strip(),
        )
        result = run_backup_scheduler(
            workspace=workspace,
            script_path=script_path,
            scratch=scratch,
            artifact_dir=artifact_dir,
            name="file_backup_cp001_disabled_jobs",
            schedule=schedule_path,
            mount=files_root,
            now="2025-09-10T03:30:00Z",
            duration="1",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    assert_json_lines_match_subsets(
        result["stdout"],
        [{"event": "SCHEDULE_PARSED", "timezone": "UTC", "jobs_total": 1}],
    )
    assert_no_json_events(
        result["stdout"],
        {"JOB_ELIGIBLE", "JOB_STARTED", "FILE_SELECTED", "FILE_EXCLUDED", "JOB_COMPLETED"},
    )
    return result["stdout_path"], result["stderr_path"]


def scenario_file_backup_cp1_block_lists_defaults_globs(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "backup_scheduler.py")
    artifact_dir = artifact_root / "file_backup" / "checkpoint_1"

    with TemporaryDirectory(prefix="file-backup-acceptance-") as tmp:
        scratch = Path(tmp)
        files_root = scratch / "files"
        for rel_path, content in [
            ("data1.txt", "one"),
            ("data10.txt", "ten"),
            ("keep.md", "keep"),
            ("report1.log", "one"),
            ("report3.log", "three"),
            ("tmp/cache.bin", "cache"),
        ]:
            write_text(files_root / rel_path, content)
        schedule_path = scratch / "schedule.yaml"
        write_text(
            schedule_path,
            """
version: 1
jobs:
  - id: defaults-and-globs
    source: mount://
    destination: backup://
    exclude:
      - tmp/**
      - data?.txt
      - report[12].log
    when:
      kind: daily
      at: "03:30"
""".strip(),
        )
        result = run_backup_scheduler(
            workspace=workspace,
            script_path=script_path,
            scratch=scratch,
            artifact_dir=artifact_dir,
            name="file_backup_cp001_block_lists_defaults_globs",
            schedule=schedule_path,
            mount=files_root,
            now="2025-09-10T03:30:00Z",
            duration="0",
        )

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    assert_json_lines_match_subsets(
        result["stdout"],
        [
            {"event": "SCHEDULE_PARSED", "timezone": "UTC", "jobs_total": 1},
            {
                "event": "JOB_ELIGIBLE",
                "job_id": "defaults-and-globs",
                "kind": "daily",
            },
            {"event": "JOB_STARTED", "job_id": "defaults-and-globs", "exclude_count": 3},
            {
                "event": "FILE_EXCLUDED",
                "job_id": "defaults-and-globs",
                "path": "data1.txt",
                "pattern": "data?.txt",
            },
            {
                "event": "FILE_SELECTED",
                "job_id": "defaults-and-globs",
                "path": "data10.txt",
            },
            {
                "event": "FILE_SELECTED",
                "job_id": "defaults-and-globs",
                "path": "keep.md",
            },
            {
                "event": "FILE_EXCLUDED",
                "job_id": "defaults-and-globs",
                "path": "report1.log",
                "pattern": "report[12].log",
            },
            {
                "event": "FILE_SELECTED",
                "job_id": "defaults-and-globs",
                "path": "report3.log",
            },
            {
                "event": "FILE_EXCLUDED",
                "job_id": "defaults-and-globs",
                "path": "tmp/cache.bin",
                "pattern": "tmp/**",
            },
            {
                "event": "JOB_COMPLETED",
                "job_id": "defaults-and-globs",
                "selected": 3,
                "excluded": 3,
            },
        ],
    )
    return result["stdout_path"], result["stderr_path"]


def scenario_file_backup_cp1_safe_dump_shape(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "backup_scheduler.py")
    artifact_dir = artifact_root / "file_backup" / "checkpoint_1"

    with TemporaryDirectory(prefix="file-backup-acceptance-") as tmp:
        scratch = Path(tmp)
        files_root = scratch / "files"
        for rel_path, content in [
            ("keep.txt", "keep"),
            ("notes.bak", "old"),
            ("tmp/cache.bin", "cache"),
        ]:
            write_text(files_root / rel_path, content)
        schedule_path = scratch / "schedule.yaml"
        schedule = {
            "version": 1,
            "timezone": "UTC",
            "jobs": [
                {
                    "id": "dumped-shape",
                    "source": "mount://",
                    "destination": "backup://",
                    "exclude": ["tmp/**", "*.bak"],
                    "when": {"kind": "daily", "at": "03:30"},
                }
            ],
        }
        write_text(schedule_path, yaml.safe_dump(schedule, sort_keys=False))
        result = run_backup_scheduler(
            workspace=workspace,
            script_path=script_path,
            scratch=scratch,
            artifact_dir=artifact_dir,
            name="file_backup_cp001_safe_dump_shape",
            schedule=schedule_path,
            mount=files_root,
            now="2025-09-10T03:30:00Z",
            duration="0",
        )

    if result["exit_code"] != 0:
        raise ProductError("safe-dumped schedule shape must parse successfully")
    assert_stderr_empty(result)
    rows = parse_json_lines(result["stdout"])
    if (
        not rows
        or not isinstance(rows[0], dict)
        or rows[0].get("event") != "SCHEDULE_PARSED"
    ):
        raise ScenarioFailureError("safe-dumped schedule produced no parse event")
    assert_json_lines_match_subsets(
        result["stdout"],
        [
            {"event": "SCHEDULE_PARSED", "timezone": "UTC", "jobs_total": 1},
            {
                "event": "JOB_ELIGIBLE",
                "job_id": "dumped-shape",
                "kind": "daily",
                "now_local": "2025-09-10T03:30:00Z",
            },
            {"event": "JOB_STARTED", "job_id": "dumped-shape", "exclude_count": 2},
            {"event": "FILE_SELECTED", "job_id": "dumped-shape", "path": "keep.txt"},
            {
                "event": "FILE_EXCLUDED",
                "job_id": "dumped-shape",
                "path": "notes.bak",
                "pattern": "*.bak",
            },
            {
                "event": "FILE_EXCLUDED",
                "job_id": "dumped-shape",
                "path": "tmp/cache.bin",
                "pattern": "tmp/**",
            },
            {
                "event": "JOB_COMPLETED",
                "job_id": "dumped-shape",
                "selected": 1,
                "excluded": 2,
            },
        ],
    )
    return result["stdout_path"], result["stderr_path"]


def scenario_file_backup_cp1_malformed_yaml(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "backup_scheduler.py")
    artifact_dir = artifact_root / "file_backup" / "checkpoint_1"

    with TemporaryDirectory(prefix="file-backup-acceptance-") as tmp:
        scratch = Path(tmp)
        files_root = scratch / "files"
        files_root.mkdir(parents=True)
        schedule_path = scratch / "schedule.yaml"
        write_text(schedule_path, "jobs: [\n")
        result = run_backup_scheduler(
            workspace=workspace,
            script_path=script_path,
            scratch=scratch,
            artifact_dir=artifact_dir,
            name="file_backup_cp001_malformed_yaml",
            schedule=schedule_path,
            mount=files_root,
            now="2025-09-10T03:30:00Z",
            duration="1",
        )

    if result["exit_code"] == 0:
        raise ScenarioFailureError("malformed YAML must return a non-zero status")
    if result["stdout"].strip():
        raise ScenarioFailureError("malformed YAML must not emit JSONL stdout")
    return result["stdout_path"], result["stderr_path"]


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


def run_migrate_configs(
    *,
    workspace: Path,
    script_path: Path,
    artifact_dir: Path,
    name: str,
    rules: Path,
    target_dir: Path,
    inheritance: Path | None = None,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(script_path),
        str(rules),
        str(target_dir),
    ]
    if inheritance is not None:
        command.extend(["--inheritance", str(inheritance)])
    return run_command(
        command,
        cwd=workspace,
        artifact_dir=artifact_dir,
        name=name,
    )


def scenario_migrate_configs_cp1_basic_rules(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "migrate.py")
    artifact_dir = artifact_root / "migrate_configs" / "checkpoint_1"

    with TemporaryDirectory(prefix="migrate-configs-acceptance-") as tmp:
        scratch = Path(tmp)
        configs = scratch / "configs"
        rules_path = scratch / "rules.json"
        write_text(
            rules_path,
            json.dumps(
                {
                    "add_logging_config": {
                        "type": "merge_data",
                        "glob": "**/*.yaml",
                        "data": {
                            "logging": {
                                "level": "info",
                                "handlers": ["console", "file"],
                            },
                            "cache": {"enabled": True},
                        },
                    },
                    "prod_env": {
                        "type": "replace_value",
                        "key": "environment",
                        "value": "production",
                    },
                    "rename_db_key": {
                        "type": "rename_key",
                        "old_key": "db.hostname",
                        "new_key": "db.host",
                    },
                },
                indent=2,
            ),
        )
        write_text(
            configs / "app.json",
            json.dumps(
                {
                    "environment": "development",
                    "db": {"hostname": "localhost", "port": 5432},
                }
            ),
        )
        write_text(
            configs / "config.yaml",
            """
app: myapp
logging:
  level: debug
  format: json
cache:
  ttl: 300
""".lstrip(),
        )
        result = run_migrate_configs(
            workspace=workspace,
            script_path=script_path,
            artifact_dir=artifact_dir,
            name="migrate_configs_cp001_basic_rules",
            rules=rules_path,
            target_dir=configs,
        )

        app_json = load_json_config(configs / "app.json")
        config_yaml = load_yaml_config(configs / "config.yaml")

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    assert_path_value(app_json, "environment", "production")
    assert_path_value(app_json, "db.host", "localhost")
    if isinstance(app_json.get("db"), dict) and "hostname" in app_json["db"]:
        raise ScenarioFailureError("renamed db.hostname key must be removed")
    assert_path_value(config_yaml, "logging.level", "info")
    assert_path_value(config_yaml, "logging.format", "json")
    assert_path_value(config_yaml, "cache.ttl", 300)
    assert_path_value(config_yaml, "cache.enabled", True)
    assert_file_updated_event(
        result["stdout"],
        file_path="app.json",
        rules_applied=["prod_env", "rename_db_key"],
    )
    assert_file_updated_event(
        result["stdout"],
        file_path="config.yaml",
        rules_applied=["add_logging_config"],
    )
    return result["stdout_path"], result["stderr_path"]


def scenario_migrate_configs_cp1_formats_and_ignored_files(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "migrate.py")
    artifact_dir = artifact_root / "migrate_configs" / "checkpoint_1"

    with TemporaryDirectory(prefix="migrate-configs-acceptance-") as tmp:
        scratch = Path(tmp)
        configs = scratch / "configs"
        rules_path = scratch / "rules.json"
        write_text(
            rules_path,
            json.dumps(
                {
                    "update_region": {
                        "type": "replace_value",
                        "key": "app.region",
                        "value": "us-west-2",
                    }
                }
            ),
        )
        write_text(configs / "app.json", '{"app":{"region":"us-east-1"}}\n')
        write_text(configs / "service.yaml", "app:\n  region: us-east-1\n")
        write_text(configs / "service.yml", "app:\n  region: us-east-1\n")
        write_text(configs / "app.toml", '[app]\nregion = "us-east-1"\n')
        write_text(configs / "app.ini", "[app]\nregion = us-east-1\n")
        write_text(configs / "readme.txt", "app.region=us-east-1\n")
        result = run_migrate_configs(
            workspace=workspace,
            script_path=script_path,
            artifact_dir=artifact_dir,
            name="migrate_configs_cp001_formats_and_ignored_files",
            rules=rules_path,
            target_dir=configs,
        )

        app_json = load_json_config(configs / "app.json")
        service_yaml = load_yaml_config(configs / "service.yaml")
        service_yml = load_yaml_config(configs / "service.yml")
        app_toml = load_toml_config(configs / "app.toml")
        app_ini = load_ini_config(configs / "app.ini")
        ignored_text = (configs / "readme.txt").read_text(encoding="utf-8")

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    for data in [app_json, service_yaml, service_yml, app_toml]:
        assert_path_value(data, "app.region", "us-west-2")
    if app_ini["app"]["region"] != "us-west-2":
        raise ScenarioFailureError("INI app.region was not updated")
    if ignored_text != "app.region=us-east-1\n":
        raise ScenarioFailureError("unsupported .txt file must remain unchanged")
    for file_path in ["app.ini", "app.json", "app.toml", "service.yaml", "service.yml"]:
        assert_file_updated_event(
            result["stdout"],
            file_path=file_path,
            rules_applied=["update_region"],
        )
    assert_no_file_updated_event(result["stdout"], file_path="readme.txt")
    return result["stdout_path"], result["stderr_path"]


def scenario_migrate_configs_cp2_patterns_templates_conditions(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "migrate.py")
    artifact_dir = artifact_root / "migrate_configs" / "checkpoint_2"

    with TemporaryDirectory(prefix="migrate-configs-acceptance-") as tmp:
        scratch = Path(tmp)
        configs = scratch / "configs"
        rules_path = scratch / "rules.json"
        write_text(
            rules_path,
            json.dumps(
                {
                    "normalize_service_hosts": {
                        "type": "pattern_replace",
                        "key_pattern": "services.$name.host",
                        "value": "${name}.internal.example.com",
                    },
                    "prod_only": {
                        "type": "conditional_replace",
                        "key": "server.host",
                        "value": "prod.example.com",
                        "condition": {"current_value_equals": "localhost"},
                    },
                    "set_bucket_name": {
                        "type": "template_string",
                        "key": "s3.bucket",
                        "variables": {
                            "env": "environment",
                            "region": "aws.region",
                        },
                        "template": "data-${env}-${region}",
                    },
                },
                indent=2,
            ),
        )
        write_text(
            configs / "config.json",
            json.dumps(
                {
                    "services": {
                        "api": {"host": "localhost", "port": 8080},
                        "database": {"host": "localhost", "port": 5432},
                    },
                    "server": {"host": "localhost"},
                }
            ),
        )
        write_text(
            configs / "bucket.yaml",
            """
environment: staging
aws:
  region: us-west-2
s3:
  bucket: old-bucket
""".lstrip(),
        )
        write_text(
            configs / "stage.json",
            json.dumps({"server": {"host": "staging.example.com"}}),
        )
        stage_before = (configs / "stage.json").read_text(encoding="utf-8")
        result = run_migrate_configs(
            workspace=workspace,
            script_path=script_path,
            artifact_dir=artifact_dir,
            name="migrate_configs_cp002_patterns_templates_conditions",
            rules=rules_path,
            target_dir=configs,
        )

        config_json = load_json_config(configs / "config.json")
        bucket_yaml = load_yaml_config(configs / "bucket.yaml")
        stage_after = (configs / "stage.json").read_text(encoding="utf-8")

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    assert_path_value(
        config_json,
        "services.api.host",
        "api.internal.example.com",
    )
    assert_path_value(
        config_json,
        "services.database.host",
        "database.internal.example.com",
    )
    assert_path_value(config_json, "server.host", "prod.example.com")
    assert_path_value(bucket_yaml, "s3.bucket", "data-staging-us-west-2")
    if stage_after != stage_before:
        raise ScenarioFailureError("failed conditional replacement must not update file")
    assert_file_updated_event(
        result["stdout"],
        file_path="config.json",
        rules_applied=["normalize_service_hosts", "prod_only"],
    )
    assert_file_updated_event(
        result["stdout"],
        file_path="bucket.yaml",
        rules_applied=["set_bucket_name"],
    )
    assert_no_file_updated_event(result["stdout"], file_path="stage.json")
    return result["stdout_path"], result["stderr_path"]


def scenario_migrate_configs_cp2_prior_rules_order(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "migrate.py")
    artifact_dir = artifact_root / "migrate_configs" / "checkpoint_2"

    with TemporaryDirectory(prefix="migrate-configs-acceptance-") as tmp:
        scratch = Path(tmp)
        configs = scratch / "configs"
        rules_path = scratch / "rules.json"
        write_text(
            rules_path,
            json.dumps(
                {
                    "a_merge_defaults": {
                        "type": "merge_data",
                        "data": {
                            "environment": "production",
                            "timeout": 30,
                        },
                    },
                    "b_set_description": {
                        "type": "template_string",
                        "key": "description",
                        "variables": {"env": "environment"},
                        "template": "${env} service",
                    },
                    "c_update_ports": {
                        "type": "pattern_replace",
                        "key_pattern": "services.*.port",
                        "value": 9000,
                    },
                    "d_normalize_host": {
                        "type": "conditional_replace",
                        "key": "server.host",
                        "value": "127.0.0.1",
                        "condition": {"current_value_matches": "^localhost$"},
                    },
                    "e_rename_db": {
                        "type": "rename_key",
                        "old_key": "db.hostname",
                        "new_key": "db.host",
                    },
                },
                indent=2,
            ),
        )
        write_text(
            configs / "app.json",
            json.dumps(
                {
                    "description": "My service",
                    "services": {
                        "api": {"port": 8080},
                        "worker": {"port": 8081},
                    },
                    "server": {"host": "localhost"},
                    "db": {"hostname": "db.local"},
                }
            ),
        )
        result = run_migrate_configs(
            workspace=workspace,
            script_path=script_path,
            artifact_dir=artifact_dir,
            name="migrate_configs_cp002_prior_rules_order",
            rules=rules_path,
            target_dir=configs,
        )

        app_json = load_json_config(configs / "app.json")

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    assert_path_value(app_json, "environment", "production")
    assert_path_value(app_json, "description", "production service")
    assert_path_value(app_json, "services.api.port", 9000)
    assert_path_value(app_json, "services.worker.port", 9000)
    assert_path_value(app_json, "server.host", "127.0.0.1")
    assert_path_value(app_json, "db.host", "db.local")
    assert_file_updated_event(
        result["stdout"],
        file_path="app.json",
        rules_applied=[
            "a_merge_defaults",
            "b_set_description",
            "c_update_ports",
            "d_normalize_host",
            "e_rename_db",
        ],
    )
    return result["stdout_path"], result["stderr_path"]


def scenario_migrate_configs_cp3_arrays_and_inheritance(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "migrate.py")
    artifact_dir = artifact_root / "migrate_configs" / "checkpoint_3"

    with TemporaryDirectory(prefix="migrate-configs-acceptance-") as tmp:
        scratch = Path(tmp)
        configs = scratch / "configs"
        rules_path = scratch / "rules.json"
        inheritance_path = scratch / "inheritance.json"
        write_text(
            rules_path,
            json.dumps(
                {
                    "a_promote_enabled": {
                        "type": "pattern_replace",
                        "key_pattern": "services[?enabled=true].host",
                        "value": "internal.example.com",
                    },
                    "b_build_primary_url": {
                        "type": "template_string",
                        "key": "primary_endpoint",
                        "variables": {
                            "host": "services[0].host",
                            "port": "services[0].port",
                        },
                        "template": "http://${host}:${port}",
                    },
                },
                indent=2,
            ),
        )
        write_text(
            inheritance_path,
            json.dumps({"json": {"pattern": "import"}}, indent=2),
        )
        write_text(
            configs / "root.json",
            json.dumps({"root_only": True, "defaults": {"retries": 2}}),
        )
        write_text(
            configs / "base.json",
            json.dumps(
                {
                    "import": "root.json",
                    "base_only": True,
                    "environment": "base",
                }
            ),
        )
        write_text(
            configs / "app.json",
            json.dumps(
                {
                    "import": "base.json",
                    "environment": "child",
                    "primary_endpoint": "unused",
                    "services": [
                        {
                            "name": "api",
                            "enabled": True,
                            "host": "localhost",
                            "port": 8080,
                        },
                        {
                            "name": "worker",
                            "enabled": False,
                            "host": "localhost",
                            "port": 9000,
                        },
                    ],
                }
            ),
        )
        result = run_migrate_configs(
            workspace=workspace,
            script_path=script_path,
            artifact_dir=artifact_dir,
            name="migrate_configs_cp003_arrays_and_inheritance",
            rules=rules_path,
            target_dir=configs,
            inheritance=inheritance_path,
        )

        app_json = load_json_config(configs / "app.json")
        root_json = load_json_config(configs / "root.json")
        base_json = load_json_config(configs / "base.json")

    assert_exit_status(result, 0)
    assert_stderr_empty(result)
    assert_path_value(app_json, "root_only", True)
    assert_path_value(app_json, "defaults.retries", 2)
    assert_path_value(app_json, "base_only", True)
    assert_path_value(app_json, "environment", "child")
    if "import" in app_json:
        raise ScenarioFailureError("inheritance directive must be removed")
    services = app_json.get("services")
    if not isinstance(services, list) or len(services) != 2:
        raise ScenarioFailureError("expected inherited app services array")
    if services[0].get("host") != "internal.example.com":
        raise ScenarioFailureError("enabled array item host was not replaced")
    if services[1].get("host") != "localhost":
        raise ScenarioFailureError("disabled array item host must remain unchanged")
    assert_path_value(app_json, "primary_endpoint", "http://internal.example.com:8080")
    if root_json != {"root_only": True, "defaults": {"retries": 2}}:
        raise ScenarioFailureError("parent root config must not be modified")
    if base_json.get("import") != "root.json":
        raise ScenarioFailureError("parent base config must not be rewritten")
    assert_file_updated_event(
        result["stdout"],
        file_path="app.json",
        rules_applied=["a_promote_enabled", "b_build_primary_url"],
    )
    assert_no_file_updated_event(result["stdout"], file_path="base.json")
    assert_no_file_updated_event(result["stdout"], file_path="root.json")
    return result["stdout_path"], result["stderr_path"]


def scenario_migrate_configs_cp3_errors_and_skips(
    workspace: Path, artifact_root: Path
) -> tuple[str | None, str | None]:
    script_path = product_script(workspace, "migrate.py")
    artifact_dir = artifact_root / "migrate_configs" / "checkpoint_3"

    with TemporaryDirectory(prefix="migrate-configs-acceptance-") as tmp:
        scratch = Path(tmp)

        circular_dir = scratch / "circular"
        circular_rules = scratch / "circular_rules.json"
        circular_inheritance = scratch / "circular_inheritance.json"
        write_text(circular_rules, "{}\n")
        write_text(
            circular_inheritance,
            json.dumps({"yaml": {"pattern": "extends"}}),
        )
        a_path = circular_dir / "a.yaml"
        b_path = circular_dir / "b.yaml"
        write_text(a_path, "extends: b.yaml\nname: a\n")
        write_text(b_path, "extends: a.yaml\nname: b\n")
        a_before = a_path.read_text(encoding="utf-8")
        b_before = b_path.read_text(encoding="utf-8")
        circular_result = run_migrate_configs(
            workspace=workspace,
            script_path=script_path,
            artifact_dir=artifact_dir,
            name="migrate_configs_cp003_circular_inheritance",
            rules=circular_rules,
            target_dir=circular_dir,
            inheritance=circular_inheritance,
        )
        a_after = a_path.read_text(encoding="utf-8")
        b_after = b_path.read_text(encoding="utf-8")

        skip_dir = scratch / "skip"
        skip_rules = scratch / "skip_rules.json"
        write_text(
            skip_rules,
            json.dumps(
                {
                    "array_no_match": {
                        "type": "pattern_replace",
                        "key_pattern": "services[?enabled=true].host",
                        "value": "internal.example.com",
                    },
                    "missing_template_var": {
                        "type": "template_string",
                        "key": "endpoint",
                        "variables": {"host": "services[1].host"},
                        "template": "http://${host}",
                    },
                }
            ),
        )
        skip_config = skip_dir / "app.json"
        write_text(
            skip_config,
            json.dumps(
                {
                    "endpoint": "unchanged",
                    "services": [
                        {
                            "name": "worker",
                            "enabled": False,
                            "host": "localhost",
                        }
                    ],
                },
                sort_keys=True,
            )
            + "\n",
        )
        skip_before = skip_config.read_text(encoding="utf-8")
        skip_result = run_migrate_configs(
            workspace=workspace,
            script_path=script_path,
            artifact_dir=artifact_dir,
            name="migrate_configs_cp003_skipped_rules",
            rules=skip_rules,
            target_dir=skip_dir,
        )
        skip_after = skip_config.read_text(encoding="utf-8")

    if circular_result["exit_code"] == 0:
        raise ScenarioFailureError("circular inheritance must fail")
    if "circular dependency" not in circular_result["stderr"]:
        raise ScenarioFailureError("circular inheritance error must mention the cycle")
    if a_after != a_before or b_after != b_before:
        raise ScenarioFailureError("circular inheritance must not modify files")
    assert_exit_status(skip_result, 0)
    assert_stderr_empty(skip_result)
    assert_stdout_empty(skip_result)
    if skip_after != skip_before:
        raise ScenarioFailureError("skipped array/template rules must not modify files")
    return skip_result["stdout_path"], skip_result["stderr_path"]


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
        "problem_id": "code_search",
        "checkpoint_index": 3,
        "scenario_id": "code_search.cp003.nested-expression-capture",
        "scenario_name": "Workspace product captures nested expression metavariables",
        "tags": ["problem:code_search", "checkpoint:3", "core", "positive", "cli"],
        "scenario_func": scenario_code_search_cp3_nested_expression,
    },
    {
        "problem_id": "code_search",
        "checkpoint_index": 3,
        "scenario_id": "code_search.cp003.pattern-edge-semantics",
        "scenario_name": "Workspace product honors optional, literal-dollar, and multi-capture pattern semantics",
        "tags": ["problem:code_search", "checkpoint:3", "core", "positive", "cli"],
        "scenario_func": scenario_code_search_cp3_pattern_edge_semantics,
    },
    {
        "problem_id": "code_search",
        "checkpoint_index": 3,
        "scenario_id": "code_search.cp003.multiline-python-captures",
        "scenario_name": "Workspace product preserves multiline Python capture boundaries",
        "tags": ["problem:code_search", "checkpoint:3", "core", "positive", "cli"],
        "scenario_func": scenario_code_search_cp3_multiline_python_captures,
    },
    {
        "problem_id": "code_search",
        "checkpoint_index": 3,
        "scenario_id": "code_search.cp003.expression-capture-boundaries",
        "scenario_name": "Workspace product captures simple expressions and string literal boundaries",
        "tags": ["problem:code_search", "checkpoint:3", "edge", "positive", "cli"],
        "scenario_func": scenario_code_search_cp3_expression_capture_boundaries,
    },
    {
        "problem_id": "code_search",
        "checkpoint_index": 3,
        "scenario_id": "code_search.cp003.comprehension-and-cpp-blocks",
        "scenario_name": "Workspace product captures list comprehensions and multiline C++ blocks",
        "tags": ["problem:code_search", "checkpoint:3", "edge", "positive", "cli"],
        "scenario_func": scenario_code_search_cp3_comprehension_and_cpp_blocks,
    },
    {
        "problem_id": "migrate_configs",
        "checkpoint_index": 1,
        "scenario_id": "migrate_configs.cp001.basic-rules",
        "scenario_name": "Workspace product applies replace, rename, and deep-merge rules",
        "tags": ["problem:migrate_configs", "checkpoint:1", "core", "positive", "cli", "file_io"],
        "scenario_func": scenario_migrate_configs_cp1_basic_rules,
    },
    {
        "problem_id": "migrate_configs",
        "checkpoint_index": 1,
        "scenario_id": "migrate_configs.cp001.formats-and-ignored-files",
        "scenario_name": "Workspace product processes supported config formats and ignores unsupported files",
        "tags": ["problem:migrate_configs", "checkpoint:1", "core", "positive", "cli", "file_io"],
        "scenario_func": scenario_migrate_configs_cp1_formats_and_ignored_files,
    },
    {
        "problem_id": "migrate_configs",
        "checkpoint_index": 2,
        "scenario_id": "migrate_configs.cp002.patterns-templates-conditions",
        "scenario_name": "Workspace product applies pattern, template, and conditional rules",
        "tags": ["problem:migrate_configs", "checkpoint:2", "core", "positive", "cli", "file_io"],
        "scenario_func": scenario_migrate_configs_cp2_patterns_templates_conditions,
    },
    {
        "problem_id": "migrate_configs",
        "checkpoint_index": 2,
        "scenario_id": "migrate_configs.cp002.prior-rules-order",
        "scenario_name": "Workspace product preserves prior rules and reports lexicographic rule order",
        "tags": ["problem:migrate_configs", "checkpoint:2", "regression", "positive", "cli", "file_io"],
        "scenario_func": scenario_migrate_configs_cp2_prior_rules_order,
    },
    {
        "problem_id": "migrate_configs",
        "checkpoint_index": 3,
        "scenario_id": "migrate_configs.cp003.arrays-and-inheritance",
        "scenario_name": "Workspace product resolves inheritance and updates filtered array items",
        "tags": ["problem:migrate_configs", "checkpoint:3", "core", "positive", "cli", "file_io"],
        "scenario_func": scenario_migrate_configs_cp3_arrays_and_inheritance,
    },
    {
        "problem_id": "migrate_configs",
        "checkpoint_index": 3,
        "scenario_id": "migrate_configs.cp003.errors-and-skips",
        "scenario_name": "Workspace product rejects circular inheritance and skips missing matches",
        "tags": ["problem:migrate_configs", "checkpoint:3", "edge", "negative", "cli", "file_io"],
        "scenario_func": scenario_migrate_configs_cp3_errors_and_skips,
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
        "checkpoint_index": 1,
        "scenario_id": "file_backup.cp001.due-window-semantics",
        "scenario_name": "Workspace product evaluates daily, weekly, and once due windows",
        "tags": ["problem:file_backup", "checkpoint:1", "core", "positive", "cli"],
        "scenario_func": scenario_file_backup_cp1_due_windows,
    },
    {
        "problem_id": "file_backup",
        "checkpoint_index": 1,
        "scenario_id": "file_backup.cp001.recurring-triggers",
        "scenario_name": "Workspace product runs recurring jobs for every trigger in the window",
        "tags": ["problem:file_backup", "checkpoint:1", "core", "positive", "cli"],
        "scenario_func": scenario_file_backup_cp1_recurring_triggers,
    },
    {
        "problem_id": "file_backup",
        "checkpoint_index": 1,
        "scenario_id": "file_backup.cp001.disabled-jobs",
        "scenario_name": "Workspace product suppresses events for disabled jobs",
        "tags": ["problem:file_backup", "checkpoint:1", "edge", "negative", "cli"],
        "scenario_func": scenario_file_backup_cp1_disabled_jobs,
    },
    {
        "problem_id": "file_backup",
        "checkpoint_index": 1,
        "scenario_id": "file_backup.cp001.block-lists-defaults-globs",
        "scenario_name": "Workspace product handles block lists, defaults, and representative globs",
        "tags": ["problem:file_backup", "checkpoint:1", "edge", "positive", "cli"],
        "scenario_func": scenario_file_backup_cp1_block_lists_defaults_globs,
    },
    {
        "problem_id": "file_backup",
        "checkpoint_index": 1,
        "scenario_id": "file_backup.cp001.safe-dump-shape",
        "scenario_name": "Workspace product accepts YAML dumper sequence indentation",
        "tags": ["problem:file_backup", "checkpoint:1", "edge", "positive", "cli"],
        "scenario_func": scenario_file_backup_cp1_safe_dump_shape,
    },
    {
        "problem_id": "file_backup",
        "checkpoint_index": 1,
        "scenario_id": "file_backup.cp001.malformed-yaml",
        "scenario_name": "Workspace product rejects malformed YAML schedules",
        "tags": ["problem:file_backup", "checkpoint:1", "edge", "negative", "cli"],
        "scenario_func": scenario_file_backup_cp1_malformed_yaml,
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
    global LAST_COMMAND_RESULT
    started = time.perf_counter()
    status = "passed"
    failure_type: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    command_path: str | None = None
    command_log_path: str | None = None
    LAST_COMMAND_RESULT = None
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
    if LAST_COMMAND_RESULT is not None:
        stdout_path = stdout_path or LAST_COMMAND_RESULT.get("stdout_path")
        stderr_path = stderr_path or LAST_COMMAND_RESULT.get("stderr_path")
        command_path = LAST_COMMAND_RESULT.get("command_path")
        command_log_path = LAST_COMMAND_RESULT.get("command_log_path")
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
        "command_path": command_path,
        "command_log_path": command_log_path,
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
    parser.add_argument("--scope-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.scope_output:
        if not args.problem_id or not args.checkpoint_id:
            raise HarnessError("--problem-id and --checkpoint-id are required")
        write_scoped_runner(
            source_path=Path(__file__).resolve(),
            output_path=args.scope_output,
            problem_id=args.problem_id,
            checkpoint_id=args.checkpoint_id,
            through_checkpoint=args.through_checkpoint,
        )
        return 0

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
