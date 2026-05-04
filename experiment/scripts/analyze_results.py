#!/usr/bin/env python3
"""Compute pilot drift summaries from normalized experiment JSONL tables."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import UTC
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

TECHNICAL_SLOPE_FIELDS = [
    "loc",
    "sloc",
    "verbosity",
    "erosion",
    "cc_max",
    "cc_mean",
    "cc_high_count",
    "clone_lines",
    "cloned_pct",
    "lines_added",
    "lines_removed",
    "files_changed",
    "acceptance_runtime_ms",
    "hidden_eval_runtime_ms",
]
PARAMETRIZED_TEST_RE = re.compile(r"\[.*\]$")


class AnalysisError(ValueError):
    """Raised when result tables cannot be analyzed."""


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


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
                raise AnalysisError(f"Expected JSON object at {path}:{line_number}")
            rows.append(payload)
    return rows


def read_json_optional(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise AnalysisError(f"Expected JSON object at {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def bool_label(value: Any) -> str:
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    return "n/a"


def slope(points: list[tuple[float, float]]) -> float | None:
    if len(points) < 2:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_mean = mean(xs)
    y_mean = mean(ys)
    denominator = sum((value - x_mean) ** 2 for value in xs)
    if denominator == 0:
        return None
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in points)
    return numerator / denominator


def checkpoints_by_run(
    checkpoint_rows: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in checkpoint_rows:
        grouped[str(row["run_id"])].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: int(row.get("checkpoint_index") or 10_000))
    return dict(grouped)


def technical_by_run(
    technical_rows: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in technical_rows:
        grouped[str(row["run_id"])].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: int(row.get("checkpoint_index") or 10_000))
    return dict(grouped)


def strict_survival(
    *, run_row: dict[str, Any], checkpoint_rows: list[dict[str, Any]]
) -> tuple[str | None, int, int]:
    expected = int(run_row.get("checkpoint_count_expected") or len(checkpoint_rows))
    rows_by_index = {
        int(row.get("checkpoint_index") or index + 1): row
        for index, row in enumerate(checkpoint_rows)
    }
    last_checkpoint_id: str | None = None
    last_index = 0
    missing_count = 0
    for index in range(1, expected + 1):
        row = rows_by_index.get(index)
        if row is None:
            missing_count += 1
            break
        if row.get("protocol_violation") is True:
            break
        if row.get("hidden_tests_passed") is not True:
            break
        if row.get("condition_id") == "C2":
            if row.get("visible_acceptance_passed") is not True:
                break
            if row.get("c2_feedback_status") != "observed":
                break
        last_checkpoint_id = str(row.get("checkpoint_id"))
        last_index = index
    missing_count += max(expected - len(rows_by_index), 0)
    return last_checkpoint_id, last_index, missing_count


def trajectory_summary(
    *, run_row: dict[str, Any], checkpoint_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    survival_checkpoint, survival_index, missing_count = strict_survival(
        run_row=run_row,
        checkpoint_rows=checkpoint_rows,
    )
    regression_values = [
        int(row["prior_regression_count"])
        for row in checkpoint_rows
        if isinstance(row.get("prior_regression_count"), int)
    ]
    regression_failures = sum(1 for value in regression_values if value > 0)
    hidden_rows = [
        row for row in checkpoint_rows if row.get("hidden_tests_passed") is not None
    ]
    hidden_passes = sum(1 for row in hidden_rows if row.get("hidden_tests_passed") is True)
    visible_rows = [
        row
        for row in checkpoint_rows
        if row.get("visible_acceptance_passed") is not None
    ]
    hidden_failure_after_visible_pass = sum(
        1 for row in checkpoint_rows if row.get("hidden_failure_after_visible_pass") is True
    )
    c2_feedback_observed_count = sum(
        1 for row in checkpoint_rows if row.get("c2_feedback_status") == "observed"
    )
    lock_violation_count = sum(
        1 for row in checkpoint_rows if row.get("protocol_violation") is True
    )
    expected = int(run_row.get("checkpoint_count_expected") or len(checkpoint_rows))
    return {
        "run_id": run_row["run_id"],
        "condition_id": run_row["condition_id"],
        "problem_id": run_row["problem_id"],
        "replicate_id": run_row["replicate_id"],
        "status": run_row.get("status"),
        "checkpoint_count_expected": expected,
        "checkpoint_count_completed": len(checkpoint_rows),
        "missing_checkpoint_count": missing_count,
        "strict_survival_checkpoint": survival_checkpoint,
        "strict_survival_index": survival_index,
        "hidden_checkpoint_pass_rate": safe_divide(hidden_passes, len(hidden_rows)),
        "regression_rate": safe_divide(regression_failures, len(regression_values)),
        "regression_failure_checkpoint_count": regression_failures,
        "hidden_failure_after_visible_pass_count": hidden_failure_after_visible_pass,
        "visible_acceptance_checkpoint_count": len(visible_rows),
        "c2_feedback_observed_count": c2_feedback_observed_count,
        "lock_violation_count": lock_violation_count,
        "not_evaluated": not hidden_rows,
    }


def safe_divide(numerator: int | float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def repo_root_from_results_dir(results_dir: Path) -> Path:
    for candidate in [results_dir.resolve(), *results_dir.resolve().parents]:
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd().resolve()


def resolve_artifact_path(path_text: Any, *, repo_root: Path) -> Path | None:
    if not isinstance(path_text, str) or not path_text:
        return None
    path = Path(path_text)
    if path.is_absolute():
        return path
    return repo_root / path


def hidden_summary(row: dict[str, Any]) -> dict[str, Any]:
    summary = row.get("hidden_test_summary")
    if isinstance(summary, dict):
        return summary
    scbench = row.get("scbench")
    if isinstance(scbench, dict):
        return scbench
    return {}


def normalized_test_label(test_name: str) -> str:
    return PARAMETRIZED_TEST_RE.sub("", test_name)


def failed_cluster_labels(evaluation: dict[str, Any] | None) -> list[str]:
    if evaluation is None:
        return []
    tests = evaluation.get("tests")
    if not isinstance(tests, dict):
        return []
    labels: set[str] = set()
    for group_name, group_payload in tests.items():
        if not isinstance(group_payload, dict):
            continue
        failed = group_payload.get("failed")
        if not isinstance(failed, list):
            continue
        for test_name in failed:
            if not isinstance(test_name, str):
                continue
            labels.add(f"{group_name}:{normalized_test_label(test_name)}")
    return sorted(labels)


def evaluation_for_checkpoint(
    row: dict[str, Any], *, repo_root: Path
) -> dict[str, Any] | None:
    artifact_paths = row.get("artifact_paths")
    if not isinstance(artifact_paths, dict):
        return None
    evaluation_path = resolve_artifact_path(
        artifact_paths.get("evaluation"),
        repo_root=repo_root,
    )
    return read_json_optional(evaluation_path)


def hidden_subtest_counts(row: dict[str, Any]) -> tuple[int | None, int | None]:
    summary = hidden_summary(row)
    passed = summary.get("passed_tests")
    total = summary.get("total_tests")
    if isinstance(passed, int) and isinstance(total, int):
        return passed, total
    rate = as_number(summary.get("strict_pass_rate"))
    collected = summary.get("pytest_collected")
    if rate is not None and isinstance(collected, int):
        return int(round(rate * collected)), collected
    return None, None


def checkpoint_pass_rate(row: dict[str, Any]) -> float | None:
    passed, total = hidden_subtest_counts(row)
    if passed is None or total is None:
        return None
    return safe_divide(passed, total)


def near_miss_rows(
    checkpoint_rows: list[dict[str, Any]],
    *,
    repo_root: Path,
) -> list[dict[str, Any]]:
    pass_rates: dict[tuple[str, str, int, int], float | None] = {}
    for row in checkpoint_rows:
        problem_id = str(row.get("problem_id"))
        checkpoint_index = int(row.get("checkpoint_index") or 0)
        replicate_id = int(row.get("replicate_id") or 0)
        condition_id = str(row.get("condition_id"))
        pass_rates[(condition_id, problem_id, checkpoint_index, replicate_id)] = (
            checkpoint_pass_rate(row)
        )

    rows: list[dict[str, Any]] = []
    for row in sorted(
        checkpoint_rows,
        key=lambda item: (
            str(item.get("problem_id")),
            int(item.get("checkpoint_index") or 0),
            int(item.get("replicate_id") or 0),
            str(item.get("condition_id")),
        ),
    ):
        if row.get("hidden_tests_passed") is not False:
            continue
        problem_id = str(row.get("problem_id"))
        checkpoint_index = int(row.get("checkpoint_index") or 0)
        replicate_id = int(row.get("replicate_id") or 0)
        condition_id = str(row.get("condition_id"))
        passed, total = hidden_subtest_counts(row)
        pass_rate = checkpoint_pass_rate(row)
        baseline_c0 = pass_rates.get(("C0", problem_id, checkpoint_index, replicate_id))
        baseline_c1 = pass_rates.get(("C1", problem_id, checkpoint_index, replicate_id))
        labels = failed_cluster_labels(
            evaluation_for_checkpoint(row, repo_root=repo_root)
        )
        delta_vs_c0 = (
            pass_rate - baseline_c0
            if condition_id in {"C1", "C2"}
            and pass_rate is not None
            and baseline_c0 is not None
            else None
        )
        delta_vs_c1 = (
            pass_rate - baseline_c1
            if condition_id == "C2"
            and pass_rate is not None
            and baseline_c1 is not None
            else None
        )
        rows.append(
            {
                "condition_id": condition_id,
                "problem_id": problem_id,
                "checkpoint_id": row.get("checkpoint_id"),
                "checkpoint_index": checkpoint_index,
                "replicate_id": replicate_id,
                "run_id": row.get("run_id"),
                "visible_acceptance_passed": row.get("visible_acceptance_passed"),
                "hidden_failure_after_visible_pass": row.get(
                    "hidden_failure_after_visible_pass"
                ),
                "hidden_subtests_passed": passed,
                "hidden_subtests_total": total,
                "hidden_subtests_failed": (total - passed)
                if passed is not None and total is not None
                else None,
                "hidden_subtest_pass_rate": pass_rate,
                "delta_vs_c0_pass_rate": delta_vs_c0,
                "delta_vs_c1_pass_rate": delta_vs_c1,
                "failed_hidden_cluster_count": len(labels),
                "failed_hidden_cluster_labels": labels,
                "failed_hidden_cluster_label_text": ", ".join(labels),
            }
        )
    return rows


def aggregate_near_misses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                str(row["condition_id"]),
                str(row["problem_id"]),
                int(row["checkpoint_index"]),
            )
        ].append(row)
    aggregates: list[dict[str, Any]] = []
    for (condition_id, problem_id, checkpoint_index), group in sorted(grouped.items()):
        pass_rates = [
            float(row["hidden_subtest_pass_rate"])
            for row in group
            if row.get("hidden_subtest_pass_rate") is not None
        ]
        failed_counts = [
            float(row["hidden_subtests_failed"])
            for row in group
            if row.get("hidden_subtests_failed") is not None
        ]
        cluster_counts = [
            float(row["failed_hidden_cluster_count"])
            for row in group
            if row.get("failed_hidden_cluster_count") is not None
        ]
        deltas_c0 = [
            float(row["delta_vs_c0_pass_rate"])
            for row in group
            if row.get("delta_vs_c0_pass_rate") is not None
        ]
        deltas_c1 = [
            float(row["delta_vs_c1_pass_rate"])
            for row in group
            if row.get("delta_vs_c1_pass_rate") is not None
        ]
        aggregates.append(
            {
                "condition_id": condition_id,
                "problem_id": problem_id,
                "checkpoint_index": checkpoint_index,
                "failed_checkpoint_count": len(group),
                "mean_hidden_subtest_pass_rate": mean(pass_rates)
                if pass_rates
                else None,
                "mean_hidden_subtests_failed": mean(failed_counts)
                if failed_counts
                else None,
                "mean_failed_hidden_cluster_count": mean(cluster_counts)
                if cluster_counts
                else None,
                "mean_delta_vs_c0_pass_rate": mean(deltas_c0)
                if deltas_c0
                else None,
                "mean_delta_vs_c1_pass_rate": mean(deltas_c1)
                if deltas_c1
                else None,
            }
        )
    return aggregates


def technical_slopes(
    *, run_row: dict[str, Any], technical_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "run_id": run_row["run_id"],
        "condition_id": run_row["condition_id"],
        "problem_id": run_row["problem_id"],
        "replicate_id": run_row["replicate_id"],
    }
    for field in TECHNICAL_SLOPE_FIELDS:
        points: list[tuple[float, float]] = []
        for row in technical_rows:
            x_value = as_number(row.get("checkpoint_index"))
            y_value = as_number(row.get(field))
            if x_value is None or y_value is None:
                continue
            points.append((x_value, y_value))
        result[f"{field}_slope"] = slope(points)
        result[f"{field}_points"] = len(points)
    return result


def aggregate_by_condition_problem(
    summaries: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in summaries:
        grouped[(str(row["condition_id"]), str(row["problem_id"]))].append(row)
    aggregates: list[dict[str, Any]] = []
    for (condition_id, problem_id), rows in sorted(grouped.items()):
        survival_values = [
            float(row["strict_survival_index"])
            for row in rows
            if isinstance(row.get("strict_survival_index"), int)
        ]
        hidden_pass_rates = [
            float(row["hidden_checkpoint_pass_rate"])
            for row in rows
            if row.get("hidden_checkpoint_pass_rate") is not None
        ]
        regression_rates = [
            float(row["regression_rate"])
            for row in rows
            if row.get("regression_rate") is not None
        ]
        aggregates.append(
            {
                "condition_id": condition_id,
                "problem_id": problem_id,
                "run_count": len(rows),
                "mean_strict_survival_index": mean(survival_values)
                if survival_values
                else None,
                "mean_hidden_checkpoint_pass_rate": mean(hidden_pass_rates)
                if hidden_pass_rates
                else None,
                "mean_regression_rate": mean(regression_rates)
                if regression_rates
                else None,
                "not_evaluated_run_count": sum(1 for row in rows if row["not_evaluated"]),
            }
        )
    return aggregates


def pass_matrix_rows(checkpoint_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in sorted(
        checkpoint_rows,
        key=lambda item: (
            str(item.get("condition_id")),
            str(item.get("problem_id")),
            int(item.get("replicate_id") or 0),
            int(item.get("checkpoint_index") or 0),
        ),
    ):
        rows.append(
            {
                "condition": row.get("condition_id"),
                "problem": row.get("problem_id"),
                "replicate": row.get("replicate_id"),
                "checkpoint": row.get("checkpoint_id"),
                "visible": bool_label(row.get("visible_acceptance_passed")),
                "hidden": bool_label(row.get("hidden_tests_passed")),
                "regressions": row.get("prior_regression_count"),
                "lock": row.get("lock_status"),
                "status": row.get("status"),
            }
        )
    return rows


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows._\n"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [format_cell(row.get(column)) for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value).replace("|", "\\|")


def trajectory_markdown(summaries: list[dict[str, Any]]) -> str:
    columns = [
        "condition_id",
        "problem_id",
        "replicate_id",
        "status",
        "strict_survival_index",
        "checkpoint_count_expected",
        "hidden_checkpoint_pass_rate",
        "regression_rate",
        "hidden_failure_after_visible_pass_count",
        "not_evaluated",
    ]
    return markdown_table(summaries, columns)


def pass_matrix_markdown(rows: list[dict[str, Any]]) -> str:
    return markdown_table(
        rows,
        [
            "condition",
            "problem",
            "replicate",
            "checkpoint",
            "visible",
            "hidden",
            "regressions",
            "lock",
            "status",
        ],
    )


def near_miss_markdown(
    rows: list[dict[str, Any]],
    aggregate: list[dict[str, Any]],
) -> str:
    sections = [
        "# Near-Miss Metrics",
        "",
        "These are secondary diagnostics for hidden-test failures. Strict trajectory survival remains the primary metric.",
        "",
        "Failed hidden-test cluster labels are derived from SCBench evaluation summary names and strip parametrized fixture values; they do not include hidden test bodies.",
        "",
        "## Failed Checkpoints",
        "",
        markdown_table(
            rows,
            [
                "condition_id",
                "problem_id",
                "checkpoint_id",
                "replicate_id",
                "visible_acceptance_passed",
                "hidden_failure_after_visible_pass",
                "hidden_subtests_passed",
                "hidden_subtests_total",
                "hidden_subtest_pass_rate",
                "delta_vs_c0_pass_rate",
                "delta_vs_c1_pass_rate",
                "failed_hidden_cluster_count",
                "failed_hidden_cluster_label_text",
            ],
        ),
        "",
        "## Aggregate Failed-Checkpoint Diagnostics",
        "",
        markdown_table(
            aggregate,
            [
                "condition_id",
                "problem_id",
                "checkpoint_index",
                "failed_checkpoint_count",
                "mean_hidden_subtest_pass_rate",
                "mean_hidden_subtests_failed",
                "mean_failed_hidden_cluster_count",
                "mean_delta_vs_c0_pass_rate",
                "mean_delta_vs_c1_pass_rate",
            ],
        ),
    ]
    return "\n".join(sections)


def run_analysis(*, results_dir: Path, output_dir: Path) -> dict[str, Any]:
    run_rows = read_jsonl(results_dir / "runs.jsonl")
    checkpoint_rows = read_jsonl(results_dir / "checkpoints.jsonl")
    technical_rows = read_jsonl(results_dir / "technical_metrics.jsonl")
    if not run_rows:
        raise AnalysisError(f"No runs found in {results_dir / 'runs.jsonl'}")

    checkpoints = checkpoints_by_run(checkpoint_rows)
    technical = technical_by_run(technical_rows)
    summaries = [
        trajectory_summary(
            run_row=run_row,
            checkpoint_rows=checkpoints.get(str(run_row["run_id"]), []),
        )
        for run_row in run_rows
    ]
    slopes = [
        technical_slopes(
            run_row=run_row,
            technical_rows=technical.get(str(run_row["run_id"]), []),
        )
        for run_row in run_rows
    ]
    matrix = pass_matrix_rows(checkpoint_rows)
    aggregate = aggregate_by_condition_problem(summaries)
    repo_root = repo_root_from_results_dir(results_dir)
    near_misses = near_miss_rows(checkpoint_rows, repo_root=repo_root)
    near_miss_aggregate = aggregate_near_misses(near_misses)
    evaluable_checkpoint_count = sum(
        1 for row in checkpoint_rows if row.get("hidden_tests_passed") is not None
    )
    visible_checkpoint_count = sum(
        1 for row in checkpoint_rows if row.get("visible_acceptance_passed") is not None
    )
    dry_run_checkpoint_count = sum(
        1 for row in checkpoint_rows if row.get("hidden_tests_passed") is None
    )
    summary = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "source_results_dir": results_dir.as_posix(),
        "run_count": len(run_rows),
        "checkpoint_count": len(checkpoint_rows),
        "technical_metric_count": len(technical_rows),
        "evaluable_checkpoint_count": evaluable_checkpoint_count,
        "visible_acceptance_checkpoint_count": visible_checkpoint_count,
        "dry_run_checkpoint_count": dry_run_checkpoint_count,
        "trajectory_summaries": summaries,
        "condition_problem_summary": aggregate,
        "technical_slopes": slopes,
        "near_miss_rows": near_misses,
        "near_miss_summary": near_miss_aggregate,
    }

    write_json(output_dir / "summary.json", summary)
    write_jsonl(output_dir / "near_miss_rows.jsonl", near_misses)
    write_text(output_dir / "trajectory_summary.md", trajectory_markdown(summaries))
    write_text(output_dir / "pass_matrix.md", pass_matrix_markdown(matrix))
    write_text(
        output_dir / "near_miss_summary.md",
        near_miss_markdown(near_misses, near_miss_aggregate),
    )
    write_text(
        output_dir / "condition_problem_summary.md",
        markdown_table(
            aggregate,
            [
                "condition_id",
                "problem_id",
                "run_count",
                "mean_strict_survival_index",
                "mean_hidden_checkpoint_pass_rate",
                "mean_regression_rate",
                "not_evaluated_run_count",
            ],
        ),
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_analysis(
        results_dir=args.results_dir.resolve(),
        output_dir=args.output_dir.resolve(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
