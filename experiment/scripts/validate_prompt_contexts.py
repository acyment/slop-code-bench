#!/usr/bin/env python3
"""Validate condition prompt rendering and intervention separation."""

from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import gettempdir

import generate_condition_context as generator

MARKER_PATTERNS = [
    "BENCHMARK" + " DATA",
    "SENT" + "INEL",
    "slop-code-bench-" + "canary",
]


class PromptValidationError(ValueError):
    """Raised when rendered prompts violate condition boundaries."""


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise PromptValidationError(f"{label} must contain {needle!r}")


def require_absent(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise PromptValidationError(f"{label} must not contain {needle!r}")


def require_marker_free(text: str, label: str) -> None:
    for marker in MARKER_PATTERNS:
        if marker in text:
            raise PromptValidationError(f"{label} contains benchmark marker text")


def render_twice(
    *,
    config_path: Path,
    problem_id: str,
    checkpoint_ref: str,
    problems_root: Path,
    output_dir: Path,
) -> tuple[generator.RenderedPrompt, str]:
    first = generator.render_condition_context(
        config_path=config_path,
        problem_id=problem_id,
        checkpoint_ref=checkpoint_ref,
        problems_root=problems_root,
        output_dir=output_dir / "first",
    )
    second = generator.render_condition_context(
        config_path=config_path,
        problem_id=problem_id,
        checkpoint_ref=checkpoint_ref,
        problems_root=problems_root,
        output_dir=output_dir / "second",
    )
    if first.prompt_hash != second.prompt_hash:
        raise PromptValidationError(
            f"{config_path.name} rendered unstable prompt hashes"
        )
    first_text = read_text(first.prompt_path)
    second_text = read_text(second.prompt_path)
    if first_text != second_text:
        raise PromptValidationError(f"{config_path.name} rendered unstable text")
    require_marker_free(first_text, config_path.name)
    require_marker_free(read_text(first.metadata_path), f"{config_path.name} metadata")
    return first, first_text


def validate_c0_prompt(text: str, metadata: dict) -> None:
    require_contains(text, "Implement a program", "C0 prompt")
    require_absent(text, "Gherkin", "C0 prompt")
    require_absent(text, "```gherkin", "C0 prompt")
    require_absent(text, "@problem_", "C0 prompt")
    require_absent(text, "run_acceptance_smoke.py", "C0 prompt")
    if metadata["includes_gherkin_context"]:
        raise PromptValidationError("C0 metadata must not include feature context")
    if metadata["includes_acceptance_command"]:
        raise PromptValidationError("C0 metadata must not include acceptance command")


def validate_c1_prompt(text: str, metadata: dict) -> None:
    require_contains(text, "Feature:", "C1 prompt")
    require_contains(text, "@problem_code_search", "C1 prompt")
    require_absent(text, "run_acceptance_smoke.py", "C1 prompt")
    if not metadata["includes_gherkin_context"]:
        raise PromptValidationError("C1 metadata must include feature context")
    if metadata["includes_acceptance_command"]:
        raise PromptValidationError("C1 metadata must not include acceptance command")


def validate_c2_prompt(text: str, metadata: dict) -> None:
    require_contains(text, "Feature:", "C2 prompt")
    require_contains(text, "@problem_code_search", "C2 prompt")
    require_contains(text, "run_acceptance_smoke.py", "C2 prompt")
    require_contains(text, "experiment/features/**", "C2 prompt")
    if not metadata["includes_gherkin_context"]:
        raise PromptValidationError("C2 metadata must include feature context")
    if not metadata["includes_acceptance_command"]:
        raise PromptValidationError("C2 metadata must include acceptance command")


def validate_prompt_contexts(problems_root: Path, output_dir: Path) -> None:
    repo_root = repo_root_from_script()
    cases = [
        (
            repo_root / "experiment" / "configs" / "mvp_c0.yaml",
            "C0",
            validate_c0_prompt,
        ),
        (
            repo_root / "experiment" / "configs" / "pilot_c1.yaml",
            "C1",
            validate_c1_prompt,
        ),
        (
            repo_root / "experiment" / "configs" / "mvp_c2.yaml",
            "C2",
            validate_c2_prompt,
        ),
    ]

    for config_path, label, validator in cases:
        rendered, text = render_twice(
            config_path=config_path,
            problem_id="code_search",
            checkpoint_ref="checkpoint_1",
            problems_root=problems_root,
            output_dir=output_dir / label.lower(),
        )
        validator(text, rendered.metadata)
        print(
            f"valid: {label} {rendered.metadata['problem_id']} "
            f"{rendered.metadata['checkpoint_id']} {rendered.prompt_hash}"
        )


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--problems-root",
        type=Path,
        default=repo_root.parent / "scb-problems",
        help="Path to the pinned scb-problems checkout.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(gettempdir()) / "scbench-prompt-contexts",
        help="Directory for temporary rendered prompts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_prompt_contexts(
        problems_root=args.problems_root.resolve(),
        output_dir=args.output_dir.resolve(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
