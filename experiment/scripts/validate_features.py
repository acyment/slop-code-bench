#!/usr/bin/env python3
"""Validate parser-neutral Gherkin feature conventions for the pilot."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN_PATTERNS = [
    "BENCHMARK" + " DATA",
    "SENT" + "INEL",
    "slop-code-bench-" + "canary",
]
FEATURE_RE = re.compile(r"^\s*Feature:\s+\S")
SCENARIO_RE = re.compile(r"^\s*Scenario(?: Outline)?:\s+\S")
STEP_RE = re.compile(r"^\s*(Given|When|Then|And|But)\s+\S")
TAG_RE = re.compile(r"^\s*@")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def validate_feature(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    rel = path.as_posix()

    for forbidden in FORBIDDEN_PATTERNS:
        if forbidden in text:
            errors.append(f"{rel}: contains forbidden benchmark marker text")

    if not text.endswith("\n"):
        errors.append(f"{rel}: file must end with a newline")

    feature_count = 0
    scenario_count = 0
    step_count = 0
    saw_problem_tag = False
    saw_checkpoint_tag = False
    in_doc_string = False

    expected_problem = path.parent.name
    expected_checkpoint = path.stem.removeprefix("checkpoint_")

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped == '"""':
            in_doc_string = not in_doc_string
            continue
        if in_doc_string or not stripped or stripped.startswith("#"):
            continue
        if TAG_RE.match(line):
            tags = stripped.split()
            saw_problem_tag = saw_problem_tag or f"@problem_{expected_problem}" in tags
            saw_checkpoint_tag = (
                saw_checkpoint_tag or f"@checkpoint_{expected_checkpoint}" in tags
            )
            continue
        if FEATURE_RE.match(line):
            feature_count += 1
            continue
        if SCENARIO_RE.match(line):
            scenario_count += 1
            continue
        if STEP_RE.match(line):
            step_count += 1
            continue
        if stripped.startswith(("Background:", "Examples:", "|")):
            continue
        errors.append(f"{rel}:{lineno}: unrecognized Gherkin convention line")

    if in_doc_string:
        errors.append(f"{rel}: unterminated doc string")
    if feature_count != 1:
        errors.append(f"{rel}: expected exactly one Feature line")
    if scenario_count < 1:
        errors.append(f"{rel}: expected at least one Scenario")
    if step_count < scenario_count:
        errors.append(f"{rel}: expected at least one step per Scenario")
    if not saw_problem_tag:
        errors.append(f"{rel}: missing @problem_{expected_problem} tag")
    if not saw_checkpoint_tag:
        errors.append(f"{rel}: missing @checkpoint_{expected_checkpoint} tag")

    return errors


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_script()
    default_root = repo_root / "experiment" / "features"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=sorted(default_root.glob("*/*.feature")),
        help="Feature files to validate.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = [path.resolve() for path in args.paths]
    if not paths:
        print("No feature files found.", file=sys.stderr)
        return 1

    errors: list[str] = []
    for path in paths:
        errors.extend(validate_feature(path))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    for path in paths:
        print(f"valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
