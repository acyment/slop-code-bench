#!/usr/bin/env python3
"""Generate a limitation-aware pilot analysis report from normalized results."""

from __future__ import annotations

import argparse
import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any


class ReportError(ValueError):
    """Raised when report inputs cannot be loaded."""


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ReportError(f"Expected JSON object at {path}")
    return payload


def read_text_optional(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


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


def format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value).replace("|", "\\|")


def gate_blockers(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    checks = preflight.get("checks", [])
    if not isinstance(checks, list):
        return []
    return [
        {
            "id": check.get("id"),
            "status": check.get("status"),
            "message": check.get("message"),
        }
        for check in checks
        if isinstance(check, dict) and check.get("status") != "pass"
    ]


def report_status(analysis: dict[str, Any], preflight: dict[str, Any]) -> str:
    if preflight.get("status") != "ready":
        return "pre_evidence_blocked"
    if int(analysis.get("evaluable_checkpoint_count") or 0) == 0:
        return "pre_evidence_no_evaluations"
    return "evidence_available"


def summarize_costs(analysis: dict[str, Any]) -> dict[str, Any]:
    # Cost fields are preserved in normalized checkpoint rows, but the M10 dry-run
    # summary has no model execution. Keep the shape explicit for later runs.
    return {
        "cost_data_available": False,
        "reason": "No implementation-agent execution has run in the current artifacts.",
        "run_count": analysis.get("run_count"),
    }


def build_report_summary(
    *,
    analysis: dict[str, Any],
    preflight: dict[str, Any],
    freeze_manifest: dict[str, Any],
) -> dict[str, Any]:
    status = report_status(analysis, preflight)
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": status,
        "claim_status": "not_tested",
        "causal_claim_supported": False,
        "analysis_source_results_dir": analysis.get("source_results_dir"),
        "run_count": analysis.get("run_count"),
        "checkpoint_count": analysis.get("checkpoint_count"),
        "evaluable_checkpoint_count": analysis.get("evaluable_checkpoint_count"),
        "visible_acceptance_checkpoint_count": analysis.get(
            "visible_acceptance_checkpoint_count"
        ),
        "dry_run_checkpoint_count": analysis.get("dry_run_checkpoint_count"),
        "full_pilot_preflight_status": preflight.get("status"),
        "full_pilot_total_trajectories": preflight.get("matrix_summary", {}).get(
            "total_trajectories"
        ),
        "full_pilot_total_checkpoint_executions": preflight.get(
            "matrix_summary", {}
        ).get("total_checkpoint_executions"),
        "freeze_hash": freeze_manifest.get("freeze_hash"),
        "gate_blockers": gate_blockers(preflight),
        "cost_metrics": summarize_costs(analysis),
    }


