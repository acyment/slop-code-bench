#!/usr/bin/env python3
"""Validate lock-manifest behavior without touching real experiment files."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import verify_locks


class LockValidationError(ValueError):
    """Raised when lock-manifest validation fails."""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def assert_status(result: dict, expected: str, label: str) -> None:
    if result["status"] != expected:
        raise LockValidationError(
            f"{label} expected {expected}, got {result['status']}"
        )


def validate_modified_feature_detection() -> None:
    with TemporaryDirectory(prefix="scbench-lock-validation-") as tmp:
        root = Path(tmp)
        feature_path = root / "experiment" / "features" / "demo" / "checkpoint_001.feature"
        write_text(feature_path, "@problem_demo @checkpoint_001\nFeature: Demo\n")
        write_text(root / "experiment" / "steps" / "demo" / "steps.py", "# steps\n")
        write_text(root / "experiment" / "prompts" / "baseline.md", "Prompt\n")
        write_text(root / "experiment" / "scripts" / "runner.py", "print('ok')\n")
        write_text(root / "experiment" / "schemas" / "schema.json", "{}\n")

        locked_paths = [
            "experiment/features/**",
            "experiment/steps/**",
            "experiment/prompts/**",
            "experiment/scripts/**",
            "experiment/schemas/**",
        ]
        manifest = verify_locks.build_manifest(
            root=root,
            locked_paths=locked_paths,
        )
        unchanged = verify_locks.verify_manifest(
            baseline_manifest=manifest,
            root=root,
        )
        assert_status(unchanged, "unchanged", "unchanged manifest")

        write_text(
            feature_path,
            "@problem_demo @checkpoint_001\nFeature: Demo changed\n",
        )
        changed = verify_locks.verify_manifest(
            baseline_manifest=manifest,
            root=root,
        )
        assert_status(changed, "changed", "modified feature manifest")
        changed_paths = {item["path"] for item in changed["changed_files"]}
        expected_path = "experiment/features/demo/checkpoint_001.feature"
        if expected_path not in changed_paths:
            raise LockValidationError(
                "modified feature file was not reported as changed"
            )
        if not changed["protocol_violation"]:
            raise LockValidationError("changed manifest must be a protocol violation")

    print("valid: modified feature file marks lock manifest changed")


def main() -> int:
    validate_modified_feature_detection()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
