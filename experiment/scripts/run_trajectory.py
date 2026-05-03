#!/usr/bin/env python3
"""Orchestrate one experiment trajectory, starting with dry-run integration."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import generate_condition_context as prompt_context
import verify_locks
from git import Repo


class TrajectoryError(ValueError):
    """Raised when a trajectory cannot be prepared or run."""


@dataclass(frozen=True)
class TrajectoryResult:
    """Summary for a prepared trajectory run."""

    run_id: str
    artifact_root: Path
    run_record: dict[str, Any]
    checkpoint_records: list[dict[str, Any]]


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def timestamp_id() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def rel_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


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


def current_git_commit(root: Path) -> str:
    try:
        return Repo(root).head.commit.hexsha
    except Exception:  # noqa: BLE001
        return "unknown"


def load_run_matrix(config_path: Path) -> dict[str, Any]:
    return prompt_context.load_yaml(config_path)


def find_replicate(matrix_config: dict[str, Any], replicate_id: int) -> dict[str, Any]:
    for replicate in matrix_config["replicates"]:
        if int(replicate["replicate_id"]) == replicate_id:
            return replicate
    raise TrajectoryError(f"replicate_id {replicate_id} is not in run matrix")


def validate_problem(matrix_config: dict[str, Any], problem_id: str) -> None:
    if problem_id not in matrix_config["problems"]:
        matrix_id = matrix_config["matrix_id"]
        raise TrajectoryError(f"{problem_id} is not listed in {matrix_id}")


def default_run_id(
    *, matrix_id: str, condition_id: str, problem_id: str, replicate_id: int
) -> str:
    return (
        f"{timestamp_id()}-{matrix_id}-{condition_id.lower()}-"
        f"{problem_id}-r{replicate_id:02d}"
    )


def trajectory_root(
    *,
    repo_root: Path,
    matrix_config: dict[str, Any],
    problem_id: str,
    replicate_id: int,
    run_id: str,
    run_root_override: Path | None,
) -> Path:
    if run_root_override is not None:
        base = run_root_override
    else:
        base = repo_root / matrix_config["outputs"]["run_root"]
    return base / problem_id / f"replicate_{replicate_id:02d}" / run_id


def ordered_checkpoints(
    *, problems_root: Path, problem_id: str
) -> tuple[dict[str, Any], list[str]]:
    problem_config = prompt_context.load_yaml(
        problems_root / problem_id / "config.yaml"
    )
    return problem_config, prompt_context.ordered_checkpoints(problem_config)


def lock_before_checkpoint(
    *,
    repo_root: Path,
    lock_policy: dict[str, Any],
    checkpoint_dir: Path,
) -> dict[str, Any] | None:
    if lock_policy["mode"] == "none":
        return None
    locked_paths = [str(path) for path in lock_policy["locked_paths"]]
    manifest = verify_locks.build_manifest(
        root=repo_root,
        locked_paths=locked_paths,
    )
    write_json(checkpoint_dir / "locks" / "before.json", manifest)
    return manifest


def lock_after_checkpoint(
    *,
    repo_root: Path,
    before_manifest: dict[str, Any] | None,
    checkpoint_dir: Path,
) -> dict[str, Any]:
    if before_manifest is None:
        result = {
            "schema_version": 1,
            "checked_at": utc_now(),
            "status": "not_applicable",
            "protocol_violation": False,
            "manifest_hash": None,
            "current_manifest_hash": None,
            "file_count_before": 0,
            "file_count_after": 0,
            "added_files": [],
            "removed_files": [],
            "changed_files": [],
            "missing_patterns_before": [],
            "missing_patterns_after": [],
        }
    else:
        result = verify_locks.verify_manifest(
            baseline_manifest=before_manifest,
            root=repo_root,
        )
    write_json(checkpoint_dir / "locks" / "after.json", result)
    return result


def planned_commands(
    *,
    condition_id: str,
    problem_id: str,
    checkpoint_id: str,
    config_path: Path,
    problems_root: Path,
    prompt_output_dir: Path,
) -> dict[str, str | None]:
    command = prompt_context.acceptance_command_text(
        condition_id=condition_id,
        problem_id=problem_id,
        checkpoint_id=checkpoint_id,
    )
    acceptance = command if condition_id == "C2" else None
    return {
        "render_prompt": (
            "uv run python experiment/scripts/generate_condition_context.py "
            f"--config {config_path.as_posix()} "
            f"--problem {problem_id} "
            f"--checkpoint {checkpoint_id} "
            f"--problems-root {problems_root.as_posix()} "
            f"--output-dir {prompt_output_dir.as_posix()}"
        ),
        "visible_acceptance": acceptance,
        "native_scbench_agent": "not executed in dry-run mode",
        "native_scbench_hidden_eval": "not executed in dry-run mode",
    }


def checkpoint_record(
    *,
    matrix_config: dict[str, Any],
    run_id: str,
    problem_id: str,
    checkpoint_id: str,
    checkpoint_index: int,
    replicate_id: int,
    replicate_seed: int,
    experiment_commit: str,
    prompt_metadata: dict[str, Any],
    lock_result: dict[str, Any],
    checkpoint_dir: Path,
    repo_root: Path,
    started_at: str,
    ended_at: str,
) -> dict[str, Any]:
    condition_id = matrix_config["condition"]["id"]
    status = (
        "invalid_lock_violation"
        if lock_result["protocol_violation"]
        else "dry_run_prepared"
    )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "condition_id": condition_id,
        "problem_id": problem_id,
        "checkpoint_id": checkpoint_id,
        "checkpoint_index": checkpoint_index,
        "replicate_id": replicate_id,
        "replicate_seed": replicate_seed,
        "model": matrix_config["model"]["name"],
        "agent_harness": matrix_config["agent_harness"]["id"],
        "agent_version": matrix_config["agent_harness"]["version"],
        "benchmark_commit": matrix_config["runner"]["benchmark_commit"],
        "problems_commit": matrix_config["runner"]["problem_commit"],
        "experiment_commit": experiment_commit,
        "started_at": started_at,
        "ended_at": ended_at,
        "status": status,
        "prompt_template_id": prompt_metadata["prompt_template_id"],
        "prompt_hash": prompt_metadata["prompt_hash"],
        "context_hash": prompt_metadata["original_spec_hash"],
        "feature_hash": prompt_metadata["gherkin_context_hash"],
        "lock_manifest_hash": lock_result["manifest_hash"],
        "lock_status": lock_result["status"],
        "protocol_violation": lock_result["protocol_violation"],
        "visible_acceptance_passed": None,
        "hidden_tests_passed": None,
        "current_checkpoint_passed": None,
        "prior_regression_count": None,
        "hidden_failure_after_visible_pass": None,
        "scenario_results": [],
        "hidden_test_summary": {},
        "technical_metrics": {},
        "cost_metrics": {},
        "artifact_paths": {
            "checkpoint_dir": rel_path(checkpoint_dir, repo_root),
            "prompt": rel_path(Path(prompt_metadata["prompt_path"]), repo_root)
            if "prompt_path" in prompt_metadata
            else None,
            "prompt_metadata": rel_path(
                Path(prompt_metadata["metadata_path"]), repo_root
            )
            if "metadata_path" in prompt_metadata
            else None,
            "lock_before": rel_path(checkpoint_dir / "locks" / "before.json", repo_root),
            "lock_after": rel_path(checkpoint_dir / "locks" / "after.json", repo_root),
        },
    }


def write_planned_commands(path: Path, commands: dict[str, str | None]) -> None:
    lines = ["# Planned Commands", ""]
    for name, command in commands.items():
        lines.append(f"## {name}")
        lines.append("")
        if command is None:
            lines.append("not applicable")
        else:
            lines.extend(["```bash", command, "```"])
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_trajectory(
    *,
    config_path: Path,
    problem_id: str,
    replicate_id: int,
    problems_root: Path,
    mode: str,
    run_id: str | None = None,
    run_root_override: Path | None = None,
) -> TrajectoryResult:
    if mode != "dry-run":
        raise TrajectoryError("only dry-run mode is implemented for Milestone 8")

    repo_root = repo_root_from_script()
    matrix_config = load_run_matrix(config_path)
    condition_id = matrix_config["condition"]["id"]
    matrix_id = matrix_config["matrix_id"]
    validate_problem(matrix_config, problem_id)
    replicate = find_replicate(matrix_config, replicate_id)
    problem_config, checkpoints = ordered_checkpoints(
        problems_root=problems_root,
        problem_id=problem_id,
    )
    current_run_id = run_id or default_run_id(
        matrix_id=matrix_id,
        condition_id=condition_id,
        problem_id=problem_id,
        replicate_id=replicate_id,
    )
    root = trajectory_root(
        repo_root=repo_root,
        matrix_config=matrix_config,
        problem_id=problem_id,
        replicate_id=replicate_id,
        run_id=current_run_id,
        run_root_override=run_root_override,
    )
    root.mkdir(parents=True, exist_ok=True)

    experiment_commit = current_git_commit(repo_root)
    started_at = utc_now()
    checkpoint_records: list[dict[str, Any]] = []

    for checkpoint_index, checkpoint_id in enumerate(checkpoints, start=1):
        checkpoint_started = utc_now()
        checkpoint_dir = root / "checkpoints" / checkpoint_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        before_manifest = lock_before_checkpoint(
            repo_root=repo_root,
            lock_policy=matrix_config["lock_policy"],
            checkpoint_dir=checkpoint_dir,
        )
        rendered = prompt_context.render_condition_context(
            config_path=config_path,
            problem_id=problem_id,
            checkpoint_ref=checkpoint_id,
            problems_root=problems_root,
            output_dir=checkpoint_dir / "prompt_context",
        )
        prompt_metadata = dict(rendered.metadata)
        prompt_metadata["prompt_path"] = rendered.prompt_path.as_posix()
        prompt_metadata["metadata_path"] = rendered.metadata_path.as_posix()
        commands = planned_commands(
            condition_id=condition_id,
            problem_id=problem_id,
            checkpoint_id=checkpoint_id,
            config_path=config_path,
            problems_root=problems_root,
            prompt_output_dir=checkpoint_dir / "prompt_context",
        )
        write_planned_commands(checkpoint_dir / "planned_commands.md", commands)
        lock_result = lock_after_checkpoint(
            repo_root=repo_root,
            before_manifest=before_manifest,
            checkpoint_dir=checkpoint_dir,
        )
        checkpoint_ended = utc_now()
        checkpoint_records.append(
            checkpoint_record(
                matrix_config=matrix_config,
                run_id=current_run_id,
                problem_id=problem_id,
                checkpoint_id=checkpoint_id,
                checkpoint_index=checkpoint_index,
                replicate_id=replicate_id,
                replicate_seed=int(replicate["seed"]),
                experiment_commit=experiment_commit,
                prompt_metadata=prompt_metadata,
                lock_result=lock_result,
                checkpoint_dir=checkpoint_dir,
                repo_root=repo_root,
                started_at=checkpoint_started,
                ended_at=checkpoint_ended,
            )
        )

    ended_at = utc_now()
    protocol_violation = any(row["protocol_violation"] for row in checkpoint_records)
    run_status = (
        "invalid_lock_violation" if protocol_violation else "dry_run_prepared"
    )
    run_record = {
        "schema_version": 1,
        "run_id": current_run_id,
        "condition_id": condition_id,
        "problem_id": problem_id,
        "replicate_id": replicate_id,
        "replicate_seed": int(replicate["seed"]),
        "model": matrix_config["model"]["name"],
        "agent_harness": matrix_config["agent_harness"]["id"],
        "agent_version": matrix_config["agent_harness"]["version"],
        "benchmark_repo": matrix_config["runner"]["benchmark_repo"],
        "benchmark_commit": matrix_config["runner"]["benchmark_commit"],
        "problems_repo": matrix_config["runner"]["problem_repo"],
        "problems_commit": matrix_config["runner"]["problem_commit"],
        "experiment_commit": experiment_commit,
        "started_at": started_at,
        "ended_at": ended_at,
        "status": run_status,
        "mode": mode,
        "checkpoint_count_expected": len(problem_config["checkpoints"]),
        "checkpoint_count_completed": len(checkpoint_records),
        "strict_survival_checkpoint": None,
        "artifact_root": rel_path(root, repo_root),
    }

    write_json(root / "run.json", run_record)
    write_jsonl(root / "checkpoints.jsonl", checkpoint_records)
    return TrajectoryResult(
        run_id=current_run_id,
        artifact_root=root,
        run_record=run_record,
        checkpoint_records=checkpoint_records,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--problem", required=True)
    parser.add_argument("--replicate-id", type=int, required=True)
    parser.add_argument(
        "--problems-root",
        type=Path,
        default=repo_root_from_script().parent / "scb-problems",
    )
    parser.add_argument("--mode", choices=["dry-run"], default="dry-run")
    parser.add_argument("--run-id")
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_trajectory(
        config_path=args.config.resolve(),
        problem_id=args.problem,
        replicate_id=args.replicate_id,
        problems_root=args.problems_root.resolve(),
        mode=args.mode,
        run_id=args.run_id,
        run_root_override=args.run_root.resolve() if args.run_root else None,
    )
    if args.print_json:
        print(json.dumps(result.run_record, indent=2, sort_keys=True))
    else:
        print(f"run_id: {result.run_id}")
        print(f"artifact_root: {result.artifact_root}")
        print(f"status: {result.run_record['status']}")
    return 0 if result.run_record["status"] != "invalid_lock_violation" else 1


if __name__ == "__main__":
    raise SystemExit(main())