def report_markdown(
    *,
    summary: dict[str, Any],
    analysis: dict[str, Any],
    preflight: dict[str, Any],
    freeze_manifest: dict[str, Any],
    trajectory_table: str,
    pass_matrix: str,
) -> str:
    blockers = gate_blockers(preflight)
    condition_problem = analysis.get("condition_problem_summary", [])
    technical_slopes = analysis.get("technical_slopes", [])
    technical_rows = []
    for row in technical_slopes:
        if not isinstance(row, dict):
            continue
        technical_rows.append(
            {
                "condition": row.get("condition_id"),
                "problem": row.get("problem_id"),
                "replicate": row.get("replicate_id"),
                "loc_points": row.get("loc_points"),
                "verbosity_points": row.get("verbosity_points"),
                "erosion_points": row.get("erosion_points"),
                "hidden_eval_runtime_points": row.get(
                    "hidden_eval_runtime_ms_points"
                ),
            }
        )

    lines = [
        "# SpecCommons SCBench Gherkin Drift Pilot Report",
        "",
        f"Generated at: `{summary['generated_at']}`",
        f"Report status: `{summary['status']}`",
        f"Freeze hash: `{summary.get('freeze_hash')}`",
        "",
        "## Bottom Line",
        "",
        (
            "No causal or directional research conclusion can be drawn from the current artifacts. "
            "The available data are dry-run and preflight outputs only: no implementation agent "
            "trajectory, visible acceptance execution against agent snapshots, hidden SCBench "
            "evaluation, cost trace, or technical drift measurement has run."
        ),
        "",
        "What is complete is the reporting pipeline: normalized exports can be summarized, "
        "blocked readiness is explicit, and the archive manifest can preserve the current "
        "pre-evidence state.",
        "",
        "## Current Data",
        "",
        f"- Normalized runs: `{summary.get('run_count')}`",
        f"- Normalized checkpoints: `{summary.get('checkpoint_count')}`",
        f"- Evaluable checkpoints: `{summary.get('evaluable_checkpoint_count')}`",
        f"- Visible acceptance checkpoint results: `{summary.get('visible_acceptance_checkpoint_count')}`",
        f"- Dry-run checkpoints: `{summary.get('dry_run_checkpoint_count')}`",
        "",
        "## Full Pilot Gate",
        "",
        f"- Preflight status: `{summary.get('full_pilot_preflight_status')}`",
        f"- Planned trajectories: `{summary.get('full_pilot_total_trajectories')}`",
        "- Planned checkpoint executions: "
        f"`{summary.get('full_pilot_total_checkpoint_executions')}`",
        "",
        markdown_table(blockers, ["id", "status", "message"]),
        "",
        "## Functional Drift Metrics",
        "",
        "Strict survival, regression rate, and hidden-failure-after-visible-pass metrics are implemented in the analysis summary, but the current values are not evidence-bearing because all checkpoints are dry-run/not evaluated.",
        "",
        "### Trajectory Summary",
        "",
        trajectory_table.strip() or "_No trajectory table._",
        "",
        "### Pass Matrix",
        "",
        pass_matrix.strip() or "_No pass matrix._",
        "",
        "### Condition And Problem Summary",
        "",
        markdown_table(
            [row for row in condition_problem if isinstance(row, dict)],
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
        "",
        "## Technical Drift Metrics",
        "",
        "Technical slope extraction is wired, but no slope is meaningful yet because no agent-produced checkpoint snapshots or static metric files were evaluated.",
        "",
        markdown_table(
            technical_rows,
            [
                "condition",
                "problem",
                "replicate",
                "loc_points",
                "verbosity_points",
                "erosion_points",
                "hidden_eval_runtime_points",
            ],
        ),
        "",
        "## Cost Metrics",
        "",
        "- Cost data available: `False`",
        "- Reason: no implementation-agent run has executed in the current artifacts.",
        "",
        "## Reproducibility Artifacts",
        "",
        "- Freeze manifest: `experiment/locks/pilot_artifact_freeze.json`",
        "- M10 normalized export: `experiment/results/m10_mvp_dry_run/export/`",
        "- M10 analysis: `experiment/results/m10_mvp_dry_run/analysis/`",
        "- M11 preflight: `experiment/results/m11_full_pilot_preflight/`",
        "- M12 report summary: `experiment/results/m12_pilot_report/report_summary.json`",
        "",
        "## Limitations",
        "",
        "- The C0/C1/C2 comparison has not run.",
        "- Hidden SCBench tests have not judged any agent-produced code.",
        "- Visible Gherkin acceptance has not run against agent checkpoint snapshots.",
        "- Model, provider, agent harness, and version are still placeholders in pilot configs.",
        "- The current report validates analysis/reporting mechanics only.",
        "",
        "## Required Next Step",
        "",
        "Implement the native execution bridge and C2 snapshot acceptance integration, select the fixed model/agent settings, regenerate the freeze manifest, rerun preflight until it is `ready`, and only then run the primary full-pilot matrix.",
    ]
    _ = freeze_manifest
    return "\n".join(lines)


def generate_report(
    *,
    analysis_summary_path: Path,
    analysis_dir: Path,
    preflight_path: Path,
    freeze_manifest_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    analysis = read_json(analysis_summary_path)
    preflight = read_json(preflight_path)
    freeze_manifest = read_json(freeze_manifest_path)
    summary = build_report_summary(
        analysis=analysis,
        preflight=preflight,
        freeze_manifest=freeze_manifest,
    )
    markdown = report_markdown(
        summary=summary,
        analysis=analysis,
        preflight=preflight,
        freeze_manifest=freeze_manifest,
        trajectory_table=read_text_optional(analysis_dir / "trajectory_summary.md"),
        pass_matrix=read_text_optional(analysis_dir / "pass_matrix.md"),
    )
    write_json(output_dir / "report_summary.json", summary)
    write_text(output_dir / "pilot_report.md", markdown)
    return summary


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-summary",
        type=Path,
        default=repo_root / "experiment/results/m10_mvp_dry_run/analysis/summary.json",
    )
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=repo_root / "experiment/results/m10_mvp_dry_run/analysis",
    )
    parser.add_argument(
        "--preflight",
        type=Path,
        default=repo_root
        / "experiment/results/m11_full_pilot_preflight/preflight.json",
    )
    parser.add_argument(
        "--freeze-manifest",
        type=Path,
        default=repo_root / "experiment/locks/pilot_artifact_freeze.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "experiment/results/m12_pilot_report",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = generate_report(
        analysis_summary_path=args.analysis_summary.resolve(),
        analysis_dir=args.analysis_dir.resolve(),
        preflight_path=args.preflight.resolve(),
        freeze_manifest_path=args.freeze_manifest.resolve(),
        output_dir=args.output_dir.resolve(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
