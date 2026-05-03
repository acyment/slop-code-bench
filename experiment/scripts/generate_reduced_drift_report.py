#!/usr/bin/env python3
"""Generate a directional C0-vs-C2 reduced-drift mini-screen report."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any


class ReducedDriftReportError(ValueError):
    """Raised when reduced-drift report inputs cannot be loaded."""


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ReducedDriftReportError(f"Expected JSON object at {path}")
    return payload


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
                raise ReducedDriftReportError(
                    f"Expected JSON object at {path}:{line_number}"
                )
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


def format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value).replace("|", "\\|")


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows._\n"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(format_cell(row.get(column)) for column in columns)
            + " |"
        )
    return "\n".join(lines)


def bool_label(value: Any) -> str:
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    return "n/a"


def yes_no_label(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "n/a"


def summary_by_condition_problem_replicate(
    analysis: dict[str, Any]
) -> dict[tuple[str, str, int], dict[str, Any]]:
    result: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in analysis.get("trajectory_summaries", []):
        if not isinstance(row, dict):
            continue
        result[
            (
                str(row["condition_id"]),
                str(row["problem_id"]),
                int(row["replicate_id"]),
            )
        ] = row
    return result


def paired_trajectory_rows(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = summary_by_condition_problem_replicate(analysis)
    keys = {
        (problem_id, replicate_id)
        for condition_id, problem_id, replicate_id in summaries
        if condition_id in {"C0", "C2"}
    }
    rows: list[dict[str, Any]] = []
    for problem_id, replicate_id in sorted(keys):
        c0 = summaries.get(("C0", problem_id, replicate_id))
        c2 = summaries.get(("C2", problem_id, replicate_id))
        if c0 is None or c2 is None:
            rows.append(
                {
                    "problem": problem_id,
                    "replicate": replicate_id,
                    "paired": False,
                    "status": "missing_pair",
                }
            )
            continue
        c0_survival = c0.get("strict_survival_index")
        c2_survival = c2.get("strict_survival_index")
        survival_delta = (
            int(c2_survival) - int(c0_survival)
            if isinstance(c0_survival, int) and isinstance(c2_survival, int)
            else None
        )
        c0_regression = c0.get("regression_rate")
        c2_regression = c2.get("regression_rate")
        regression_delta = (
            float(c2_regression) - float(c0_regression)
            if c0_regression is not None and c2_regression is not None
            else None
        )
        rows.append(
            {
                "problem": problem_id,
                "replicate": replicate_id,
                "paired": True,
                "status": "paired",
                "c0_survival": c0_survival,
                "c2_survival": c2_survival,
                "survival_delta_c2_minus_c0": survival_delta,
                "c0_regression_rate": c0_regression,
                "c2_regression_rate": c2_regression,
                "regression_delta_c2_minus_c0": regression_delta,
                "c0_hidden_pass_rate": c0.get("hidden_checkpoint_pass_rate"),
                "c2_hidden_pass_rate": c2.get("hidden_checkpoint_pass_rate"),
                "c2_hidden_after_visible": c2.get(
                    "hidden_failure_after_visible_pass_count"
                ),
            }
        )
    return rows


def checkpoint_pair_rows(checkpoint_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in checkpoint_rows:
        if row.get("condition_id") not in {"C0", "C2"}:
            continue
        grouped[
            (
                str(row["problem_id"]),
                int(row["replicate_id"]),
                int(row["checkpoint_index"]),
            )
        ][str(row["condition_id"])] = row

    rows: list[dict[str, Any]] = []
    for (problem_id, replicate_id, checkpoint_index), conditions in sorted(grouped.items()):
        c0 = conditions.get("C0", {})
        c2 = conditions.get("C2", {})
        rows.append(
            {
                "problem": problem_id,
                "replicate": replicate_id,
                "checkpoint": f"checkpoint_{checkpoint_index}",
                "c0_hidden": bool_label(c0.get("hidden_tests_passed")),
                "c2_hidden": bool_label(c2.get("hidden_tests_passed")),
                "c2_visible": bool_label(c2.get("visible_acceptance_passed")),
                "c0_regressions": c0.get("prior_regression_count"),
                "c2_regressions": c2.get("prior_regression_count"),
                "c2_hidden_after_visible": yes_no_label(
                    c2.get("hidden_failure_after_visible_pass")
                ),
            }
        )
    return rows


def cost_summary(checkpoint_rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "api_cost_usd": 0.0,
        "agent_steps": 0,
        "input_tokens_net": 0,
        "output_tokens_net": 0,
        "reasoning_tokens_net": 0,
        "checkpoint_rows_with_cost": 0,
    }
    for row in checkpoint_rows:
        cost = row.get("cost_metrics")
        if not isinstance(cost, dict):
            continue
        if cost.get("api_cost_usd") is None:
            continue
        totals["checkpoint_rows_with_cost"] += 1
        for key in [
            "api_cost_usd",
            "agent_steps",
            "input_tokens_net",
            "output_tokens_net",
            "reasoning_tokens_net",
        ]:
            value = cost.get(key)
            if isinstance(value, int | float):
                totals[key] += value
    return totals


def technical_slope_rows(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in analysis.get("technical_slopes", []):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "condition": row.get("condition_id"),
                "problem": row.get("problem_id"),
                "replicate": row.get("replicate_id"),
                "loc_slope": row.get("loc_slope"),
                "sloc_slope": row.get("sloc_slope"),
                "cc_max_slope": row.get("cc_max_slope"),
                "clone_lines_slope": row.get("clone_lines_slope"),
                "cloned_pct_slope": row.get("cloned_pct_slope"),
                "acceptance_runtime_ms_slope": row.get("acceptance_runtime_ms_slope"),
                "loc_points": row.get("loc_points"),
            }
        )
    return rows


def report_status(
    *, analysis: dict[str, Any], preflight: dict[str, Any], pair_rows: list[dict[str, Any]]
) -> str:
    if not preflight.get("evidence_gate", {}).get("ready"):
        return "blocked_not_evidence"
    if int(analysis.get("evaluable_checkpoint_count") or 0) == 0:
        return "ready_no_evaluations"
    if any(row.get("paired") is not True for row in pair_rows):
        return "incomplete_pairs"
    return "directional_probe_complete"


def build_report(
    *,
    results_dir: Path,
    analysis_dir: Path,
    preflight_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    analysis = read_json(analysis_dir / "summary.json")
    preflight = read_json(preflight_path)
    checkpoint_rows = read_jsonl(results_dir / "checkpoints.jsonl")
    run_rows = read_jsonl(results_dir / "runs.jsonl")
    pair_rows = paired_trajectory_rows(analysis)
    checkpoint_pairs = checkpoint_pair_rows(checkpoint_rows)
    technical_rows = technical_slope_rows(analysis)
    costs = cost_summary(checkpoint_rows)
    status = report_status(
        analysis=analysis,
        preflight=preflight,
        pair_rows=pair_rows,
    )
    summary = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": status,
        "claim_status": "directional_only" if status == "directional_probe_complete" else "not_interpretable",
        "causal_claim_supported": False,
        "results_dir": results_dir.as_posix(),
        "analysis_dir": analysis_dir.as_posix(),
        "preflight_path": preflight_path.as_posix(),
        "run_count": len(run_rows),
        "checkpoint_count": len(checkpoint_rows),
        "evaluable_checkpoint_count": analysis.get("evaluable_checkpoint_count"),
        "paired_trajectory_rows": pair_rows,
        "checkpoint_pair_rows": checkpoint_pairs,
        "technical_slope_rows": technical_rows,
        "cost_summary": costs,
        "limitations": [
            "One replicate and two problems are underpowered and directional only.",
            "Visible acceptance tests are an intervention; hidden SCBench tests remain the correctness judge.",
            (
                "C2 agent-side visible acceptance execution must be audited or harness-enforced as "
                "implementation-time feedback; scorer-only post-hoc reruns are measurement, not the intervention."
            ),
            "Technical drift slopes over three checkpoints are noisy and should be treated as secondary.",
            "Before scaling, inspect C2 asset staging so future checkpoint scenarios are not exposed early.",
        ],
    }
    write_json(output_dir / "reduced_drift_report_summary.json", summary)
    write_text(
        output_dir / "reduced_drift_report.md",
        report_markdown(
            summary=summary,
            pair_rows=pair_rows,
            checkpoint_pairs=checkpoint_pairs,
            technical_rows=technical_rows,
        ),
    )
    return summary


def report_markdown(
    *,
    summary: dict[str, Any],
    pair_rows: list[dict[str, Any]],
    checkpoint_pairs: list[dict[str, Any]],
    technical_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# Reduced-Drift Mini-Screen Report",
        "",
        f"Generated at: `{summary['generated_at']}`",
        f"Status: `{summary['status']}`",
        f"Claim status: `{summary['claim_status']}`",
        "",
        "## Bottom Line",
        "",
        (
            "This report is directional only. It can indicate whether the paired C0 vs C2 "
            "mini-screen pipeline is worth inspecting, but it cannot support a causal "
            "research claim. Treat C2 as primary evidence only after visible acceptance "
            "execution is audited or harness-enforced as implementation-time feedback."
        ),
        "",
        "## Data Shape",
        "",
        f"- Runs: `{summary['run_count']}`",
        f"- Checkpoints: `{summary['checkpoint_count']}`",
        f"- Evaluable checkpoints: `{summary['evaluable_checkpoint_count']}`",
        "",
        "## Paired Trajectories",
        "",
        markdown_table(
            pair_rows,
            [
                "problem",
                "replicate",
                "paired",
                "c0_survival",
                "c2_survival",
                "survival_delta_c2_minus_c0",
                "c0_regression_rate",
                "c2_regression_rate",
                "regression_delta_c2_minus_c0",
                "c2_hidden_after_visible",
            ],
        ),
        "",
        "## Checkpoint Matrix",
        "",
        markdown_table(
            checkpoint_pairs,
            [
                "problem",
                "replicate",
                "checkpoint",
                "c0_hidden",
                "c2_hidden",
                "c2_visible",
                "c0_regressions",
                "c2_regressions",
                "c2_hidden_after_visible",
            ],
        ),
        "",
        "## Technical Drift Slopes",
        "",
        markdown_table(
            technical_rows,
            [
                "condition",
                "problem",
                "replicate",
                "loc_slope",
                "sloc_slope",
                "cc_max_slope",
                "clone_lines_slope",
                "cloned_pct_slope",
                "acceptance_runtime_ms_slope",
                "loc_points",
            ],
        ),
        "",
        "## Cost Summary",
        "",
        markdown_table([summary["cost_summary"]], sorted(summary["cost_summary"])),
        "",
        "## Limitations",
        "",
        "\n".join(f"- {item}" for item in summary["limitations"]),
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_report(
        results_dir=args.results_dir.resolve(),
        analysis_dir=args.analysis_dir.resolve(),
        preflight_path=args.preflight.resolve(),
        output_dir=args.output_dir.resolve(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
