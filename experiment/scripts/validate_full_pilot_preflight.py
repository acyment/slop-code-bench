#!/usr/bin/env python3
"""Validate whether the full pilot matrix is ready for primary execution."""

from __future__ import annotations

import argparse
import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import audit_acceptance_coverage
import freeze_pilot_artifacts
import yaml

PILOT_CONFIGS = [
    "experiment/configs/pilot_c0.yaml",
    "experiment/configs/pilot_c1.yaml",
    "experiment/configs/pilot_c2.yaml",
]
SCREENING_CONFIGS = [
    "experiment/configs/screening_c0.yaml",
    "experiment/configs/screening_c1.yaml",
    "experiment/configs/screening_c2.yaml",
]
MINI_SCREEN_CONFIGS = [
    "experiment/configs/mini_screen_c0.yaml",
    "experiment/configs/mini_screen_c1.yaml",
    "experiment/configs/mini_screen_c2.yaml",
]
CONFIG_PROFILES = {
    "mini_screen": MINI_SCREEN_CONFIGS,
    "pilot": PILOT_CONFIGS,
    "screening": SCREENING_CONFIGS,
}
EVIDENCE_DISABLED_PROBLEMS = {
    "file_backup": {
        "decision_id": "EXP-100X",
        "status": "harness_validation_only",
        "reason": (
            "All C0/C1/C2 EXP-100R replicates failed checkpoint 1; keep this "
            "problem out of evidence-producing drift screens until a post-fix "
            "smoke demonstrates multi-checkpoint feasibility."
        ),
    }
}


class PreflightError(ValueError):
    """Raised when preflight inputs cannot be read."""


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise PreflightError(f"Expected YAML mapping at {path}")
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


def is_placeholder(value: Any) -> bool:
    return not isinstance(value, str) or not value or value.startswith("TBD")


