#!/usr/bin/env python3
"""Validate experiment run-matrix YAML files against the local schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return loaded


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected YAML object at {path}")
    return loaded


def validate_condition_consistency(path: Path, payload: dict[str, Any]) -> list[str]:
    errors = []
    condition = payload["condition"]
    condition_id = condition["id"]
    gherkin_visible = condition["gherkin_context_visible"]
    harness_visible = condition["acceptance_harness_visible"]
    harness_runnable = condition["acceptance_harness_runnable"]
    lock_policy = payload["lock_policy"]
    lock_mode = lock_policy["mode"]
    locked_paths = set(lock_policy["locked_paths"])

    if not payload["matrix_id"].endswith(condition_id.lower()):
        errors.append("matrix_id must end with the lowercase condition id")

    if condition_id == "C0":
        if gherkin_visible or harness_visible or harness_runnable:
            errors.append("C0 must not expose Gherkin or acceptance harness")
        if lock_mode != "none":
            errors.append("C0 lock mode must be none")
    elif condition_id == "C1":
        if not gherkin_visible:
            errors.append("C1 must expose Gherkin context")
        if harness_visible or harness_runnable:
            errors.append("C1 must not expose runnable harness files")
        if lock_mode != "manifest_before_after_checkpoint":
            errors.append("C1 must verify the feature/prompt lock manifest")
        for required_path in {"experiment/features/**", "experiment/prompts/**"}:
            if required_path not in locked_paths:
                errors.append(f"C1 lock policy must include {required_path}")
    elif condition_id == "C2":
        if not (gherkin_visible and harness_visible and harness_runnable):
            errors.append("C2 must expose runnable Gherkin acceptance harness")
        if lock_mode != "manifest_before_after_checkpoint":
            errors.append("C2 must verify locked experiment files")
        for required_path in {
            "experiment/features/**",
            "experiment/steps/**",
            "experiment/prompts/**",
            "experiment/scripts/**",
            "experiment/schemas/**",
            "experiment/locks/**",
        }:
            if required_path not in locked_paths:
                errors.append(f"C2 lock policy must include {required_path}")

    if condition["hidden_tests_visible_to_agent"]:
        errors.append("hidden tests must never be visible to the agent")

    return [f"{path}: {error}" for error in errors]


def validate_files(paths: list[Path], schema_path: Path) -> int:
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    failures: list[str] = []

    for path in paths:
        payload = load_yaml(path)
        schema_failures = [
            f"{path}: {error.message}"
            for error in sorted(validator.iter_errors(payload), key=str)
        ]
        failures.extend(schema_failures)
        if not schema_failures:
            failures.extend(validate_condition_consistency(path, payload))

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    for path in paths:
        print(f"valid: {path}")
    return 0


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=sorted((repo_root / "experiment" / "configs").glob("*.yaml")),
        help="Run-matrix YAML files to validate.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=repo_root / "experiment" / "schemas" / "run_matrix.schema.json",
        help="JSON schema path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = [path.resolve() for path in args.paths]
    if not paths:
        print("No run-matrix YAML files found.", file=sys.stderr)
        return 1
    return validate_files(paths, args.schema.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
