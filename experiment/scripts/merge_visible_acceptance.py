#!/usr/bin/env python3
"""Merge visible acceptance scenario results into normalized result tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class MergeError(ValueError):
    """Raised when visible acceptance results cannot be merged."""


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
                raise MergeError(f"Expected JSON object at {path}:{line_number}")
            rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def visible_passed(rows: list[dict[str, Any]]) -> bool | None:
    runnable = [row for row in rows if row.get("status") != "skipped"]
    if not runnable:
        return None
    return all(row.get("status") == "passed" for row in runnable)


def duration_ms(rows: list[dict[str, Any]]) -> float | None:
    values = [
        float(row["duration_ms"])
        for row in rows
        if isinstance(row.get("duration_ms"), int | float)
    ]
    if not values:
        return None
    return sum(values)


def merge_visible_acceptance(
    *, results_dir: Path, acceptance_root: Path
) -> dict[str, Any]:
    checkpoint_path = results_dir / "checkpoints.jsonl"
    technical_path = results_dir / "technical_metrics.jsonl"
    checkpoints = read_jsonl(checkpoint_path)
    technical_rows = read_jsonl(technical_path)
    technical_index = {
        (str(row["run_id"]), str(row["checkpoint_id"])): row
        for row in technical_rows
    }

    merged = 0
    for row in checkpoints:
        scenario_path = acceptance_root / str(row["checkpoint_id"]) / "scenarios.jsonl"
        scenario_rows = read_jsonl(scenario_path)
        if not scenario_rows:
            continue
        passed = visible_passed(scenario_rows)
        row["visible_acceptance_passed"] = passed
        row["scenario_results"] = scenario_rows
        row["hidden_failure_after_visible_pass"] = (
            passed is True and row.get("hidden_tests_passed") is False
        )
        artifact_paths = dict(row.get("artifact_paths") or {})
        artifact_paths["visible_acceptance"] = scenario_path.parent.as_posix()
        row["artifact_paths"] = artifact_paths
        technical = technical_index.get((str(row["run_id"]), str(row["checkpoint_id"])))
        if technical is not None:
            technical["acceptance_runtime_ms"] = duration_ms(scenario_rows)
        merged += 1

    write_jsonl(checkpoint_path, checkpoints)
    write_jsonl(technical_path, technical_rows)
    summary = {
        "schema_version": 1,
        "results_dir": results_dir.as_posix(),
        "acceptance_root": acceptance_root.as_posix(),
        "checkpoint_rows_merged": merged,
    }
    write_json(results_dir / "visible_acceptance_merge.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--acceptance-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = merge_visible_acceptance(
        results_dir=args.results_dir.resolve(),
        acceptance_root=args.acceptance_root.resolve(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
