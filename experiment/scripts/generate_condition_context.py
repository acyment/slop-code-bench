#!/usr/bin/env python3
"""Render condition-specific implementation prompts for the drift pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment

MARKER_PATTERNS = [
    "BENCHMARK" + " DATA",
    "SENT" + "INEL",
    "slop-code-bench-" + "canary",
]
COMMENT_PREFIX_RE = re.compile(r"^<!-- [\s\S]+?-->\n?")
ENTRY_FILE_RE = re.compile(r"%%%ENTRYPOINT:entry_file%%%")
ENTRY_COMMAND_RE = re.compile(r"%%%ENTRYPOINT:entry_command%%%")


class PromptContextError(ValueError):
    """Raised when a condition prompt cannot be rendered."""


@dataclass(frozen=True)
class RenderedPrompt:
    """Paths and hashes for a rendered condition prompt."""

    prompt_path: Path
    metadata_path: Path
    prompt_hash: str
    metadata: dict[str, Any]


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise PromptContextError(f"Expected YAML mapping at {path}")
    return payload


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_no_marker_text(text: str, source: str) -> None:
    for pattern in MARKER_PATTERNS:
        if pattern in text:
            raise PromptContextError(f"{source} contains benchmark marker text")


def strip_leading_marker_comment(text: str) -> str:
    return COMMENT_PREFIX_RE.sub("", text)


def replace_entry_placeholders(
    text: str, *, entry_file: str, entry_command: str
) -> str:
    text = ENTRY_FILE_RE.sub(entry_file, text)
    return ENTRY_COMMAND_RE.sub(entry_command, text)


def format_entry_file(entry_file: str) -> str:
    if Path(entry_file).suffix:
        return entry_file
    return f"{entry_file}.py"


def agent_entry_command(entry_file: str) -> str:
    return f"python {format_entry_file(entry_file)}"


def ordered_checkpoints(problem_config: dict[str, Any]) -> list[str]:
    checkpoints = problem_config.get("checkpoints")
    if not isinstance(checkpoints, dict) or not checkpoints:
        raise PromptContextError("Problem config has no checkpoints mapping")
    return sorted(
        checkpoints,
        key=lambda checkpoint_id: int(
            checkpoints[checkpoint_id].get("order", 10_000)
        ),
    )


def normalize_checkpoint_ref(
    checkpoint_ref: str, problem_config: dict[str, Any]
) -> tuple[str, int]:
    checkpoints = ordered_checkpoints(problem_config)
    checkpoint_map = {checkpoint_id: checkpoint_id for checkpoint_id in checkpoints}
    checkpoint_map.update(
        {
            f"checkpoint_{index:03d}": checkpoint_id
            for index, checkpoint_id in enumerate(checkpoints, start=1)
        }
    )
    checkpoint_map.update(
        {
            str(index): checkpoint_id
            for index, checkpoint_id in enumerate(checkpoints, start=1)
        }
    )

    checkpoint_id = checkpoint_map.get(checkpoint_ref)
    if checkpoint_id is None:
        valid = ", ".join(sorted(checkpoint_map))
        msg = f"Unknown checkpoint {checkpoint_ref!r}; valid values: {valid}"
        raise PromptContextError(msg)
    return checkpoint_id, checkpoints.index(checkpoint_id) + 1


def checkpoint_ids_through(
    problem_config: dict[str, Any], checkpoint_index: int
) -> list[tuple[str, int]]:
    return [
        (checkpoint_id, index)
        for index, checkpoint_id in enumerate(
            ordered_checkpoints(problem_config), start=1
        )
        if index <= checkpoint_index
    ]


def read_checkpoint_spec(
    problems_root: Path,
    problem_id: str,
    checkpoint_id: str,
    *,
    entry_file: str,
    entry_command: str,
) -> str:
    spec_path = problems_root / problem_id / f"{checkpoint_id}.md"
    if not spec_path.is_file():
        raise PromptContextError(f"Missing checkpoint spec: {spec_path}")
    spec_text = spec_path.read_text(encoding="utf-8")
    spec_text = strip_leading_marker_comment(spec_text)
    spec_text = replace_entry_placeholders(
        spec_text,
        entry_file=entry_file,
        entry_command=entry_command,
    )
    ensure_no_marker_text(spec_text, spec_path.as_posix())
    return spec_text.strip()


def read_gherkin_context(
    repo_root: Path,
    problem_id: str,
    problem_config: dict[str, Any],
    checkpoint_index: int,
) -> tuple[str, list[str]]:
    sections: list[str] = []
    feature_paths: list[str] = []
    for _checkpoint_id, index in checkpoint_ids_through(
        problem_config, checkpoint_index
    ):
        feature_rel = (
            Path("experiment")
            / "features"
            / problem_id
            / f"checkpoint_{index:03d}.feature"
        )
        feature_path = repo_root / feature_rel
        if not feature_path.is_file():
            raise PromptContextError(f"Missing feature file: {feature_path}")
        feature_text = feature_path.read_text(encoding="utf-8")
        ensure_no_marker_text(feature_text, feature_path.as_posix())
        feature_paths.append(feature_rel.as_posix())
        sections.append(
            "\n".join(
                [
                    f"## {feature_rel.as_posix()}",
                    "",
                    "```gherkin",
                    feature_text.rstrip(),
                    "```",
                ]
            )
        )
    return "\n\n".join(sections), feature_paths


def list_lines(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def allowed_paths_text() -> str:
    return list_lines(
        [
            "product implementation files in the agent workspace",
            "dependency files required by the product implementation",
            "local scratch artifacts created by product-level test commands",
        ]
    )


def forbidden_paths_text(locked_paths: list[str]) -> str:
    base_paths = [
        "native benchmark test files",
        "hidden evaluation files or generated evaluation workspaces",
        "experiment result schemas and scoring/export scripts",
    ]
    return list_lines(base_paths + locked_paths)


def protected_manifest_text(locked_paths: list[str]) -> str:
    if not locked_paths:
        return "- no experiment lock paths configured for this condition"
    return list_lines(locked_paths)


def acceptance_command_text(
    *, condition_id: str, problem_id: str, checkpoint_id: str
) -> str:
    if condition_id != "C2":
        return "No visible acceptance command is provided for this condition."
    run_id = f"{condition_id.lower()}-{problem_id}-{checkpoint_id}"
    return (
        "python .scbench_acceptance/runner.py "
        "--workspace . "
        f"--problem-id {problem_id} "
        f"--checkpoint-id {checkpoint_id} "
        "--through-checkpoint "
        f"--output-dir .scbench_acceptance/results/{run_id} "
        f"--run-id {run_id}"
    )


def render_template(template_text: str, context: dict[str, Any]) -> str:
    env = Environment(
        autoescape=False,  # noqa: S701
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    rendered = env.from_string(template_text).render(**context).strip()
    return f"{rendered}\n"


def condition_exposes_gherkin(condition: dict[str, Any]) -> bool:
    return bool(condition.get("gherkin_context_visible", False))


def condition_exposes_acceptance(condition: dict[str, Any]) -> bool:
    return bool(condition.get("acceptance_harness_runnable", False))


def render_condition_context(
    *,
    config_path: Path,
    problem_id: str,
    checkpoint_ref: str,
    problems_root: Path,
    output_dir: Path,
) -> RenderedPrompt:
    repo_root = repo_root_from_script()
    matrix_config = load_yaml(config_path)
    condition = matrix_config.get("condition")
    if not isinstance(condition, dict):
        raise PromptContextError("Run matrix missing condition mapping")
    condition_id = str(condition["id"])
    prompt_template_path = repo_root / str(condition["prompt_template"])
    if not prompt_template_path.is_file():
        raise PromptContextError(f"Missing prompt template: {prompt_template_path}")

    problem_config_path = problems_root / problem_id / "config.yaml"
    problem_config = load_yaml(problem_config_path)
    checkpoint_id, checkpoint_index = normalize_checkpoint_ref(
        checkpoint_ref, problem_config
    )
    entry_file = format_entry_file(str(problem_config["entry_file"]))
    entry_command = agent_entry_command(str(problem_config["entry_file"]))
    original_spec = read_checkpoint_spec(
        problems_root,
        problem_id,
        checkpoint_id,
        entry_file=entry_file,
        entry_command=entry_command,
    )

    feature_paths: list[str] = []
    gherkin_context = ""
    if condition_exposes_gherkin(condition):
        gherkin_context, feature_paths = read_gherkin_context(
            repo_root, problem_id, problem_config, checkpoint_index
        )

    lock_policy = matrix_config.get("lock_policy", {})
    locked_paths = list(lock_policy.get("locked_paths", []))
    acceptance_command = acceptance_command_text(
        condition_id=condition_id,
        problem_id=problem_id,
        checkpoint_id=checkpoint_id,
    )
    if not condition_exposes_acceptance(condition):
        acceptance_command = ""

    context: dict[str, Any] = {
        "problem_id": problem_id,
        "checkpoint_id": checkpoint_id,
        "checkpoint_index": checkpoint_index,
        "condition_id": condition_id,
        "is_continuation": checkpoint_index > 1,
        "entry_command": entry_command,
        "original_checkpoint_spec": original_spec,
        "gherkin_context": gherkin_context,
        "acceptance_command": acceptance_command,
        "hidden_eval_command": (
            "Native SCBench scoring is run externally after the agent turn."
        ),
        "allowed_paths": allowed_paths_text(),
        "forbidden_paths": forbidden_paths_text(locked_paths),
        "protected_file_manifest": protected_manifest_text(locked_paths),
    }

    template_text = prompt_template_path.read_text(encoding="utf-8")
    ensure_no_marker_text(template_text, prompt_template_path.as_posix())
    rendered_prompt = render_template(template_text, context)
    ensure_no_marker_text(rendered_prompt, "rendered prompt")

    condition_dir = output_dir / condition_id.lower() / problem_id
    condition_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = condition_dir / f"{checkpoint_id}.md"
    metadata_path = condition_dir / f"{checkpoint_id}.metadata.json"
    prompt_path.write_text(rendered_prompt, encoding="utf-8")

    prompt_hash = sha256_text(rendered_prompt)
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "matrix_id": matrix_config["matrix_id"],
        "condition_id": condition_id,
        "problem_id": problem_id,
        "checkpoint_id": checkpoint_id,
        "checkpoint_index": checkpoint_index,
        "prompt_template": str(condition["prompt_template"]),
        "prompt_template_id": prompt_template_path.stem,
        "prompt_hash": prompt_hash,
        "original_spec_hash": sha256_text(original_spec),
        "gherkin_context_hash": sha256_text(gherkin_context),
        "acceptance_command_hash": sha256_text(acceptance_command),
        "includes_gherkin_context": bool(gherkin_context),
        "includes_acceptance_command": bool(acceptance_command),
        "locked_paths": locked_paths,
        "source_paths": {
            "run_matrix": config_path.as_posix(),
            "problem_config": problem_config_path.as_posix(),
            "checkpoint_spec": (
                problems_root / problem_id / f"{checkpoint_id}.md"
            ).as_posix(),
            "features": feature_paths,
        },
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return RenderedPrompt(
        prompt_path=prompt_path,
        metadata_path=metadata_path,
        prompt_hash=prompt_hash,
        metadata=metadata,
    )


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Experiment run-matrix YAML path.",
    )
    parser.add_argument(
        "--problem",
        required=True,
        help="Problem id to render.",
    )
    parser.add_argument(
        "--checkpoint",
        required=True,
        help="Checkpoint id, three-digit id, or index.",
    )
    parser.add_argument(
        "--problems-root",
        type=Path,
        default=repo_root.parent / "scb-problems",
        help="Path to the pinned scb-problems checkout.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "experiment" / "runs" / "rendered_prompts",
        help="Directory for rendered prompt artifacts.",
    )
    parser.add_argument(
        "--print-metadata",
        action="store_true",
        help="Print metadata JSON instead of a short path/hash summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rendered = render_condition_context(
        config_path=args.config.resolve(),
        problem_id=args.problem,
        checkpoint_ref=args.checkpoint,
        problems_root=args.problems_root.resolve(),
        output_dir=args.output_dir.resolve(),
    )
    if args.print_metadata:
        print(json.dumps(rendered.metadata, indent=2, sort_keys=True))
        return 0

    print(f"prompt: {rendered.prompt_path}")
    print(f"metadata: {rendered.metadata_path}")
    print(f"prompt_hash: {rendered.prompt_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
