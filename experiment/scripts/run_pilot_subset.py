#!/usr/bin/env python3
"""Run reproducible MVP or pilot trajectory subsets through the wrapper."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import run_trajectory

SUBSET_CONFIGS = {
    "mini_screen": ["mini_screen_c0.yaml", "mini_screen_c2.yaml"],
    "mvp": ["mvp_c0.yaml", "mvp_c2.yaml"],
    "screening": ["screening_c0.yaml", "screening_c1.yaml", "screening_c2.yaml"],
    "pilot": ["pilot_c0.yaml", "pilot_c1.yaml", "pilot_c2.yaml"],
}


class SubsetRunError(ValueError):
    """Raised when a subset cannot be prepared."""


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def selected_config_paths(
    *, repo_root: Path, subset: str, condition_ids: list[str] | None
) -> list[Path]:
    config_dir = repo_root / "experiment" / "configs"
    paths = [config_dir / name for name in SUBSET_CONFIGS[subset]]
    if not condition_ids:
        return paths

    selected: list[Path] = []
    condition_set = set(condition_ids)
    for path in paths:
        matrix = run_trajectory.load_run_matrix(path)
        if matrix["condition"]["id"] in condition_set:
            selected.append(path)
    if not selected:
        raise SubsetRunError("condition filter selected no run matrices")
    return selected


def selected_problems(
    matrix_config: dict[str, Any], problem_filter: list[str] | None
) -> list[str]:
    problems = list(matrix_config["problems"])
    if not problem_filter:
        return problems
    selected = [problem for problem in problems if problem in set(problem_filter)]
    if not selected:
        raise SubsetRunError(
            f"problem filter selected no problems for {matrix_config['matrix_id']}"
        )
    return selected


def selected_replicates(
    matrix_config: dict[str, Any], replicate_filter: list[int] | None
) -> list[int]:
    replicate_ids = [int(rep["replicate_id"]) for rep in matrix_config["replicates"]]
    if not replicate_filter:
        return replicate_ids
    selected = [rep for rep in replicate_ids if rep in set(replicate_filter)]
    if not selected:
        raise SubsetRunError(
            f"replicate filter selected no replicates for {matrix_config['matrix_id']}"
        )
    return selected


def subset_run_id(
    *,
    prefix: str,
    matrix_id: str,
    problem_id: str,
    replicate_id: int,
) -> str:
    return f"{prefix}-{matrix_id}-{problem_id}-r{replicate_id:02d}"


def matrix_checkpoint_limit(matrix_config: dict[str, Any]) -> int | None:
    raw = matrix_config.get("checkpoint_limit")
    if raw is None:
        return None
    if not isinstance(raw, int) or raw <= 0:
        raise SubsetRunError(
            f"{matrix_config['matrix_id']} checkpoint_limit must be a positive integer"
        )
    return raw


def run_subset(
    *,
    subset: str,
    mode: str,
    problems_root: Path,
    run_root: Path | None,
    condition_ids: list[str] | None,
    problem_filter: list[str] | None,
    replicate_filter: list[int] | None,
    run_id_prefix: str,
    checkpoint_limit: int | None,
) -> list[dict[str, Any]]:
    repo_root = repo_root_from_script()
    summaries: list[dict[str, Any]] = []
    for config_path in selected_config_paths(
        repo_root=repo_root,
        subset=subset,
        condition_ids=condition_ids,
    ):
        matrix = run_trajectory.load_run_matrix(config_path)
        for problem_id in selected_problems(matrix, problem_filter):
            for replicate_id in selected_replicates(matrix, replicate_filter):
                run_id = subset_run_id(
                    prefix=run_id_prefix,
                    matrix_id=matrix["matrix_id"],
                    problem_id=problem_id,
                    replicate_id=replicate_id,
                )
                result = run_trajectory.run_trajectory(
                    config_path=config_path.resolve(),
                    problem_id=problem_id,
                    replicate_id=replicate_id,
                    problems_root=problems_root.resolve(),
                    mode=mode,
                    run_id=run_id,
                    run_root_override=run_root.resolve() if run_root else None,
                    checkpoint_limit=checkpoint_limit
                    if checkpoint_limit is not None
                    else matrix_checkpoint_limit(matrix),
                )
                summaries.append(result.run_record)
                print(
                    f"{result.run_record['status']}: "
                    f"{result.run_id} -> {result.artifact_root}"
                )
    return summaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", choices=sorted(SUBSET_CONFIGS), required=True)
    parser.add_argument(
        "--mode",
        choices=["dry-run", "native-dry-run", "native-run"],
        default="dry-run",
    )
    parser.add_argument(
        "--problems-root",
        type=Path,
        default=repo_root_from_script().parent / "scb-problems",
    )
    parser.add_argument("--run-root", type=Path)
    parser.add_argument(
        "--condition",
        action="append",
        choices=["C0", "C1", "C2"],
        help="Condition id to include, repeatable.",
    )
    parser.add_argument(
        "--problem",
        action="append",
        help="Problem id to include, repeatable.",
    )
    parser.add_argument(
        "--replicate-id",
        action="append",
        type=int,
        help="Replicate id to include, repeatable.",
    )
    parser.add_argument(
        "--run-id-prefix",
        default="subset-dry-run",
        help="Prefix used to create deterministic run ids.",
    )
    parser.add_argument(
        "--checkpoint-limit",
        type=int,
        help="Limit each trajectory to the first N checkpoints.",
    )
    parser.add_argument(
        "--summary-jsonl",
        type=Path,
        help="Optional path for aggregate run records.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summaries = run_subset(
        subset=args.subset,
        mode=args.mode,
        problems_root=args.problems_root,
        run_root=args.run_root,
        condition_ids=args.condition,
        problem_filter=args.problem,
        replicate_filter=args.replicate_id,
        run_id_prefix=args.run_id_prefix,
        checkpoint_limit=args.checkpoint_limit,
    )
    if args.summary_jsonl is not None:
        write_jsonl(args.summary_jsonl, summaries)
    return 0 if all(row["status"] != "invalid_lock_violation" for row in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
