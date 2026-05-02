#!/usr/bin/env python3
"""Build an auditable SCBench problem-selection inventory.

The script intentionally emits metadata, counts, hashes, runtimes, and
aggregate pass/fail summaries only. It does not export checkpoint prose, pytest
test names, hidden-test assertions, or fixture contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_FULL_PILOT = {
    "code_search",
    "file_backup",
    "log_query",
    "file_merger",
    "textdrop",
    "migrate_configs",
}
DEFAULT_MVP = {"code_search", "file_backup"}
HEAVY_DEPENDENCIES = {
    "pyarrow",
    "pandas",
    "numpy",
    "playwright",
    "selenium",
}
SERVICE_TAGS = {"api", "rest", "http", "http-server", "web", "server"}
FILE_TAGS = {
    "file-io",
    "file-systems",
    "jsonl",
    "yaml",
    "csv",
    "parquet",
    "data-transformation",
}
QUERY_TAGS = {"query-language", "sql", "search", "xpath", "css-selectors"}


@dataclass(frozen=True)
class RuntimeContext:
    repo_root: Path
    problems_dir: Path
    env_config: Path
    max_checkpoints: int | None


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def default_problems_dir(repo_root: Path) -> Path:
    env_path = os.environ.get("SCBENCH_PROBLEMS_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return (repo_root.parent / "scb-problems").resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected YAML object at {path}")
    return loaded


def git_commit(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["/usr/bin/git", "rev-parse", "HEAD"],
            cwd=path,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_problem_dirs(problems_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in problems_dir.iterdir()
        if path.is_dir() and (path / "config.yaml").exists()
    )


def ordered_checkpoints(config: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    raw = config.get("checkpoints") or {}
    if isinstance(raw, list):
        items = [(str(name), {}) for name in raw]
    elif isinstance(raw, dict):
        items = [
            (str(name), value if isinstance(value, dict) else {})
            for name, value in raw.items()
        ]
    else:
        items = []
    return sorted(
        items,
        key=lambda item: (
            int(item[1].get("order", 10_000)),
            item[0],
        ),
    )


def spec_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "bytes": 0,
            "lines": 0,
            "words": 0,
            "code_fence_count": 0,
            "example_signal_count": 0,
            "sha256": None,
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    return {
        "exists": True,
        "bytes": path.stat().st_size,
        "lines": len(text.splitlines()),
        "words": len(text.split()),
        "code_fence_count": text.count("```"),
        "example_signal_count": sum(
            lowered.count(token)
            for token in ("example", "given", "when", "then", "input", "output")
        ),
        "sha256": sha256_file(path),
    }


def checkpoint_inventory(
    problem_dir: Path,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    checkpoints = []
    for name, checkpoint in ordered_checkpoints(config):
        solution_dir = problem_dir / "solutions" / name
        include_prior = checkpoint.get("include_prior_tests", True)
        stats = spec_stats(problem_dir / f"{name}.md")
        checkpoints.append(
            {
                "checkpoint_id": name,
                "order": int(checkpoint.get("order", len(checkpoints) + 1)),
                "state": checkpoint.get("state", "unknown"),
                "version": checkpoint.get("version"),
                "include_prior_tests": bool(include_prior),
                "timeout_seconds": checkpoint.get(
                    "timeout",
                    config.get("timeout"),
                ),
                "spec": stats,
                "has_test_file": (
                    problem_dir / "tests" / f"test_{name}.py"
                ).exists(),
                "has_solution_dir": solution_dir.exists(),
                "solution_file_count": count_files(solution_dir)
                if solution_dir.exists()
                else 0,
            }
        )
    return checkpoints


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for child in path.rglob("*") if child.is_file())


def lower_set(values: list[Any]) -> set[str]:
    return {str(value).lower() for value in values}


def classify_boundary(config: dict[str, Any]) -> list[str]:
    tags = lower_set(config.get("tags") or [])
    deps = lower_set(config.get("test_dependencies") or [])
    category = str(config.get("category", "")).lower()
    fields = tags | deps | {category}

    out: list[str] = []
    if "cli-tools" in fields:
        out.append("cli")
    if fields & SERVICE_TAGS or "httpx" in deps:
        out.append("api_service")
    if fields & FILE_TAGS or "file" in category:
        out.append("file_processing")
    if fields & QUERY_TAGS:
        out.append("query_language")
    if "database" in category or "sqlite" in fields:
        out.append("database")
    if not out:
        out.append("other")
    return out


def selection_assessment(
    problem_id: str,
    config: dict[str, Any],
    checkpoints: list[dict[str, Any]],
) -> dict[str, Any]:
    tags = lower_set(config.get("tags") or [])
    deps = lower_set(config.get("test_dependencies") or [])
    boundary = classify_boundary(config)
    disabled_prior = [
        item["checkpoint_id"]
        for item in checkpoints
        if not item["include_prior_tests"]
    ]
    missing_solutions = [
        item["checkpoint_id"] for item in checkpoints if not item["has_solution_dir"]
    ]

    risk_flags: list[str] = []
    if disabled_prior:
        risk_flags.append("prior_tests_disabled")
    if "api_service" in boundary:
        risk_flags.append("service_lifecycle")
    if deps & HEAVY_DEPENDENCIES:
        risk_flags.append("heavy_dependency")
    if config.get("difficulty") == "Hard":
        risk_flags.append("hard_problem")
    if len(checkpoints) > 6:
        risk_flags.append("long_trajectory")
    if missing_solutions:
        risk_flags.append("missing_checkpoint_solution")

    score = 0
    if "cli" in boundary:
        score += 3
    if "file_processing" in boundary:
        score += 2
    if "query_language" in boundary:
        score += 2
    if "api_service" in boundary:
        score += 1
    if 4 <= len(checkpoints) <= 6:
        score += 2
    if not disabled_prior:
        score += 2
    if config.get("difficulty") == "Easy":
        score += 1
    if deps & HEAVY_DEPENDENCIES:
        score -= 1
    if "service_lifecycle" in risk_flags:
        score -= 1
    if config.get("difficulty") == "Hard":
        score -= 3
    if len(checkpoints) > 6:
        score -= 2
    if missing_solutions:
        score -= 2

    notes = []
    if "httpx" in deps:
        notes.append("requires service/API runtime handling")
    if "pyarrow" in deps:
        notes.append("check parquet/pyarrow runtime cost")
    if "cli-tools" in tags:
        notes.append("observable CLI boundary")
    if disabled_prior:
        notes.append("native config disables prior tests on some checkpoints")

    return {
        "boundary_tags": boundary,
        "score": score,
        "risk_flags": risk_flags,
        "notes": notes,
        "recommended_mvp": problem_id in DEFAULT_MVP,
        "recommended_full_pilot": problem_id in DEFAULT_FULL_PILOT,
    }


def build_problem_record(
    problem_dir: Path,
    problems_dir: Path,
    generated_at: str,
    problem_commit: str | None,
) -> dict[str, Any]:
    config = load_yaml(problem_dir / "config.yaml")
    checkpoints = checkpoint_inventory(problem_dir, config)
    tests_dir = problem_dir / "tests"
    checkpoint_tests = sorted(tests_dir.glob("test_checkpoint_*.py"))
    disabled_prior = [
        item["checkpoint_id"]
        for item in checkpoints
        if not item["include_prior_tests"]
    ]
    spec_items = [item["spec"] for item in checkpoints]

    problem_id = str(config.get("name") or problem_dir.name)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "problem_repo_commit": problem_commit,
        "problem_id": problem_id,
        "problem_dir": str(problem_dir.relative_to(problems_dir)),
        "config_sha256": sha256_file(problem_dir / "config.yaml"),
        "category": config.get("category"),
        "difficulty": config.get("difficulty"),
        "entry_file": config.get("entry_file"),
        "timeout_seconds": config.get("timeout"),
        "tags": config.get("tags") or [],
        "test_dependencies": config.get("test_dependencies") or [],
        "static_assets": sorted((config.get("static_assets") or {}).keys()),
        "checkpoint_count": len(checkpoints),
        "checkpoints": checkpoints,
        "include_prior_tests": {
            "all_enabled": not disabled_prior,
            "disabled_checkpoint_ids": disabled_prior,
            "enabled_count": len(checkpoints) - len(disabled_prior),
            "disabled_count": len(disabled_prior),
        },
        "tests": {
            "checkpoint_test_file_count": len(checkpoint_tests),
            "has_conftest": (tests_dir / "conftest.py").exists(),
            "helper_file_count": max(0, count_files(tests_dir) - len(checkpoint_tests)),
        },
        "solutions": {
            "per_checkpoint_solution_count": sum(
                1 for item in checkpoints if item["has_solution_dir"]
            ),
            "missing_solution_checkpoint_ids": [
                item["checkpoint_id"]
                for item in checkpoints
                if not item["has_solution_dir"]
            ],
            "has_legacy_solution_dir": (problem_dir / "solution").exists(),
        },
        "spec_summary": {
            "total_bytes": sum(int(item["bytes"]) for item in spec_items),
            "total_lines": sum(int(item["lines"]) for item in spec_items),
            "total_words": sum(int(item["words"]) for item in spec_items),
            "total_code_fences": sum(
                int(item["code_fence_count"]) for item in spec_items
            ),
            "total_example_signals": sum(
                int(item["example_signal_count"]) for item in spec_items
            ),
        },
        "selection": selection_assessment(problem_id, config, checkpoints),
        "reference_runtime_status": "not_measured",
        "reference_runtime_seconds": None,
        "reference_runtime_infrastructure_failures": None,
        "reference_runtime_checkpoint_results": [],
    }


def load_runtime_imports(repo_root: Path) -> dict[str, Any]:
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from slop_code.entrypoints.config import loader as config_loader
    from slop_code.evaluation.config import ProblemConfig
    from slop_code.evaluation.pytest_runner import run_checkpoint_pytest

    return {
        "config_loader": config_loader,
        "ProblemConfig": ProblemConfig,
        "run_checkpoint_pytest": run_checkpoint_pytest,
    }


def copy_solution(solution_dir: Path, destination: Path) -> None:
    shutil.copytree(solution_dir, destination, dirs_exist_ok=True)


def measure_reference_runtime(
    record: dict[str, Any],
    context: RuntimeContext,
) -> None:
    imports = load_runtime_imports(context.repo_root)
    problem_path = context.problems_dir / record["problem_dir"]
    problem = imports["ProblemConfig"].from_yaml(problem_path)
    environment = imports["config_loader"].resolve_environment(context.env_config)

    checkpoint_results: list[dict[str, Any]] = []
    total_runtime = 0.0
    infrastructure_failures = 0

    ordered = list(problem.iterate_checkpoint_items())
    if context.max_checkpoints is not None:
        ordered = ordered[: context.max_checkpoints]

    for idx, (checkpoint_name, checkpoint) in enumerate(ordered, start=1):
        solution_dir = problem_path / "solutions" / checkpoint_name
        if not solution_dir.exists():
            checkpoint_results.append(
                {
                    "checkpoint_id": checkpoint_name,
                    "checkpoint_index": idx,
                    "status": "missing_solution",
                    "runtime_seconds": None,
                    "evaluation_duration_seconds": None,
                    "infrastructure_failure": True,
                }
            )
            infrastructure_failures += 1
            continue

        with tempfile.TemporaryDirectory(
            prefix=f"scb-ref-{record['problem_id']}-{checkpoint_name}-"
        ) as temp_dir:
            snapshot_dir = Path(temp_dir) / "snapshot"
            copy_solution(solution_dir, snapshot_dir)
            started = time.perf_counter()
            try:
                result = imports["run_checkpoint_pytest"](
                    submission_path=snapshot_dir,
                    problem=problem,
                    checkpoint=checkpoint,
                    env_spec=environment,
                )
            except Exception as exc:  # noqa: BLE001 - inventory must continue
                elapsed = time.perf_counter() - started
                checkpoint_results.append(
                    {
                        "checkpoint_id": checkpoint_name,
                        "checkpoint_index": idx,
                        "status": "error",
                        "runtime_seconds": round(elapsed, 3),
                        "evaluation_duration_seconds": None,
                        "infrastructure_failure": True,
                        "error_type": type(exc).__name__,
                    }
                )
                total_runtime += elapsed
                infrastructure_failures += 1
                continue

            elapsed = time.perf_counter() - started
            total_runtime += elapsed
            total_counts = dict(result.total_counts)
            pass_counts = dict(result.pass_counts)
            total_tests = sum(total_counts.values()) or result.pytest_collected
            passed_tests = sum(pass_counts.values())
            core_total = total_counts.get("Core", 0)
            core_passed = pass_counts.get("Core", 0)
            strict_pass_rate = (
                passed_tests / total_tests if total_tests else 0.0
            )
            core_pass_rate = core_passed / core_total if core_total else 0.0
            if result.infrastructure_failure:
                infrastructure_failures += 1
            checkpoint_results.append(
                {
                    "checkpoint_id": checkpoint_name,
                    "checkpoint_index": idx,
                    "status": "completed",
                    "runtime_seconds": round(elapsed, 3),
                    "evaluation_duration_seconds": round(result.duration, 3),
                    "infrastructure_failure": bool(
                        result.infrastructure_failure
                    ),
                    "hidden_total_tests": total_tests,
                    "hidden_passed_tests": passed_tests,
                    "hidden_strict_pass_rate": round(strict_pass_rate, 4),
                    "hidden_core_pass_rate": round(core_pass_rate, 4),
                }
            )

    measured = [row for row in checkpoint_results if row["runtime_seconds"]]
    if not checkpoint_results:
        status = "not_measured"
    elif infrastructure_failures:
        status = "partial" if measured else "failed"
    else:
        status = "measured"

    record["reference_runtime_status"] = status
    record["reference_runtime_seconds"] = (
        round(total_runtime, 3) if measured else None
    )
    record["reference_runtime_infrastructure_failures"] = infrastructure_failures
    record["reference_runtime_measured_at"] = utc_now()
    record["reference_runtime_checkpoint_results"] = checkpoint_results


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def load_existing_runtime(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    fields = {
        "reference_runtime_status",
        "reference_runtime_seconds",
        "reference_runtime_infrastructure_failures",
        "reference_runtime_measured_at",
        "reference_runtime_checkpoint_results",
    }
    out: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            problem_id = record.get("problem_id")
            if not isinstance(problem_id, str):
                continue
            runtime = {field: record.get(field) for field in fields}
            if runtime.get("reference_runtime_status") != "not_measured":
                out[problem_id] = runtime
    return out


def preserve_existing_runtime(
    records: list[dict[str, Any]],
    existing_runtime: dict[str, dict[str, Any]],
    selected_for_measurement: set[str],
) -> None:
    for record in records:
        problem_id = record["problem_id"]
        if problem_id in selected_for_measurement:
            continue
        runtime = existing_runtime.get(problem_id)
        if runtime:
            record.update(runtime)


def render_problem_row(record: dict[str, Any]) -> str:
    selection = record["selection"]
    runtime = record["reference_runtime_seconds"]
    runtime_text = f"{runtime:.1f}s" if isinstance(runtime, int | float) else "-"
    risks = ", ".join(selection["risk_flags"]) or "-"
    boundary = ", ".join(selection["boundary_tags"])
    return (
        f"| `{record['problem_id']}` | {boundary} | "
        f"{record['difficulty']} | {record['checkpoint_count']} | "
        f"{runtime_text} | {selection['score']} | {risks} |"
    )


def write_report(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    full = [r for r in records if r["selection"]["recommended_full_pilot"]]
    mvp = [r for r in records if r["selection"]["recommended_mvp"]]
    ranked = sorted(
        records,
        key=lambda r: (-int(r["selection"]["score"]), r["problem_id"]),
    )

    lines = [
        "# Problem Selection Inventory Report",
        "",
        f"Generated at: {utc_now()}",
        "",
        "## MVP Recommendation",
        "",
        "Use `code_search` and `file_backup` for the minimum viable pilot.",
        "",
        "| Problem | Boundary | Difficulty | Checkpoints | Ref runtime | Score | Risks |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
        *[render_problem_row(record) for record in sorted(mvp, key=lambda r: r["problem_id"])],
        "",
        "## First Full Pilot Recommendation",
        "",
        "Use `code_search`, `file_backup`, `log_query`, `file_merger`, `textdrop`, and `migrate_configs` for the first 5-6 problem pilot.",
        "",
        "| Problem | Boundary | Difficulty | Checkpoints | Ref runtime | Score | Risks |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
        *[render_problem_row(record) for record in sorted(full, key=lambda r: r["problem_id"])],
        "",
        "## Top Ranked Problems By Metadata Heuristic",
        "",
        "| Problem | Boundary | Difficulty | Checkpoints | Ref runtime | Score | Risks |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
        *[render_problem_row(record) for record in ranked[:12]],
        "",
        "## Notes",
        "",
        "- Runtime fields are populated only for requested runtime-probe problems.",
        "- `xjq` remains a strong alternate, but the local reference-runtime probe showed core-pass mismatches that should be resolved before using it in the MVP.",
        "- The inventory intentionally excludes checkpoint prose, test names, fixture source, and assertion details.",
        "- Reference-runtime pass rates are diagnostic only; hidden SCBench evaluation remains the final judge during actual experiment runs.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--problems-dir",
        type=Path,
        default=default_problems_dir(repo_root),
        help="Flat scb-problems checkout. Defaults to SCBENCH_PROBLEMS_PATH or ../scb-problems.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "experiment" / "results" / "problem_inventory.jsonl",
        help="JSONL inventory output path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=repo_root
        / "experiment"
        / "results"
        / "problem_selection_report.md",
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--measure-reference-runtime",
        action="store_true",
        help="Run native pytest evaluation against reference solution snapshots.",
    )
    parser.add_argument(
        "--runtime-problem",
        action="append",
        default=[],
        help="Problem to runtime-probe. Repeatable. Defaults to first-pilot problems when measuring.",
    )
    parser.add_argument(
        "--env-config",
        type=Path,
        default=repo_root / "configs" / "environments" / "local-py.yaml",
        help="SCBench environment config for reference runtime probes.",
    )
    parser.add_argument(
        "--max-runtime-checkpoints",
        type=int,
        default=None,
        help="Optional cap for runtime-probe checkpoints per problem.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Do not write the Markdown report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = repo_root_from_script()
    problems_dir = args.problems_dir.expanduser().resolve()
    if not problems_dir.exists():
        print(f"Problems directory not found: {problems_dir}", file=sys.stderr)
        return 2

    generated_at = utc_now()
    problem_commit = git_commit(problems_dir)
    records = [
        build_problem_record(path, problems_dir, generated_at, problem_commit)
        for path in discover_problem_dirs(problems_dir)
    ]

    if args.measure_reference_runtime:
        selected = set(args.runtime_problem or sorted(DEFAULT_FULL_PILOT))
        existing_runtime = load_existing_runtime(args.output)
        preserve_existing_runtime(records, existing_runtime, selected)
        context = RuntimeContext(
            repo_root=repo_root,
            problems_dir=problems_dir,
            env_config=args.env_config.expanduser().resolve(),
            max_checkpoints=args.max_runtime_checkpoints,
        )
        for record in records:
            if record["problem_id"] in selected:
                print(
                    f"Measuring reference runtime for {record['problem_id']}...",
                    file=sys.stderr,
                )
                measure_reference_runtime(record, context)

    records = sorted(records, key=lambda item: item["problem_id"])
    write_jsonl(args.output, records)
    if not args.no_report:
        write_report(args.report, records)

    print(f"Wrote {len(records)} problem records to {args.output}")
    if not args.no_report:
        print(f"Wrote report to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