def check_model_and_agent(
    repo_root: Path, config_rels: list[str]
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for config_rel in config_rels:
        config_path = repo_root / config_rel
        config = load_yaml(config_path)
        model = config.get("model", {})
        agent = config.get("agent_harness", {})
        model_ready = not is_placeholder(model.get("provider")) and not is_placeholder(
            model.get("name")
        )
        agent_ready = not is_placeholder(agent.get("id")) and not is_placeholder(
            agent.get("version")
        )
        checks.append(
            {
                "id": f"{config['matrix_id']}.model_agent_selected",
                "status": "pass" if model_ready and agent_ready else "block",
                "matrix_id": config["matrix_id"],
                "message": (
                    "Model and agent are selected."
                    if model_ready and agent_ready
                    else "Model/provider and agent harness/version still contain TBD placeholders."
                ),
            }
        )
    return checks


def check_execution_bridge(repo_root: Path) -> dict[str, Any]:
    source = (repo_root / "experiment/scripts/run_trajectory.py").read_text(
        encoding="utf-8"
    )
    dry_run_only = "choices=[\"dry-run\"]" in source or (
        "only dry-run mode is implemented" in source
    )
    return {
        "id": "trajectory.execution_bridge",
        "status": "block" if dry_run_only else "pass",
        "message": (
            "run_trajectory.py is still dry-run only."
            if dry_run_only
            else "run_trajectory.py appears to support a non-dry-run execution mode."
        ),
    }


def check_acceptance_snapshot_bridge(repo_root: Path) -> dict[str, Any]:
    source = (
        repo_root / "experiment/scripts/generate_condition_context.py"
    ).read_text(encoding="utf-8")
    smoke_only = "run_acceptance_smoke.py" in source
    standalone_exists = (
        repo_root / "experiment/steps/acceptance/standalone_runner.py"
    ).is_file()
    return {
        "id": "c2.acceptance_snapshot_bridge",
        "status": "block" if smoke_only or not standalone_exists else "pass",
        "message": (
            "C2 acceptance command still points at the smoke/reference runner, not agent checkpoint snapshots."
            if smoke_only
            else "C2 acceptance command points at a workspace-local standalone runner."
            if standalone_exists
            else "C2 acceptance standalone runner is missing."
        ),
    }


def c2_feedback_policy_blockers(configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    accepted_enforcement = {"agent_transcript_audited", "harness_mediated"}
    for config in configs:
        condition = config.get("condition", {})
        if condition.get("id") != "C2":
            continue
        policy = condition.get("acceptance_feedback_policy")
        if not isinstance(policy, dict):
            blockers.append(
                {
                    "type": "missing_c2_acceptance_feedback_policy",
                    "matrix_id": config.get("matrix_id"),
                }
            )
            continue
        if policy.get("mode") not in {
            "mandatory_pre_completion_execution",
            "harness_mediated_repair_loop",
        }:
            blockers.append(
                {
                    "type": "c2_acceptance_feedback_mode_not_executed",
                    "matrix_id": config.get("matrix_id"),
                    "mode": policy.get("mode"),
                }
            )
        if policy.get("enforcement") not in accepted_enforcement:
            blockers.append(
                {
                    "type": "c2_acceptance_feedback_not_enforced",
                    "matrix_id": config.get("matrix_id"),
                    "enforcement": policy.get("enforcement"),
                    "required_enforcement": sorted(accepted_enforcement),
                }
            )
        if policy.get("scorer_rerun_after_checkpoint") is not True:
            blockers.append(
                {
                    "type": "c2_scorer_acceptance_rerun_missing",
                    "matrix_id": config.get("matrix_id"),
                }
            )
        if policy.get("invalid_if_not_executed") is not True:
            blockers.append(
                {
                    "type": "c2_missing_invalid_if_not_executed_policy",
                    "matrix_id": config.get("matrix_id"),
                }
            )
    return blockers


def check_c2_feedback_enforcement(
    repo_root: Path, config_rels: list[str]
) -> dict[str, Any]:
    configs = [load_yaml(repo_root / config_rel) for config_rel in config_rels]
    blockers = c2_feedback_policy_blockers(configs)
    return {
        "id": "c2.acceptance_feedback_enforcement",
        "status": "pass" if not blockers else "block",
        "message": (
            "C2 requires executed acceptance feedback and the runner can audit or enforce it."
            if not blockers
            else "C2 visible acceptance is not yet enforced as implementation-time feedback."
        ),
        "blockers": blockers,
    }


def acceptance_coverage_index(repo_root: Path) -> set[tuple[str, int]]:
    import importlib.util

    runner_path = repo_root / "experiment/steps/acceptance/standalone_runner.py"
    spec = importlib.util.spec_from_file_location(
        "speccommons_standalone_acceptance", runner_path
    )
    if spec is None or spec.loader is None:
        raise PreflightError(f"Cannot import acceptance runner: {runner_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        (str(row["problem_id"]), int(row["checkpoint_index"]))
        for row in module.SCENARIO_SPECS
    }


def configured_checkpoint_limit(config: dict[str, Any]) -> int | None:
    raw = config.get("checkpoint_limit")
    if raw is None:
        return None
    if not isinstance(raw, int) or raw <= 0:
        raise PreflightError(
            f"{config.get('matrix_id', '<unknown>')} checkpoint_limit must be a positive integer"
        )
    return raw


def selected_checkpoint_count(
    *, problems_root: Path, config: dict[str, Any], problem_id: str
) -> int:
    total = checkpoint_count(problems_root, problem_id)
    limit = configured_checkpoint_limit(config)
    if limit is None:
        return total
    return min(total, limit)


def selected_c2_slots(
    *, repo_root: Path, problems_root: Path, config_rels: list[str]
) -> set[tuple[str, int]]:
    slots: set[tuple[str, int]] = set()
    for config_rel in config_rels:
        config = load_yaml(repo_root / config_rel)
        if config["condition"]["id"] != "C2":
            continue
        for problem_id in config["problems"]:
            total = selected_checkpoint_count(
                problems_root=problems_root,
                config=config,
                problem_id=str(problem_id),
            )
            for index in range(1, total + 1):
                slots.add((str(problem_id), index))
    return slots


def build_feature_runner_coverage_audit(
    *, repo_root: Path, problems_root: Path, config_rels: list[str]
) -> dict[str, Any]:
    return audit_acceptance_coverage.build_coverage_audit(
        repo_root=repo_root,
        selected_slots=selected_c2_slots(
            repo_root=repo_root,
            problems_root=problems_root,
            config_rels=config_rels,
        ),
    )


def check_acceptance_coverage(
    *, repo_root: Path, problems_root: Path, config_rels: list[str]
) -> dict[str, Any]:
    coverage = acceptance_coverage_index(repo_root)
    missing: list[dict[str, Any]] = []
    checked = 0
    for config_rel in config_rels:
        config = load_yaml(repo_root / config_rel)
        if config["condition"]["id"] != "C2":
            continue
        for problem_id in config["problems"]:
            total = selected_checkpoint_count(
                problems_root=problems_root,
                config=config,
                problem_id=str(problem_id),
            )
            for index in range(1, total + 1):
                checked += 1
                if (str(problem_id), index) not in coverage:
                    missing.append(
                        {
                            "matrix_id": config["matrix_id"],
                            "problem_id": str(problem_id),
                            "checkpoint_index": index,
                        }
                    )
    return {
        "id": "c2.acceptance_coverage",
        "status": "pass" if not missing else "block",
        "message": (
            "C2 visible acceptance coverage exists for every selected checkpoint."
            if not missing
            else "C2 visible acceptance coverage is partial: "
            f"{len(missing)} of {checked} selected checkpoint slots are missing locked scenarios."
        ),
        "checked_checkpoint_slots": checked,
        "missing_checkpoint_slots": missing,
    }


def check_feature_runner_coverage(
    *, repo_root: Path, problems_root: Path, config_rels: list[str]
) -> dict[str, Any]:
    audit = build_feature_runner_coverage_audit(
        repo_root=repo_root,
        problems_root=problems_root,
        config_rels=config_rels,
    )
    summary = audit["summary"]
    has_features = summary["feature_scenario_count"] > 0
    ready = audit["status"] == "pass" and has_features
    return {
        "id": "c2.feature_runner_coverage",
        "status": "pass" if ready else "block",
        "message": (
            "C2 feature scenarios are mapped to locked executable runner coverage or documented as spec-only."
            if ready
            else "C2 feature-to-runner coverage has blockers: "
            f"{summary['blocker_count']} required/missing scenario(s) need locked executable coverage."
        ),
        "feature_scenario_count": summary["feature_scenario_count"],
        "executable_scenario_count": summary["executable_scenario_count"],
        "spec_only_scenario_count": summary["spec_only_scenario_count"],
        "required_missing_count": summary["required_missing_count"],
        "missing_ledger_count": summary["missing_ledger_count"],
        "invalid_coverage_count": summary["invalid_coverage_count"],
        "blocker_count": summary["blocker_count"],
        "blockers": summary["blockers"],
        "details": summary,
    }


def configured_evidence_disabled_problem_blockers(
    configs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for config in configs:
        for problem_id in [str(problem) for problem in config["problems"]]:
            decision = EVIDENCE_DISABLED_PROBLEMS.get(problem_id)
            if decision is None:
                continue
            blockers.append(
                {
                    "type": "evidence_disabled_problem",
                    "matrix_id": config.get("matrix_id"),
                    "condition_id": config.get("condition", {}).get("id"),
                    "problem_id": problem_id,
                    **decision,
                }
            )
    return blockers


def check_evidence_problem_status(
    repo_root: Path, config_rels: list[str]
) -> dict[str, Any]:
    configs = [load_yaml(repo_root / config_rel) for config_rel in config_rels]
    blockers = configured_evidence_disabled_problem_blockers(configs)
    return {
        "id": "problem_selection.evidence_disabled",
        "status": "pass" if not blockers else "block",
        "message": (
            "All configured problems are enabled for evidence-producing drift runs."
            if not blockers
            else "One or more configured problems are currently disabled for evidence-producing drift runs."
        ),
        "blockers": blockers,
    }


def model_key(config: dict[str, Any]) -> tuple[str, str]:
    model = config.get("model", {})
    return (str(model.get("provider")), str(model.get("name")))


def agent_key(config: dict[str, Any]) -> tuple[str, str]:
    agent = config.get("agent_harness", {})
    return (str(agent.get("id")), str(agent.get("version")))


def replicate_ids(config: dict[str, Any]) -> list[int]:
    return sorted(int(replicate["replicate_id"]) for replicate in config["replicates"])


def check_reduced_drift_evidence_gate(
    *, repo_root: Path, problems_root: Path, config_rels: list[str]
) -> dict[str, Any]:
    configs = [load_yaml(repo_root / config_rel) for config_rel in config_rels]
    by_condition = {
        str(config["condition"]["id"]): config
        for config in configs
    }
    blockers: list[dict[str, Any]] = []
    blockers.extend(configured_evidence_disabled_problem_blockers(configs))

    required_conditions = {"C0", "C2"}
    missing_conditions = sorted(required_conditions - set(by_condition))
    if missing_conditions:
        blockers.append(
            {
                "type": "missing_counterfactual_conditions",
                "missing_conditions": missing_conditions,
            }
        )

    comparable_conditions = [
        condition_id
        for condition_id in ["C0", "C1", "C2"]
        if condition_id in by_condition
    ]
    if "C0" in by_condition:
        baseline = by_condition["C0"]
        for condition_id in comparable_conditions:
            config = by_condition[condition_id]
            if model_key(config) != model_key(baseline):
                blockers.append(
                    {
                        "type": "model_mismatch",
                        "condition_id": condition_id,
                        "baseline_model": list(model_key(baseline)),
                        "condition_model": list(model_key(config)),
                    }
                )
            if agent_key(config) != agent_key(baseline):
                blockers.append(
                    {
                        "type": "agent_harness_mismatch",
                        "condition_id": condition_id,
                        "baseline_agent": list(agent_key(baseline)),
                        "condition_agent": list(agent_key(config)),
                    }
                )

    if required_conditions.issubset(by_condition):
        baseline = by_condition["C0"]
        baseline_problems = {str(problem) for problem in baseline["problems"]}
        baseline_replicates = replicate_ids(baseline)
        for condition_id in comparable_conditions:
            config = by_condition[condition_id]
            problems = {str(problem) for problem in config["problems"]}
            if problems != baseline_problems:
                blockers.append(
                    {
                        "type": "problem_set_mismatch",
                        "condition_id": condition_id,
                        "baseline_problems": sorted(baseline_problems),
                        "condition_problems": sorted(problems),
                    }
                )
            condition_replicates = replicate_ids(config)
            if condition_replicates != baseline_replicates:
                blockers.append(
                    {
                        "type": "replicate_mismatch",
                        "condition_id": condition_id,
                        "baseline_replicates": baseline_replicates,
                        "condition_replicates": condition_replicates,
                    }
                )

        for problem_id in sorted(baseline_problems):
            counts_by_condition = {
                condition_id: selected_checkpoint_count(
                    problems_root=problems_root,
                    config=by_condition[condition_id],
                    problem_id=problem_id,
                )
                for condition_id in comparable_conditions
                if problem_id in {str(problem) for problem in by_condition[condition_id]["problems"]}
            }
            if counts_by_condition and len(set(counts_by_condition.values())) > 1:
                blockers.append(
                    {
                        "type": "checkpoint_prefix_mismatch",
                        "problem_id": problem_id,
                        "checkpoint_counts": counts_by_condition,
                    }
                )
            minimum_count = min(counts_by_condition.values()) if counts_by_condition else 0
            if minimum_count < 3:
                blockers.append(
                    {
                        "type": "insufficient_checkpoint_depth",
                        "problem_id": problem_id,
                        "minimum_checkpoint_count": minimum_count,
                        "required_minimum": 3,
                    }
                )

    coverage = acceptance_coverage_index(repo_root)
    c2_config = by_condition.get("C2")
    if c2_config is not None:
        blockers.extend(c2_feedback_policy_blockers(configs))
        missing_coverage: list[dict[str, Any]] = []
        for problem_id in [str(problem) for problem in c2_config["problems"]]:
            total = selected_checkpoint_count(
                problems_root=problems_root,
                config=c2_config,
                problem_id=problem_id,
            )
            for index in range(1, total + 1):
                if (problem_id, index) not in coverage:
                    missing_coverage.append(
                        {
                            "problem_id": problem_id,
                            "checkpoint_index": index,
                        }
                    )
        if missing_coverage:
            blockers.append(
                {
                    "type": "incomplete_c2_acceptance_coverage",
                    "missing_checkpoint_slots": missing_coverage,
                }
            )
        feature_runner_audit = build_feature_runner_coverage_audit(
            repo_root=repo_root,
            problems_root=problems_root,
            config_rels=config_rels,
        )
        feature_runner_summary = feature_runner_audit["summary"]
        if feature_runner_summary["blocker_count"] > 0:
            blockers.append(
                {
                    "type": "incomplete_c2_feature_runner_coverage",
                    "blocker_count": feature_runner_summary["blocker_count"],
                    "required_missing_count": feature_runner_summary[
                        "required_missing_count"
                    ],
                    "missing_ledger_count": feature_runner_summary[
                        "missing_ledger_count"
                    ],
                    "invalid_coverage_count": feature_runner_summary[
                        "invalid_coverage_count"
                    ],
                    "blockers": feature_runner_summary["blockers"],
                }
            )

    ready = not blockers
    return {
        "id": "reduced_drift.evidence_gate",
        "status": "pass" if ready else "block",
        "message": (
            "Configured run matrix is evidence-producing for a directional reduced-drift probe."
            if ready
            else f"Configured run matrix is not evidence-producing: {len(blockers)} blocker(s)."
        ),
        "ready": ready,
        "minimum_checkpoint_depth": 3,
        "required_conditions": sorted(required_conditions),
        "blockers": blockers,
    }


def check_freeze_manifest(repo_root: Path, manifest_path: Path) -> dict[str, Any]:
    result = freeze_pilot_artifacts.verify_freeze(
        manifest_path=manifest_path,
        repo_root=repo_root,
    )
    return {
        "id": "pilot_artifacts.freeze_manifest",
        "status": "pass" if result["status"] == "unchanged" else "block",
        "message": (
            "Freeze manifest matches current files."
            if result["status"] == "unchanged"
            else "Freeze manifest no longer matches current files."
        ),
        "freeze_hash": result["freeze_hash"],
        "details": result,
    }


def checkpoint_count(problems_root: Path, problem_id: str) -> int:
    config_path = problems_root / problem_id / "config.yaml"
    config = load_yaml(config_path)
    checkpoints = config.get("checkpoints")
    if not isinstance(checkpoints, dict):
        raise PreflightError(f"{config_path} has no checkpoints mapping")
    return len(checkpoints)


def matrix_summary(
    repo_root: Path, problems_root: Path, config_rels: list[str]
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for config_rel in config_rels:
        config = load_yaml(repo_root / config_rel)
        problems = [str(problem) for problem in config["problems"]]
        replicates = list(config["replicates"])
        checkpoints = {
            problem: selected_checkpoint_count(
                problems_root=problems_root,
                config=config,
                problem_id=problem,
            )
            for problem in problems
        }
        rows.append(
            {
                "matrix_id": config["matrix_id"],
                "condition_id": config["condition"]["id"],
                "problem_count": len(problems),
                "replicate_count": len(replicates),
                "trajectory_count": len(problems) * len(replicates),
                "checkpoint_executions": sum(checkpoints.values())
                * len(replicates),
                "checkpoint_counts": checkpoints,
            }
        )
    return {
        "matrices": rows,
        "total_trajectories": sum(row["trajectory_count"] for row in rows),
        "total_checkpoint_executions": sum(
            row["checkpoint_executions"] for row in rows
        ),
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Pilot Preflight",
        "",
        f"Profile: `{report.get('profile', 'pilot')}`",
        f"Status: `{report['status']}`",
        f"Generated at: `{report['generated_at']}`",
        "",
        "## Matrix",
        "",
        f"- Total trajectories: `{report['matrix_summary']['total_trajectories']}`",
        "- Total checkpoint executions: "
        f"`{report['matrix_summary']['total_checkpoint_executions']}`",
        "",
        "## Gate Checks",
        "",
        "| check | status | message |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(check["id"]),
                    str(check["status"]),
                    str(check["message"]).replace("|", "\\|"),
                ]
            )
            + " |"
        )
    evidence_gate = report.get("evidence_gate", {})
    blockers = evidence_gate.get("blockers", [])
    lines.extend(
        [
            "",
            "## Reduced-Drift Evidence Gate",
            "",
            f"- Ready: `{bool(evidence_gate.get('ready'))}`",
            f"- Message: {evidence_gate.get('message', '')}",
        ]
    )
    if blockers:
        lines.extend(["", "| blocker | detail |", "| --- | --- |"])
        for blocker in blockers:
            if not isinstance(blocker, dict):
                continue
            blocker_type = blocker.get("type")
            detail = json.dumps(blocker, sort_keys=True).replace("|", "\\|")
            lines.append(f"| {blocker_type} | `{detail}` |")
    profile = str(report.get("profile", "selected"))
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                f"The `{profile}` matrix is ready to execute."
                if report["status"] == "ready"
                else f"The `{profile}` matrix is blocked. Do not run primary data collection until every gate check passes."
            ),
        ]
    )
    return "\n".join(lines)


