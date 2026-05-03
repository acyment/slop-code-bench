#!/usr/bin/env python3
"""Normalize experiment and native SCBench run artifacts into JSONL tables."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from git import InvalidGitRepositoryError
from git import Repo

CHECKPOINT_DIR_RE = re.compile(r"^checkpoint_(?P<index>\d+)$")
CONDITION_RE = re.compile(r"(?<![A-Za-z0-9])(?P<condition>c[0-5])(?![A-Za-z0-9])", re.I)
REPLICATE_RE = re.compile(r"(?:^|[_-])r(?P<replicate>\d+)(?:$|[_-])", re.I)

RUN_FIELDS = [
    "schema_version",
    "run_id",
    "condition_id",
    "problem_id",
    "replicate_id",
    "model",
    "agent_harness",
    "agent_version",
    "benchmark_commit",
    "experiment_commit",
    "started_at",
    "ended_at",
    "status",
    "checkpoint_count_expected",
    "checkpoint_count_completed",
    "artifact_root",
]

CHECKPOINT_FIELDS = [
    "schema_version",
    "run_id",
    "condition_id",
    "problem_id",
    "checkpoint_id",
    "checkpoint_index",
    "replicate_id",
    "model",
    "agent_harness",
    "agent_version",
    "benchmark_commit",
    "experiment_commit",
    "started_at",
    "ended_at",
    "status",
    "visible_acceptance_passed",
    "hidden_tests_passed",
    "current_checkpoint_passed",
    "prior_regression_count",
    "hidden_failure_after_visible_pass",
    "artifact_paths",
]


class ExportError(ValueError):
    """Raised when run artifacts cannot be exported."""


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def current_git_commit(root: Path) -> str:
    try:
        return Repo(root).head.commit.hexsha
    except (InvalidGitRepositoryError, ValueError):
        return "unknown"


def rel_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ExportError(f"Expected JSON object at {path}")
    return payload


def read_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return read_json(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise ExportError(f"Expected JSON object at {path}:{line_number}")
            rows.append(payload)
    return rows


def read_yaml_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ExportError(f"Expected YAML mapping at {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def require_fields(row: dict[str, Any], fields: list[str], source: str) -> None:
    missing = [field for field in fields if field not in row]
    if missing:
        joined = ", ".join(missing)
        raise ExportError(f"{source} is missing required fields: {joined}")


def as_number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    return None


def nested_get(payload: dict[str, Any] | None, path: list[str]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def nested_number(payload: dict[str, Any] | None, paths: list[list[str]]) -> float | int | None:
    for path in paths:
        value = as_number(nested_get(payload, path))
        if value is not None:
            return value
    return None


def group_count(counts: dict[str, Any], group_name: str) -> int:
    for key, value in counts.items():
        if str(key).lower() == group_name.lower() and isinstance(value, int):
            return value
    return 0


def safe_rate(passed: int, total: int) -> float | None:
    if total <= 0:
        return None
    return passed / total


def checkpoint_index_from_name(name: str) -> int | None:
    match = CHECKPOINT_DIR_RE.match(name)
    if match is None:
        return None
    return int(match.group("index"))


def checkpoint_sort_key(path: Path) -> tuple[int, str]:
    return (checkpoint_index_from_name(path.name) or 10_000, path.name)


def guess_condition_id(path: Path) -> str | None:
    match = CONDITION_RE.search(path.name)
    if match is None:
        return None
    return match.group("condition").upper()


def guess_replicate_id(path: Path) -> int | None:
    match = REPLICATE_RE.search(path.name)
    if match is None:
        return None
    return int(match.group("replicate"))


def model_name_from_config(config: dict[str, Any]) -> str | None:
    model = config.get("model")
    if not isinstance(model, dict):
        return None
    provider = model.get("provider")
    name = model.get("name")
    if provider and name:
        return f"{provider}/{name}"
    if name:
        return str(name)
    return None


def agent_id_from_config(config: dict[str, Any]) -> str | None:
    agent = config.get("agent")
    if not isinstance(agent, dict):
        return None
    agent_id = agent.get("type") or agent.get("binary")
    return str(agent_id) if agent_id else None


def agent_version_from_config(config: dict[str, Any]) -> str | None:
    agent = config.get("agent")
    if not isinstance(agent, dict):
        return None
    version = agent.get("version")
    return str(version) if version is not None else None


def problem_from_config(config: dict[str, Any]) -> str | None:
    problems = config.get("problems")
    if isinstance(problems, list) and len(problems) == 1:
        return str(problems[0])
    return None


def extract_cost_metrics(inference: dict[str, Any] | None) -> dict[str, Any]:
    usage = nested_get(inference, ["usage"])
    if not isinstance(usage, dict):
        usage = {}
    net_tokens = usage.get("net_tokens")
    if not isinstance(net_tokens, dict):
        net_tokens = {}
    current_tokens = usage.get("current_tokens")
    if not isinstance(current_tokens, dict):
        current_tokens = {}

    return {
        "api_cost_usd": as_number(usage.get("cost")),
        "agent_steps": as_number(usage.get("steps")),
        "input_tokens_net": as_number(net_tokens.get("input")),
        "output_tokens_net": as_number(net_tokens.get("output")),
        "cache_read_tokens_net": as_number(net_tokens.get("cache_read")),
        "cache_write_tokens_net": as_number(net_tokens.get("cache_write")),
        "reasoning_tokens_net": as_number(net_tokens.get("reasoning")),
        "input_tokens_final": as_number(current_tokens.get("input")),
        "output_tokens_final": as_number(current_tokens.get("output")),
        "cache_read_tokens_final": as_number(current_tokens.get("cache_read")),
        "cache_write_tokens_final": as_number(current_tokens.get("cache_write")),
        "reasoning_tokens_final": as_number(current_tokens.get("reasoning")),
        "agent_duration_seconds": nested_number(inference, [["elapsed"]]),
    }


def extract_scbench_metrics(evaluation: dict[str, Any] | None) -> dict[str, Any]:
    if evaluation is None:
        return {}
    pass_counts_payload = evaluation.get("pass_counts")
    total_counts_payload = evaluation.get("total_counts")
    pass_counts = pass_counts_payload if isinstance(pass_counts_payload, dict) else {}
    total_counts = total_counts_payload if isinstance(total_counts_payload, dict) else {}

    total_tests = sum(value for value in total_counts.values() if isinstance(value, int))
    passed_tests = sum(value for value in pass_counts.values() if isinstance(value, int))
    core_total = group_count(total_counts, "Core")
    core_passed = group_count(pass_counts, "Core")
    functionality_total = group_count(total_counts, "Functionality")
    functionality_passed = group_count(pass_counts, "Functionality")
    error_total = group_count(total_counts, "Error")
    error_passed = group_count(pass_counts, "Error")
    regression_total = group_count(total_counts, "Regression")
    regression_passed = group_count(pass_counts, "Regression")
    current_total = total_tests - regression_total
    current_passed = passed_tests - regression_passed

    return {
        "strict_pass_rate": safe_rate(passed_tests, total_tests),
        "isolated_pass_rate": safe_rate(current_passed, current_total),
        "core_pass_rate": safe_rate(core_passed, core_total),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "core_total": core_total,
        "core_passed": core_passed,
        "functionality_total": functionality_total,
        "functionality_passed": functionality_passed,
        "error_total": error_total,
        "error_passed": error_passed,
        "regression_total": regression_total,
        "regression_passed": regression_passed,
        "hidden_eval_duration_seconds": as_number(evaluation.get("duration")),
        "pytest_exit_code": evaluation.get("pytest_exit_code"),
        "pytest_collected": evaluation.get("pytest_collected"),
        "test_collection_hash": evaluation.get("test_collection_hash"),
        "infrastructure_failure": bool(evaluation.get("infrastructure_failure")),
    }


def hidden_passed_from_scbench(scbench: dict[str, Any]) -> bool | None:
    if not scbench:
        return None
    if scbench.get("infrastructure_failure") is True:
        return False
    core_total = scbench.get("core_total")
    core_passed = scbench.get("core_passed")
    total_tests = scbench.get("total_tests")
    passed_tests = scbench.get("passed_tests")
    if isinstance(core_total, int) and core_total > 0:
        return core_passed == core_total
    if isinstance(total_tests, int) and total_tests > 0:
        return passed_tests == total_tests
    return False


def flatten_quality_metrics(
    *,
    run_row: dict[str, Any],
    checkpoint_row: dict[str, Any],
    quality: dict[str, Any] | None,
    diff: dict[str, Any] | None,
    scbench: dict[str, Any],
    checkpoint_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    loc = nested_number(quality, [["lines", "total_lines"], ["total_lines"], ["loc"]])
    sloc = nested_number(quality, [["lines", "loc"], ["sloc"]])
    cloned_sloc = nested_number(
        quality,
        [
            ["redundancy", "cloned_sloc_lines"],
            ["cloned_sloc_lines"],
        ],
    )
    cloned_pct = nested_number(
        quality,
        [
            ["redundancy", "cloned_pct"],
            ["redundancy", "clone_ratio_sum"],
            ["cloned_pct"],
        ],
    )
    verbosity = nested_number(
        quality,
        [
            ["verbosity"],
            ["root", "verbosity"],
            ["root", "verbosity_flagged_pct"],
            ["verbosity_flagged_pct"],
        ],
    )
    erosion = nested_number(
        quality,
        [
            ["erosion"],
            ["mass", "high_cc_pct"],
            ["high_complexity_mass_share"],
        ],
    )

    return {
        "schema_version": 1,
        "run_id": run_row["run_id"],
        "problem_id": run_row["problem_id"],
        "checkpoint_id": checkpoint_row["checkpoint_id"],
        "checkpoint_index": checkpoint_row["checkpoint_index"],
        "condition_id": run_row["condition_id"],
        "replicate_id": run_row["replicate_id"],
        "loc": loc,
        "sloc": sloc,
        "verbosity": verbosity,
        "erosion": erosion,
        "cc_max": nested_number(quality, [["complexity", "cc_max"], ["cc_max"]]),
        "cc_mean": nested_number(quality, [["complexity", "cc_mean"], ["cc_mean"]]),
        "cc_high_count": nested_number(
            quality,
            [["complexity", "cc_high_count"], ["cc_high_count"]],
        ),
        "clone_lines": nested_number(
            quality,
            [["redundancy", "clone_lines"], ["clone_lines"]],
        ),
        "cloned_sloc_lines": cloned_sloc,
        "cloned_pct": cloned_pct,
        "lines_added": nested_number(diff, [["lines_added"], ["added_lines"], ["added"]]),
        "lines_removed": nested_number(
            diff,
            [["lines_removed"], ["removed_lines"], ["removed"]],
        ),
        "files_changed": nested_number(
            diff,
            [["files_changed"], ["changed_files"], ["file_count"]],
        ),
        "dependencies_added": [],
        "acceptance_runtime_ms": None,
        "hidden_eval_runtime_ms": seconds_to_ms(
            scbench.get("hidden_eval_duration_seconds")
        ),
        "quality_artifact": rel_path(
            checkpoint_dir / "quality_analysis" / "overall_quality.json",
            repo_root,
        ),
    }


def seconds_to_ms(value: Any) -> float | None:
    number = as_number(value)
    if number is None:
        return None
    return float(number) * 1000.0


def export_dry_run(
    *,
    run_dir: Path,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    run_row = read_json(run_dir / "run.json")
    require_fields(run_row, RUN_FIELDS, (run_dir / "run.json").as_posix())
    checkpoint_rows = read_jsonl(run_dir / "checkpoints.jsonl")
    for row in checkpoint_rows:
        require_fields(row, CHECKPOINT_FIELDS, (run_dir / "checkpoints.jsonl").as_posix())

    native_technical_rows = read_jsonl(run_dir / "normalized" / "technical_metrics.jsonl")
    native_technical_by_checkpoint = {
        str(row.get("checkpoint_id")): row
        for row in native_technical_rows
        if isinstance(row, dict)
    }
    technical_rows: list[dict[str, Any]] = []
    artifact_rows = [
        {
            "schema_version": 1,
            "run_id": run_row["run_id"],
            "problem_id": run_row["problem_id"],
            "condition_id": run_row["condition_id"],
            "artifact_type": "experiment_wrapper_run",
            "path": rel_path(run_dir, repo_root),
        }
    ]
    for checkpoint_row in checkpoint_rows:
        technical = dict(checkpoint_row.get("technical_metrics") or {})
        native_technical = native_technical_by_checkpoint.get(
            str(checkpoint_row["checkpoint_id"])
        )
        if native_technical is not None:
            technical_row = dict(native_technical)
            technical_row["acceptance_runtime_ms"] = technical.get(
                "acceptance_runtime_ms",
                technical_row.get("acceptance_runtime_ms"),
            )
        else:
            technical_row = {
                "schema_version": 1,
                "run_id": run_row["run_id"],
                "problem_id": run_row["problem_id"],
                "checkpoint_id": checkpoint_row["checkpoint_id"],
                "checkpoint_index": checkpoint_row["checkpoint_index"],
                "condition_id": run_row["condition_id"],
                "replicate_id": run_row["replicate_id"],
                "loc": technical.get("loc"),
                "sloc": technical.get("sloc"),
                "verbosity": technical.get("verbosity"),
                "erosion": technical.get("erosion"),
                "cc_max": technical.get("cc_max"),
                "cc_mean": technical.get("cc_mean"),
                "cc_high_count": technical.get("cc_high_count"),
                "clone_lines": technical.get("clone_lines"),
                "cloned_pct": technical.get("cloned_pct"),
                "lines_added": technical.get("lines_added"),
                "lines_removed": technical.get("lines_removed"),
                "files_changed": technical.get("files_changed"),
                "dependencies_added": technical.get("dependencies_added", []),
                "acceptance_runtime_ms": technical.get("acceptance_runtime_ms"),
                "hidden_eval_runtime_ms": technical.get("hidden_eval_runtime_ms"),
            }
        technical_rows.append(technical_row)
        artifact_rows.append(
            {
                "schema_version": 1,
                "run_id": run_row["run_id"],
                "problem_id": run_row["problem_id"],
                "checkpoint_id": checkpoint_row["checkpoint_id"],
                "condition_id": run_row["condition_id"],
                "artifact_type": "experiment_wrapper_checkpoint",
                "path": checkpoint_row["artifact_paths"].get("checkpoint_dir"),
            }
        )
    return [run_row], checkpoint_rows, technical_rows, artifact_rows


def discover_native_problem_dirs(run_dir: Path) -> list[Path]:
    checkpoint_dirs = [
        path
        for path in run_dir.glob("checkpoint_*")
        if path.is_dir() and checkpoint_index_from_name(path.name)
    ]
    if (run_dir / "run_info.yaml").is_file() or checkpoint_dirs:
        return [run_dir]
    problem_dirs = [
        path
        for path in run_dir.iterdir()
        if path.is_dir()
        and ((path / "run_info.yaml").is_file() or list(path.glob("checkpoint_*")))
    ]
    return sorted(problem_dirs)


def native_checkpoint_dirs(problem_dir: Path) -> list[Path]:
    return sorted(
        [path for path in problem_dir.iterdir() if path.is_dir() and checkpoint_index_from_name(path.name)],
        key=checkpoint_sort_key,
    )


def native_run_status(
    *, run_info: dict[str, Any], checkpoint_rows: list[dict[str, Any]], run_dir: Path
) -> str:
    summary = run_info.get("summary")
    if isinstance(summary, dict):
        if summary.get("error_type") or summary.get("state") == "error":
            return "failed"
        passed_policy = summary.get("passed_policy")
        if passed_policy is True:
            return "completed"
        if checkpoint_rows:
            return "completed_with_failures"
    if checkpoint_rows:
        return "completed_with_unknown_policy"
    if (run_dir / "run_agent.log").is_file() or (run_dir / "config.yaml").is_file():
        return "infrastructure_failure"
    return "failed"


def export_native_problem(
    *,
    run_dir: Path,
    problem_dir: Path,
    repo_root: Path,
    experiment_commit: str,
    overrides: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    config = read_yaml_optional(run_dir / "config.yaml")
    run_info = read_yaml_optional(problem_dir / "run_info.yaml")
    summary = run_info.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    problem_id = (
        overrides.get("problem_id")
        or problem_from_config(config)
        or problem_dir.name
    )
    condition_id = overrides.get("condition_id") or guess_condition_id(run_dir) or "UNKNOWN"
    replicate_id = overrides.get("replicate_id") or guess_replicate_id(run_dir) or 1
    run_id = overrides.get("run_id") or f"{run_dir.name}-{problem_id}"
    model = overrides.get("model") or model_name_from_config(config) or "unknown"
    agent_harness = (
        overrides.get("agent_harness")
        or agent_id_from_config(config)
        or "unknown"
    )
    agent_version = overrides.get("agent_version") or agent_version_from_config(config)
    checkpoint_rows: list[dict[str, Any]] = []
    technical_rows: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []

    run_row = {
        "schema_version": 1,
        "run_id": run_id,
        "condition_id": condition_id,
        "problem_id": problem_id,
        "replicate_id": int(replicate_id),
        "model": model,
        "agent_harness": agent_harness,
        "agent_version": agent_version,
        "benchmark_repo": "SprocketLab/slop-code-bench",
        "benchmark_commit": overrides.get("benchmark_commit") or experiment_commit,
        "problems_repo": "gabeorlanski/scb-problems",
        "problems_commit": overrides.get("problems_commit") or "unknown",
        "experiment_commit": experiment_commit,
        "started_at": summary_dict.get("started"),
        "ended_at": summary_dict.get("ended"),
        "status": "pending",
        "checkpoint_count_expected": 0,
        "checkpoint_count_completed": 0,
        "strict_survival_checkpoint": None,
        "artifact_root": rel_path(problem_dir, repo_root),
    }

    for checkpoint_dir in native_checkpoint_dirs(problem_dir):
        checkpoint_id = checkpoint_dir.name
        checkpoint_index = checkpoint_index_from_name(checkpoint_id) or len(checkpoint_rows) + 1
        evaluation = read_json_optional(checkpoint_dir / "evaluation.json")
        inference = read_json_optional(checkpoint_dir / "inference_result.json")
        quality = read_json_optional(
            checkpoint_dir / "quality_analysis" / "overall_quality.json"
        )
        diff = read_json_optional(checkpoint_dir / "diff.json")
        scbench = extract_scbench_metrics(evaluation)
        hidden_passed = hidden_passed_from_scbench(scbench)
        prior_regression_count = None
        if scbench:
            prior_regression_count = max(
                int(scbench["regression_total"]) - int(scbench["regression_passed"]),
                0,
            )
        cost_metrics = extract_cost_metrics(inference)
        started_at = inference.get("started") if isinstance(inference, dict) else None
        ended_at = inference.get("completed") if isinstance(inference, dict) else None
        checkpoint_row = {
            "schema_version": 1,
            "run_id": run_id,
            "condition_id": condition_id,
            "problem_id": problem_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint_index": checkpoint_index,
            "replicate_id": int(replicate_id),
            "model": model,
            "agent_harness": agent_harness,
            "agent_version": agent_version,
            "benchmark_commit": run_row["benchmark_commit"],
            "problems_commit": run_row["problems_commit"],
            "experiment_commit": experiment_commit,
            "started_at": started_at,
            "ended_at": ended_at,
            "status": "evaluated" if evaluation is not None else "missing_evaluation",
            "prompt_template_id": None,
            "prompt_hash": None,
            "context_hash": None,
            "feature_hash": None,
            "step_hash": None,
            "lock_manifest_hash": None,
            "lock_status": "not_applicable",
            "protocol_violation": False,
            "visible_acceptance_passed": None,
            "hidden_tests_passed": hidden_passed,
            "current_checkpoint_passed": hidden_passed,
            "prior_regression_count": prior_regression_count,
            "hidden_failure_after_visible_pass": None,
            "scbench": scbench,
            "scenario_results": [],
            "hidden_test_summary": scbench,
            "technical_metrics": {},
            "cost_metrics": cost_metrics,
            "artifact_paths": {
                "checkpoint_dir": rel_path(checkpoint_dir, repo_root),
                "evaluation": rel_path(checkpoint_dir / "evaluation.json", repo_root),
                "inference_result": rel_path(
                    checkpoint_dir / "inference_result.json",
                    repo_root,
                ),
                "diff": rel_path(checkpoint_dir / "diff.json", repo_root),
                "quality": rel_path(
                    checkpoint_dir / "quality_analysis" / "overall_quality.json",
                    repo_root,
                ),
            },
        }
        checkpoint_rows.append(checkpoint_row)
        technical_rows.append(
            flatten_quality_metrics(
                run_row=run_row,
                checkpoint_row=checkpoint_row,
                quality=quality,
                diff=diff,
                scbench=scbench,
                checkpoint_dir=checkpoint_dir,
                repo_root=repo_root,
            )
        )
        artifact_rows.append(
            {
                "schema_version": 1,
                "run_id": run_id,
                "problem_id": problem_id,
                "checkpoint_id": checkpoint_id,
                "condition_id": condition_id,
                "artifact_type": "native_checkpoint",
                "path": rel_path(checkpoint_dir, repo_root),
            }
        )

    run_row["checkpoint_count_expected"] = len(checkpoint_rows)
    run_row["checkpoint_count_completed"] = len(checkpoint_rows)
    run_row["status"] = native_run_status(
        run_info=run_info,
        checkpoint_rows=checkpoint_rows,
        run_dir=run_dir,
    )
    artifact_rows.append(
        {
            "schema_version": 1,
            "run_id": run_id,
            "problem_id": problem_id,
            "condition_id": condition_id,
            "artifact_type": "native_problem_run",
            "path": rel_path(problem_dir, repo_root),
        }
    )
    return run_row, checkpoint_rows, technical_rows, artifact_rows


def export_native_partial(
    *,
    run_dir: Path,
    repo_root: Path,
    experiment_commit: str,
    overrides: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    config = read_yaml_optional(run_dir / "config.yaml")
    problem_id = overrides.get("problem_id") or problem_from_config(config) or "unknown"
    condition_id = overrides.get("condition_id") or guess_condition_id(run_dir) or "UNKNOWN"
    replicate_id = overrides.get("replicate_id") or guess_replicate_id(run_dir) or 1
    run_id = overrides.get("run_id") or f"{run_dir.name}-{problem_id}"
    run_row = {
        "schema_version": 1,
        "run_id": run_id,
        "condition_id": condition_id,
        "problem_id": problem_id,
        "replicate_id": int(replicate_id),
        "model": overrides.get("model") or model_name_from_config(config) or "unknown",
        "agent_harness": overrides.get("agent_harness") or agent_id_from_config(config) or "unknown",
        "agent_version": overrides.get("agent_version") or agent_version_from_config(config),
        "benchmark_repo": "SprocketLab/slop-code-bench",
        "benchmark_commit": overrides.get("benchmark_commit") or experiment_commit,
        "problems_repo": "gabeorlanski/scb-problems",
        "problems_commit": overrides.get("problems_commit") or "unknown",
        "experiment_commit": experiment_commit,
        "started_at": None,
        "ended_at": None,
        "status": "infrastructure_failure",
        "checkpoint_count_expected": 0,
        "checkpoint_count_completed": 0,
        "strict_survival_checkpoint": None,
        "artifact_root": rel_path(run_dir, repo_root),
    }
    artifact_rows = [
        {
            "schema_version": 1,
            "run_id": run_id,
            "problem_id": problem_id,
            "condition_id": condition_id,
            "artifact_type": "native_partial_run",
            "path": rel_path(run_dir, repo_root),
        }
    ]
    if (run_dir / "run_agent.log").is_file():
        artifact_rows.append(
            {
                "schema_version": 1,
                "run_id": run_id,
                "problem_id": problem_id,
                "condition_id": condition_id,
                "artifact_type": "native_run_log",
                "path": rel_path(run_dir / "run_agent.log", repo_root),
            }
        )
    return [run_row], [], [], artifact_rows


def export_native(
    *,
    run_dir: Path,
    repo_root: Path,
    experiment_commit: str,
    overrides: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    problem_dirs = discover_native_problem_dirs(run_dir)
    if not problem_dirs:
        return export_native_partial(
            run_dir=run_dir,
            repo_root=repo_root,
            experiment_commit=experiment_commit,
            overrides=overrides,
        )

    run_rows: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    technical_rows: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []
    for problem_dir in problem_dirs:
        run_row, checkpoints, technical, artifacts = export_native_problem(
            run_dir=run_dir,
            problem_dir=problem_dir,
            repo_root=repo_root,
            experiment_commit=experiment_commit,
            overrides=overrides,
        )
        run_rows.append(run_row)
        checkpoint_rows.extend(checkpoints)
        technical_rows.extend(technical)
        artifact_rows.extend(artifacts)
    return run_rows, checkpoint_rows, technical_rows, artifact_rows


def is_dry_run_dir(path: Path) -> bool:
    return (path / "run.json").is_file() and (path / "checkpoints.jsonl").is_file()


def discover_input_runs(roots: list[Path]) -> list[Path]:
    wrapper_runs: dict[Path, None] = {}
    native_runs: dict[Path, None] = {}
    for root in roots:
        if is_dry_run_dir(root):
            wrapper_runs[root.resolve()] = None
            continue
        if (root / "config.yaml").is_file():
            native_runs[root.resolve()] = None
            continue
        for run_json in root.rglob("run.json"):
            run_dir = run_json.parent
            if is_dry_run_dir(run_dir):
                wrapper_runs[run_dir.resolve()] = None
        for config_path in root.rglob("config.yaml"):
            candidate = config_path.parent
            if (
                (candidate / "environment.yaml").is_file()
                or (candidate / "run_agent.log").is_file()
                or (candidate / "problem_catalog.json").is_file()
            ):
                native_runs[candidate.resolve()] = None

    wrapper_roots = list(wrapper_runs)
    for native_run in list(native_runs):
        if any(native_run.is_relative_to(wrapper_root) for wrapper_root in wrapper_roots):
            native_runs.pop(native_run, None)
    return sorted({**wrapper_runs, **native_runs})


def export_runs(
    *,
    input_runs: list[Path],
    output_dir: Path,
    repo_root: Path,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    experiment_commit = current_git_commit(repo_root)
    run_rows: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    technical_rows: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []

    for run_dir in input_runs:
        if is_dry_run_dir(run_dir):
            runs, checkpoints, technical, artifacts = export_dry_run(
                run_dir=run_dir,
                repo_root=repo_root,
            )
        else:
            runs, checkpoints, technical, artifacts = export_native(
                run_dir=run_dir,
                repo_root=repo_root,
                experiment_commit=experiment_commit,
                overrides=overrides,
            )
        run_rows.extend(runs)
        checkpoint_rows.extend(checkpoints)
        technical_rows.extend(technical)
        artifact_rows.extend(artifacts)

    for row in run_rows:
        require_fields(row, RUN_FIELDS, f"run {row.get('run_id')}")
    for row in checkpoint_rows:
        require_fields(row, CHECKPOINT_FIELDS, f"checkpoint {row.get('checkpoint_id')}")

    write_jsonl(output_dir / "runs.jsonl", run_rows)
    write_jsonl(output_dir / "checkpoints.jsonl", checkpoint_rows)
    write_jsonl(output_dir / "technical_metrics.jsonl", technical_rows)
    write_jsonl(output_dir / "artifacts.jsonl", artifact_rows)
    write_json(
        output_dir / "export_summary.json",
        {
            "schema_version": 1,
            "generated_at": utc_now(),
            "input_runs": [path.as_posix() for path in input_runs],
            "run_count": len(run_rows),
            "checkpoint_count": len(checkpoint_rows),
            "technical_metric_count": len(technical_rows),
            "artifact_count": len(artifact_rows),
        },
    )
    return {
        "run_count": len(run_rows),
        "checkpoint_count": len(checkpoint_rows),
        "technical_metric_count": len(technical_rows),
        "artifact_count": len(artifact_rows),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-run",
        action="append",
        type=Path,
        default=[],
        help="Run artifact directory to export. Repeatable.",
    )
    parser.add_argument(
        "--input-root",
        action="append",
        type=Path,
        default=[],
        help="Root to scan for run artifact directories. Repeatable.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--condition-id", choices=["C0", "C1", "C2", "C3", "C4", "C5"])
    parser.add_argument("--problem-id")
    parser.add_argument("--replicate-id", type=int)
    parser.add_argument("--model")
    parser.add_argument("--agent-harness")
    parser.add_argument("--agent-version")
    parser.add_argument("--benchmark-commit")
    parser.add_argument("--problems-commit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = repo_root_from_script()
    inputs = [path.resolve() for path in args.input_run]
    inputs.extend(discover_input_runs([path.resolve() for path in args.input_root]))
    unique_inputs = sorted(dict.fromkeys(inputs))
    if not unique_inputs:
        raise ExportError("No input run directories were provided or discovered")

    overrides = {
        "run_id": args.run_id,
        "condition_id": args.condition_id,
        "problem_id": args.problem_id,
        "replicate_id": args.replicate_id,
        "model": args.model,
        "agent_harness": args.agent_harness,
        "agent_version": args.agent_version,
        "benchmark_commit": args.benchmark_commit,
        "problems_commit": args.problems_commit,
    }
    summary = export_runs(
        input_runs=unique_inputs,
        output_dir=args.output_dir.resolve(),
        repo_root=repo_root,
        overrides=overrides,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
