#!/usr/bin/env python3
"""Validate whether the full pilot matrix is ready for primary execution."""

from __future__ import annotations

import argparse
import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

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
CONFIG_PROFILES = {
    "pilot": PILOT_CONFIGS,
    "screening": SCREENING_CONFIGS,
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
            total = checkpoint_count(problems_root, str(problem_id))
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
            problem: checkpoint_count(problems_root, problem)
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
        "# Full Pilot Preflight",
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
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The full pilot matrix is ready to execute."
                if report["status"] == "ready"
                else "The full pilot matrix is blocked. Do not run primary data collection until every gate check passes."
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
    checks = [
        check_freeze_manifest(repo_root, freeze_manifest),
        *check_model_and_agent(repo_root, config_rels),
        check_execution_bridge(repo_root),
        check_acceptance_snapshot_bridge(repo_root),
        check_acceptance_coverage(
            repo_root=repo_root,
            problems_root=problems_root,
            config_rels=config_rels,
        ),
    ]
    status = "ready" if all(check["status"] == "pass" for check in checks) else "blocked"
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "profile": profile,
        "status": status,
        "freeze_manifest": freeze_manifest.as_posix(),
        "matrix_summary": matrix_summary(repo_root, problems_root, config_rels),
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
