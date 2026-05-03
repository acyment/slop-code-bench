#!/usr/bin/env python3
"""Validate scenario result JSONL records against the local schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return loaded


def validate_jsonl(path: Path, schema_path: Path) -> list[str]:
    validator = Draft202012Validator(load_json(schema_path))
    errors: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{line_no}: invalid JSON: {exc.msg}")
                continue
            for error in sorted(validator.iter_errors(payload), key=str):
                errors.append(f"{path}:{line_no}: {error.message}")
    return errors


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=repo_root / "experiment" / "schemas" / "scenario_result.schema.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    for path in args.paths:
        errors.extend(validate_jsonl(path.resolve(), args.schema.resolve()))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    for path in args.paths:
        print(f"valid: {path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
