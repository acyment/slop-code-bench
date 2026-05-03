#!/usr/bin/env python3
"""Compute pilot drift summaries from normalized experiment JSONL tables."""

from __future__ import annotations

import argparse
import json
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


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
    }

    write_json(output_dir / "summary.json", summary)
    write_text(output_dir / "trajectory_summary.md", trajectory_markdown(summaries))
    write_text(output_dir / "pass_matrix.md", pass_matrix_markdown(matrix))
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
