#!/usr/bin/env python3
"""Create and verify the pre-execution pilot artifact freeze manifest."""

from __future__ import annotations

import argparse
import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import verify_locks
import yaml
from git import InvalidGitRepositoryError
from git import Repo

DEFAULT_FROZEN_PATHS = [
    "docs/experiment/**",
    "experiment/README.md",
    "experiment/REPRODUCIBILITY.md",
    "experiment/FORK_SETUP.md",
    "experiment/configs/screening_c0.yaml",
    "experiment/configs/screening_c1.yaml",
    "experiment/configs/screening_c2.yaml",
    "experiment/configs/pilot_c0.yaml",
    "experiment/configs/pilot_c1.yaml",
    "experiment/configs/pilot_c2.yaml",
    "experiment/features/**",
    "experiment/prompts/**",
    "experiment/steps/**",
    "experiment/scripts/**",
    "experiment/schemas/**",
]
DEFAULT_MATRIX_PATHS = [
    "experiment/configs/pilot_c0.yaml",
    "experiment/configs/pilot_c1.yaml",
    "experiment/configs/pilot_c2.yaml",
]
FREEZE_OUTPUT_PATH = Path("experiment/locks/pilot_artifact_freeze.json")


class FreezeError(ValueError):
    """Raised when the freeze manifest cannot be created or verified."""


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise FreezeError(f"Expected YAML mapping at {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise FreezeError(f"Expected JSON object at {path}")
    return payload


def repo_metadata(root: Path) -> dict[str, Any]:
    try:
        repo = Repo(root)
    except InvalidGitRepositoryError:
        return {
            "branch": "unknown",
            "head_commit_at_manifest_generation": "unknown",
            "freeze_commit_note": "not a git repository",
        }
    return {
        "branch": repo.active_branch.name,
        "head_commit_at_manifest_generation": repo.head.commit.hexsha,
        "freeze_commit_note": (
            "Use the commit containing this manifest, or a tag pointing at that "
            "commit, as the immutable experiment freeze reference."
        ),
    }


def checkpoint_count(problems_root: Path, problem_id: str) -> int | None:
    config_path = problems_root / problem_id / "config.yaml"
    if not config_path.is_file():
        return None
    config = load_yaml(config_path)
    checkpoints = config.get("checkpoints")
    if not isinstance(checkpoints, dict):
        return None
    return len(checkpoints)


def summarize_matrix(
    *, matrix_path: Path, problems_root: Path
) -> dict[str, Any]:
    matrix = load_yaml(matrix_path)
    problems = [str(problem) for problem in matrix.get("problems", [])]
    replicates = matrix.get("replicates", [])
    if not isinstance(replicates, list):
        raise FreezeError(f"{matrix_path} replicates must be a list")

    checkpoint_counts = {
        problem: checkpoint_count(problems_root, problem) for problem in problems
    }
    checkpoint_total_per_replicate = sum(
        value for value in checkpoint_counts.values() if value is not None
    )
    return {
        "matrix_id": matrix["matrix_id"],
        "condition_id": matrix["condition"]["id"],
        "path": matrix_path.as_posix(),
        "problem_count": len(problems),
        "problems": problems,
        "replicate_count": len(replicates),
        "replicate_ids": [replicate["replicate_id"] for replicate in replicates],
        "trajectory_count": len(problems) * len(replicates),
        "checkpoint_counts": checkpoint_counts,
        "checkpoint_executions": checkpoint_total_per_replicate * len(replicates),
        "model_name": matrix["model"]["name"],
        "agent_harness": matrix["agent_harness"]["id"],
    }


def summarize_matrices(
    *, repo_root: Path, problems_root: Path, matrix_paths: list[str]
) -> dict[str, Any]:
    matrices = [
        summarize_matrix(
            matrix_path=repo_root / matrix_path,
            problems_root=problems_root,
        )
        for matrix_path in matrix_paths
    ]
    return {
        "matrices": matrices,
        "total_trajectories": sum(matrix["trajectory_count"] for matrix in matrices),
        "total_checkpoint_executions": sum(
            matrix["checkpoint_executions"] for matrix in matrices
        ),
        "conditions": [matrix["condition_id"] for matrix in matrices],
        "problems": sorted(
            {
                problem
                for matrix in matrices
                for problem in matrix["problems"]
            }
        ),
    }


def build_freeze_manifest(
    *,
    repo_root: Path,
    problems_root: Path,
    frozen_paths: list[str],
    matrix_paths: list[str],
) -> dict[str, Any]:
    lock_manifest = verify_locks.build_manifest(
        root=repo_root,
        locked_paths=frozen_paths,
    )
    matrix_summary = summarize_matrices(
        repo_root=repo_root,
        problems_root=problems_root,
        matrix_paths=matrix_paths,
    )
    manifest: dict[str, Any] = {
        **lock_manifest,
        "freeze_schema_version": 1,
        "freeze_created_at": utc_now(),
        "freeze_status": "pre_execution_artifact_freeze",
        "artifact_policy": (
            "Feature files, step helpers, prompts, schemas, runner/export scripts, "
            "pilot configs, and experiment docs are frozen before primary data "
            "collection. Any later edit requires a new freeze manifest and a "
            "deviation entry."
        ),
        "git": repo_metadata(repo_root),
        "problems_root": problems_root.resolve().as_posix(),
        "matrix_summary": matrix_summary,
        "primary_run_gate": {
            "status": "blocked",
            "reason": (
                "The artifact package is frozen, but the full pilot should not run "
                "until the native execution bridge and C2 snapshot acceptance "
                "integration are implemented."
            ),
        },
    }
    manifest["freeze_hash"] = verify_locks.sha256_json(
        {
            "manifest_hash": manifest["manifest_hash"],
            "matrix_summary": manifest["matrix_summary"],
            "artifact_policy": manifest["artifact_policy"],
            "primary_run_gate": manifest["primary_run_gate"],
        }
    )
    return manifest


def verify_freeze(*, manifest_path: Path, repo_root: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    verification = verify_locks.verify_manifest(
        baseline_manifest=manifest,
        root=repo_root,
    )
    return {
        "schema_version": 1,
        "checked_at": utc_now(),
        "manifest_path": manifest_path.as_posix(),
        "freeze_hash": manifest.get("freeze_hash"),
        "freeze_status": manifest.get("freeze_status"),
        "status": verification["status"],
        "protocol_violation": verification["protocol_violation"],
        "file_count_before": verification["file_count_before"],
        "file_count_after": verification["file_count_after"],
        "added_files": verification["added_files"],
        "removed_files": verification["removed_files"],
        "changed_files": verification["changed_files"],
        "missing_patterns_before": verification["missing_patterns_before"],
        "missing_patterns_after": verification["missing_patterns_after"],
        "primary_run_gate": manifest.get("primary_run_gate", {}),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot", help="Write freeze manifest.")
    snapshot.add_argument("--root", type=Path, default=repo_root_from_script())
    snapshot.add_argument(
        "--problems-root",
        type=Path,
        default=repo_root_from_script().parent / "scb-problems",
    )
    snapshot.add_argument("--output", type=Path, default=FREEZE_OUTPUT_PATH)
    snapshot.add_argument(
        "--frozen-path",
        action="append",
        default=[],
        help="Additional frozen path or glob relative to the repo root.",
    )
    snapshot.add_argument(
        "--matrix",
        action="append",
        default=[],
        help="Pilot matrix path relative to the repo root.",
    )

    verify = subparsers.add_parser("verify", help="Verify freeze manifest.")
    verify.add_argument("--root", type=Path, default=repo_root_from_script())
    verify.add_argument("--manifest", type=Path, default=FREEZE_OUTPUT_PATH)
    verify.add_argument(
        "--print-json",
        action="store_true",
        help="Print full verification JSON instead of one-line status.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "snapshot":
        repo_root = args.root.resolve()
        frozen_paths = DEFAULT_FROZEN_PATHS + list(args.frozen_path)
        matrix_paths = list(args.matrix) or DEFAULT_MATRIX_PATHS
        manifest = build_freeze_manifest(
            repo_root=repo_root,
            problems_root=args.problems_root.resolve(),
            frozen_paths=frozen_paths,
            matrix_paths=matrix_paths,
        )
        output_path = args.output
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        write_json(output_path, manifest)
        print(f"freeze_hash: {manifest['freeze_hash']}")
        print(f"manifest: {output_path}")
        print(f"files: {len(manifest['files'])}")
        print(
            "total_trajectories: "
            f"{manifest['matrix_summary']['total_trajectories']}"
        )
        print(
            "total_checkpoint_executions: "
            f"{manifest['matrix_summary']['total_checkpoint_executions']}"
        )
        return 0

    repo_root = args.root.resolve()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    result = verify_freeze(manifest_path=manifest_path, repo_root=repo_root)
    if args.print_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"freeze_status: {result['status']}")
        print(f"freeze_hash: {result['freeze_hash']}")
    return 1 if result["protocol_violation"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