def run_preflight(
    *,
    repo_root: Path,
    problems_root: Path,
    freeze_manifest: Path,
    profile: str,
) -> dict[str, Any]:
    config_rels = CONFIG_PROFILES[profile]
    evidence_gate = check_reduced_drift_evidence_gate(
        repo_root=repo_root,
        problems_root=problems_root,
        config_rels=config_rels,
    )
    checks = [
        check_freeze_manifest(repo_root, freeze_manifest),
        *check_model_and_agent(repo_root, config_rels),
        check_evidence_problem_status(repo_root, config_rels),
        check_execution_bridge(repo_root),
        check_acceptance_snapshot_bridge(repo_root),
        check_c2_feedback_enforcement(repo_root, config_rels),
        check_acceptance_coverage(
            repo_root=repo_root,
            problems_root=problems_root,
            config_rels=config_rels,
        ),
        check_feature_runner_coverage(
            repo_root=repo_root,
            problems_root=problems_root,
            config_rels=config_rels,
        ),
        evidence_gate,
    ]
    status = "ready" if all(check["status"] == "pass" for check in checks) else "blocked"
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "profile": profile,
        "status": status,
        "freeze_manifest": freeze_manifest.as_posix(),
        "matrix_summary": matrix_summary(repo_root, problems_root, config_rels),
        "evidence_gate": {
            "ready": evidence_gate["ready"],
            "message": evidence_gate["message"],
            "blockers": evidence_gate["blockers"],
        },
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root_from_script())
    parser.add_argument(
        "--problems-root",
        type=Path,
        default=repo_root_from_script().parent / "scb-problems",
    )
    parser.add_argument(
        "--freeze-manifest",
        type=Path,
        default=repo_root_from_script()
        / "experiment/locks/pilot_artifact_freeze.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root_from_script() / "experiment/results/m11_full_pilot_preflight",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(CONFIG_PROFILES),
        default="pilot",
        help="Run matrix profile to preflight.",
    )
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Return exit code 0 even when the full pilot is blocked.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.root.resolve()
    freeze_manifest = args.freeze_manifest
    if not freeze_manifest.is_absolute():
        freeze_manifest = repo_root / freeze_manifest
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir

    report = run_preflight(
        repo_root=repo_root,
        problems_root=args.problems_root.resolve(),
        freeze_manifest=freeze_manifest,
        profile=args.profile,
    )
    write_json(output_dir / "preflight.json", report)
    write_text(output_dir / "preflight.md", markdown_report(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] == "ready" or args.allow_blocked:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
