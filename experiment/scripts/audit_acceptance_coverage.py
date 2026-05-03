#!/usr/bin/env python3
"""Audit feature-scenario coverage by the locked C2 acceptance runner."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections import defaultdict
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_LEDGER = Path("experiment/steps/acceptance/coverage_ledger.yaml")
DEFAULT_RUNNER = Path("experiment/steps/acceptance/standalone_runner.py")
SCENARIO_RE = re.compile(r"^\s*Scenario(?: Outline)?:\s*(?P<name>.+?)\s*$")


class CoverageAuditError(ValueError):
    """Raised when coverage audit inputs are invalid."""


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise CoverageAuditError(f"Expected YAML mapping at {path}")
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


def checkpoint_index_from_path(path: Path) -> int:
    match = re.search(r"checkpoint_(\d+)\.feature$", path.name)
    if not match:
        raise CoverageAuditError(f"Cannot infer checkpoint index from {path}")
    return int(match.group(1))


def parse_feature_scenarios(
    *, repo_root: Path, feature_path: Path
) -> list[dict[str, Any]]:
    rel_path = feature_path.relative_to(repo_root).as_posix()
    problem_id = feature_path.parent.name
    checkpoint_index = checkpoint_index_from_path(feature_path)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        feature_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        match = SCENARIO_RE.match(line)
        if match is None:
            continue
        rows.append(
            {
                "problem_id": problem_id,
                "checkpoint_index": checkpoint_index,
                "feature_path": rel_path,
                "feature_line": line_number,
                "feature_scenario": match.group("name"),
            }
        )
    return rows


def feature_scenarios_for_selection(
    *,
    repo_root: Path,
    selected_slots: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for problem_id, checkpoint_index in sorted(selected_slots):
        feature_path = (
            repo_root
            / "experiment"
            / "features"
            / problem_id
            / f"checkpoint_{checkpoint_index:03d}.feature"
        )
        if not feature_path.is_file():
            rows.append(
                {
                    "problem_id": problem_id,
                    "checkpoint_index": checkpoint_index,
                    "feature_path": feature_path.relative_to(repo_root).as_posix(),
                    "feature_line": None,
                    "feature_scenario": None,
                    "coverage": "missing_feature_file",
                    "blocker": True,
                    "reason": "Selected C2 checkpoint has no feature file.",
                }
            )
            continue
        rows.extend(parse_feature_scenarios(repo_root=repo_root, feature_path=feature_path))
    return rows


def load_runner_scenarios(
    *, repo_root: Path, runner_path: Path
) -> dict[str, dict[str, Any]]:
    if not runner_path.is_absolute():
        runner_path = repo_root / runner_path
    spec = importlib.util.spec_from_file_location(
        "speccommons_standalone_acceptance", runner_path
    )
    if spec is None or spec.loader is None:
        raise CoverageAuditError(f"Cannot import acceptance runner: {runner_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = getattr(module, "SCENARIO_SPECS", None)
    if not isinstance(rows, list):
        raise CoverageAuditError(f"{runner_path} does not expose SCENARIO_SPECS")
    return {
        str(row["scenario_id"]): {
            key: value
            for key, value in row.items()
            if key != "scenario_func"
        }
        for row in rows
    }


def load_ledger(
    *, repo_root: Path, ledger_path: Path
) -> dict[tuple[str, int, str], dict[str, Any]]:
    if not ledger_path.is_absolute():
        ledger_path = repo_root / ledger_path
    payload = load_yaml(ledger_path)
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise CoverageAuditError(f"{ledger_path} must contain an entries list")
    index: dict[tuple[str, int, str], dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise CoverageAuditError(f"Invalid ledger entry in {ledger_path}: {entry!r}")
        try:
            key = (
                str(entry["problem_id"]),
                int(entry["checkpoint_index"]),
                str(entry["feature_scenario"]),
            )
        except KeyError as exc:
            raise CoverageAuditError(f"Ledger entry missing key: {entry!r}") from exc
        if key in index:
            raise CoverageAuditError(f"Duplicate ledger entry: {key!r}")
        index[key] = entry
    return index


def normalize_runner_ids(entry: dict[str, Any]) -> list[str]:
    raw = entry.get("runner_scenario_ids", [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise CoverageAuditError(
            f"runner_scenario_ids must be a list for {entry!r}"
        )
    return [str(item) for item in raw]


def evaluate_feature_row(
    *,
    feature_row: dict[str, Any],
    ledger: dict[tuple[str, int, str], dict[str, Any]],
    runner_scenarios: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if feature_row.get("coverage") == "missing_feature_file":
        return feature_row
    key = (
        str(feature_row["problem_id"]),
        int(feature_row["checkpoint_index"]),
        str(feature_row["feature_scenario"]),
    )
    entry = ledger.get(key)
    row = dict(feature_row)
    if entry is None:
        row.update(
            {
                "coverage": "missing_ledger",
                "runner_scenario_ids": [],
                "runner_scenarios": [],
                "blocker": True,
                "reason": "Feature scenario is not mapped in the acceptance coverage ledger.",
            }
        )
        return row

    coverage = str(entry.get("coverage", "")).strip()
    runner_ids = normalize_runner_ids(entry)
    runner_rows = [
        runner_scenarios[runner_id]
        for runner_id in runner_ids
        if runner_id in runner_scenarios
    ]
    missing_runner_ids = [
        runner_id for runner_id in runner_ids if runner_id not in runner_scenarios
    ]
    reason = str(entry.get("reason", "")).strip()
    row.update(
        {
            "coverage": coverage,
            "runner_scenario_ids": runner_ids,
            "runner_scenarios": runner_rows,
            "missing_runner_scenario_ids": missing_runner_ids,
            "reason": reason,
        }
    )
    if coverage == "executable":
        row["blocker"] = bool(missing_runner_ids) or not runner_ids
        if row["blocker"] and not reason:
            row["reason"] = "Executable coverage entry has no valid runner scenario."
    elif coverage == "spec_only":
        row["blocker"] = not reason
        if row["blocker"]:
            row["reason"] = "Spec-only scenario must include an omission reason."
    elif coverage == "required":
        row["blocker"] = True
        if not reason:
            row["reason"] = "Required scenario lacks executable runner coverage."
    else:
        row["coverage"] = "invalid_coverage"
        row["blocker"] = True
        if not reason:
            row["reason"] = f"Unsupported coverage value: {coverage!r}"
    return row


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_problem_checkpoint: dict[tuple[str, int], dict[str, Any]] = {}
    coverage_counts: dict[str, int] = defaultdict(int)
    blocker_rows = []
    omitted_rows = []
    for row in rows:
        coverage = str(row.get("coverage"))
        coverage_counts[coverage] += 1
        key = (str(row["problem_id"]), int(row["checkpoint_index"]))
        group = by_problem_checkpoint.setdefault(
            key,
            {
                "problem_id": key[0],
                "checkpoint_index": key[1],
                "feature_scenario_count": 0,
                "executable_scenario_count": 0,
                "spec_only_scenario_count": 0,
                "required_missing_count": 0,
                "blocker_count": 0,
            },
        )
        group["feature_scenario_count"] += 1
        if coverage == "executable":
            group["executable_scenario_count"] += 1
        if coverage == "spec_only":
            group["spec_only_scenario_count"] += 1
            omitted_rows.append(row)
        if coverage == "required":
            group["required_missing_count"] += 1
            omitted_rows.append(row)
        if row.get("blocker"):
            group["blocker_count"] += 1
            blocker_rows.append(row)
    return {
        "feature_scenario_count": len(rows),
        "executable_scenario_count": coverage_counts.get("executable", 0),
        "spec_only_scenario_count": coverage_counts.get("spec_only", 0),
        "required_missing_count": coverage_counts.get("required", 0),
        "missing_ledger_count": coverage_counts.get("missing_ledger", 0),
        "invalid_coverage_count": coverage_counts.get("invalid_coverage", 0),
        "blocker_count": len(blocker_rows),
        "coverage_counts": dict(sorted(coverage_counts.items())),
        "by_problem_checkpoint": sorted(
            by_problem_checkpoint.values(),
            key=lambda item: (item["problem_id"], item["checkpoint_index"]),
        ),
        "blockers": [
            {
                "problem_id": row.get("problem_id"),
                "checkpoint_index": row.get("checkpoint_index"),
                "feature_scenario": row.get("feature_scenario"),
                "coverage": row.get("coverage"),
                "reason": row.get("reason"),
            }
            for row in blocker_rows
        ],
        "omitted_scenarios": [
            {
                "problem_id": row.get("problem_id"),
                "checkpoint_index": row.get("checkpoint_index"),
                "feature_scenario": row.get("feature_scenario"),
                "coverage": row.get("coverage"),
                "reason": row.get("reason"),
            }
            for row in omitted_rows
        ],
    }


def build_coverage_audit(
    *,
    repo_root: Path,
    selected_slots: set[tuple[str, int]],
    ledger_path: Path = DEFAULT_LEDGER,
    runner_path: Path = DEFAULT_RUNNER,
) -> dict[str, Any]:
    runner_scenarios = load_runner_scenarios(
        repo_root=repo_root,
        runner_path=runner_path,
    )
    ledger = load_ledger(repo_root=repo_root, ledger_path=ledger_path)
    feature_rows = feature_scenarios_for_selection(
        repo_root=repo_root,
        selected_slots=selected_slots,
    )
    rows = [
        evaluate_feature_row(
            feature_row=row,
            ledger=ledger,
            runner_scenarios=runner_scenarios,
        )
        for row in feature_rows
    ]
    summary = summarize_rows(rows)
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "pass" if summary["blocker_count"] == 0 else "block",
        "ledger_path": (
            ledger_path
            if ledger_path.is_absolute()
            else repo_root / ledger_path
        ).relative_to(repo_root).as_posix(),
        "runner_path": (
            runner_path
            if runner_path.is_absolute()
            else repo_root / runner_path
        ).relative_to(repo_root).as_posix(),
        "selected_slots": [
            {"problem_id": problem_id, "checkpoint_index": checkpoint_index}
            for problem_id, checkpoint_index in sorted(selected_slots)
        ],
        "summary": summary,
        "rows": rows,
    }


def markdown_report(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    lines = [
        "# Acceptance Coverage Audit",
        "",
        f"Status: `{audit['status']}`",
        f"Generated at: `{audit['generated_at']}`",
        f"Ledger: `{audit['ledger_path']}`",
        f"Runner: `{audit['runner_path']}`",
        "",
        "## Summary",
        "",
        f"- Feature scenarios: `{summary['feature_scenario_count']}`",
        f"- Executable scenarios: `{summary['executable_scenario_count']}`",
        f"- Spec-only scenarios: `{summary['spec_only_scenario_count']}`",
        f"- Required missing scenarios: `{summary['required_missing_count']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        "",
        "## By Problem And Checkpoint",
        "",
        "| problem | checkpoint | feature scenarios | executable | spec-only | required missing | blockers |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["by_problem_checkpoint"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["problem_id"]),
                    str(row["checkpoint_index"]),
                    str(row["feature_scenario_count"]),
                    str(row["executable_scenario_count"]),
                    str(row["spec_only_scenario_count"]),
                    str(row["required_missing_count"]),
                    str(row["blocker_count"]),
                ]
            )
            + " |"
        )
    blockers = summary["blockers"]
    if blockers:
        lines.extend(
            [
                "",
                "## Blockers",
                "",
                "| problem | checkpoint | scenario | coverage | reason |",
                "| --- | ---: | --- | --- | --- |",
            ]
        )
        for row in blockers:
            reason = str(row.get("reason", "")).replace("|", "\\|")
            scenario = str(row.get("feature_scenario", "")).replace("|", "\\|")
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("problem_id")),
                        str(row.get("checkpoint_index")),
                        scenario,
                        str(row.get("coverage")),
                        reason,
                    ]
                )
                + " |"
            )
    omitted = summary["omitted_scenarios"]
    if omitted:
        lines.extend(
            [
                "",
                "## Omitted Or Pending Scenarios",
                "",
                "| problem | checkpoint | scenario | coverage | reason |",
                "| --- | ---: | --- | --- | --- |",
            ]
        )
        for row in omitted:
            reason = str(row.get("reason", "")).replace("|", "\\|")
            scenario = str(row.get("feature_scenario", "")).replace("|", "\\|")
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("problem_id")),
                        str(row.get("checkpoint_index")),
                        scenario,
                        str(row.get("coverage")),
                        reason,
                    ]
                )
                + " |"
            )
    return "\n".join(lines)


def selected_slots_from_args(args: argparse.Namespace) -> set[tuple[str, int]]:
    slots: set[tuple[str, int]] = set()
    for raw in args.slot:
        try:
            problem_id, checkpoint = raw.split(":", 1)
            slots.add((problem_id, int(checkpoint)))
        except ValueError as exc:
            raise CoverageAuditError(
                f"Invalid --slot value {raw!r}; expected problem_id:checkpoint_index"
            ) from exc
    return slots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root_from_script())
    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_LEDGER,
        help="Coverage ledger path relative to the repo root.",
    )
    parser.add_argument(
        "--runner",
        type=Path,
        default=DEFAULT_RUNNER,
        help="Standalone acceptance runner path relative to the repo root.",
    )
    parser.add_argument(
        "--slot",
        action="append",
        default=[],
        help="Selected C2 slot as problem_id:checkpoint_index. Repeatable.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root_from_script() / "experiment/results/acceptance_coverage_audit",
    )
    parser.add_argument("--allow-blocked", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.root.resolve()
    selected_slots = selected_slots_from_args(args)
    if not selected_slots:
        raise CoverageAuditError("At least one --slot is required")
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    audit = build_coverage_audit(
        repo_root=repo_root,
        selected_slots=selected_slots,
        ledger_path=args.ledger,
        runner_path=args.runner,
    )
    write_json(output_dir / "coverage_audit.json", audit)
    write_text(output_dir / "coverage_audit.md", markdown_report(audit))
    print(json.dumps(audit, indent=2, sort_keys=True))
    if audit["status"] == "pass" or args.allow_blocked:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
