#!/usr/bin/env python3
"""Orchestrate one experiment trajectory, starting with dry-run integration."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import export_results
import generate_condition_context as prompt_context
import verify_locks
import yaml
from git import Repo


class TrajectoryError(ValueError):
    """Raised when a trajectory cannot be prepared or run."""


@dataclass(frozen=True)
class TrajectoryResult:
    """Summary for a prepared trajectory run."""

    run_id: str
    artifact_root: Path
    run_record: dict[str, Any]
    checkpoint_records: list[dict[str, Any]]


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def timestamp_id() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def rel_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TrajectoryError(f"Expected object JSON in {path}")
    return payload


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def current_git_commit(root: Path) -> str:
    try:
        return Repo(root).head.commit.hexsha
    except Exception:  # noqa: BLE001
        return "unknown"


def load_run_matrix(config_path: Path) -> dict[str, Any]:
    return prompt_context.load_yaml(config_path)


def find_replicate(matrix_config: dict[str, Any], replicate_id: int) -> dict[str, Any]:
    for replicate in matrix_config["replicates"]:
        if int(replicate["replicate_id"]) == replicate_id:
            return replicate
    raise TrajectoryError(f"replicate_id {replicate_id} is not in run matrix")


def validate_problem(matrix_config: dict[str, Any], problem_id: str) -> None:
    if problem_id not in matrix_config["problems"]:
        matrix_id = matrix_config["matrix_id"]
        raise TrajectoryError(f"{problem_id} is not listed in {matrix_id}")


def default_run_id(
    *, matrix_id: str, condition_id: str, problem_id: str, replicate_id: int
) -> str:
    return (
        f"{timestamp_id()}-{matrix_id}-{condition_id.lower()}-"
        f"{problem_id}-r{replicate_id:02d}"
    )


def trajectory_root(
    *,
    repo_root: Path,
    matrix_config: dict[str, Any],
    problem_id: str,
    replicate_id: int,
    run_id: str,
    run_root_override: Path | None,
) -> Path:
    if run_root_override is not None:
        base = run_root_override
    else:
        base = repo_root / matrix_config["outputs"]["run_root"]
    return base / problem_id / f"replicate_{replicate_id:02d}" / run_id


def ordered_checkpoints(
    *, problems_root: Path, problem_id: str
) -> tuple[dict[str, Any], list[str]]:
    problem_config = prompt_context.load_yaml(
        problems_root / problem_id / "config.yaml"
    )
    return problem_config, prompt_context.ordered_checkpoints(problem_config)


def checkpoint_limit_slice(checkpoints: list[str], checkpoint_limit: int | None) -> list[str]:
    if checkpoint_limit is None:
        return checkpoints
    if checkpoint_limit <= 0:
        raise TrajectoryError("--checkpoint-limit must be greater than zero")
    return checkpoints[:checkpoint_limit]


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def stage_acceptance_asset(
    *,
    problem_dir: Path,
) -> None:
    asset_root = problem_dir / "experiment_acceptance"
    asset_root.mkdir(parents=True, exist_ok=True)
    (asset_root / "runner.py").write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                '"""Checkpoint-scoped SpecCommons acceptance runner entrypoint."""',
                "",
                "from __future__ import annotations",
                "",
                "import runpy",
                "import sys",
                "from pathlib import Path",
                "",
                'CURRENT_RUNNER = Path(__file__).with_name("runner_current.py")',
                "if not CURRENT_RUNNER.is_file():",
                "    raise SystemExit(",
                '        "checkpoint-scoped acceptance runner has not been prepared"',
                "    )",
                "sys.argv[0] = str(CURRENT_RUNNER)",
                'runpy.run_path(str(CURRENT_RUNNER), run_name="__main__")',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (asset_root / "README.md").write_text(
        "\n".join(
            [
                "# SpecCommons C2 Acceptance Harness",
                "",
                "This workspace asset intentionally contains a checkpoint-scoped runner entrypoint only.",
                "Checkpoint feature text is rendered into the prompt as current/prior context.",
                "The native experiment runner writes `.scbench_acceptance/runner_current.py` before each checkpoint.",
                "Future checkpoint `.feature` files and future scenario code are not staged here to avoid leakage.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def prepare_native_problem_fixture(
    *,
    source_problems_root: Path,
    artifact_root: Path,
    matrix_config: dict[str, Any],
    config_path: Path,
    problem_id: str,
    checkpoint_ids: list[str],
) -> Path:
    native_problem_root = artifact_root / "native_problem_root"
    problem_dir = native_problem_root / problem_id
    if problem_dir.exists():
        shutil.rmtree(problem_dir)
    shutil.copytree(source_problems_root / problem_id, problem_dir)

    config_payload = prompt_context.load_yaml(problem_dir / "config.yaml")
    checkpoints_payload = config_payload.get("checkpoints")
    if not isinstance(checkpoints_payload, dict):
        raise TrajectoryError(f"{problem_id} config has no checkpoints mapping")
    config_payload["checkpoints"] = {
        checkpoint_id: checkpoints_payload[checkpoint_id]
        for checkpoint_id in checkpoint_ids
    }

    if matrix_config["condition"]["id"] == "C2":
        stage_acceptance_asset(
            problem_dir=problem_dir,
        )
        static_assets = dict(config_payload.get("static_assets") or {})
        static_assets["speccommons_acceptance"] = {
            "path": "experiment_acceptance",
            "save_path": ".scbench_acceptance",
        }
        config_payload["static_assets"] = static_assets

    write_yaml(problem_dir / "config.yaml", config_payload)

    prompt_output_dir = artifact_root / "condition_prompts"
    for checkpoint_id in checkpoint_ids:
        rendered = prompt_context.render_condition_context(
            config_path=config_path,
            problem_id=problem_id,
            checkpoint_ref=checkpoint_id,
            problems_root=source_problems_root,
            output_dir=prompt_output_dir,
        )
        shutil.copy2(rendered.prompt_path, problem_dir / f"{checkpoint_id}.md")

    return native_problem_root


def write_passthrough_prompt_template(artifact_root: Path) -> Path:
    path = artifact_root / "native_passthrough_prompt.jinja"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{{ spec.strip() }}\n", encoding="utf-8")
    return path


def native_model_string(matrix_config: dict[str, Any]) -> str:
    model = matrix_config["model"]
    return f"{model['provider']}/{model['name']}"


def write_native_agent_config(
    *, repo_root: Path, artifact_root: Path, matrix_config: dict[str, Any]
) -> Path:
    base_config = prompt_context.load_yaml(
        repo_root / "configs" / "agents" / f"{matrix_config['agent_harness']['id']}.yaml"
    )
    base_config["version"] = matrix_config["agent_harness"]["version"]
    config_path = artifact_root / "native_agent_config.yaml"
    write_yaml(config_path, base_config)
    return config_path


def write_native_run_config(
    *,
    repo_root: Path,
    artifact_root: Path,
    matrix_config: dict[str, Any],
    problem_id: str,
    prompt_template_path: Path,
) -> Path:
    runner = matrix_config.get("runner", {})
    agent_config_path = write_native_agent_config(
        repo_root=repo_root,
        artifact_root=artifact_root,
        matrix_config=matrix_config,
    )
    config = {
        "agent": agent_config_path.as_posix(),
        "environment": runner.get("native_environment", "docker-python3.12-uv"),
        "prompt": prompt_template_path.as_posix(),
        "model": {
            "provider": matrix_config["model"]["provider"],
            "name": matrix_config["model"]["name"],
        },
        "thinking": runner.get("thinking", "low"),
        "pass_policy": runner.get("pass_policy", "core-cases"),
        "problems": [problem_id],
        "save_dir": (artifact_root / "native").as_posix(),
        "save_template": "run",
    }
    config_path = artifact_root / "native_run_config.yaml"
    write_yaml(config_path, config)
    return config_path


def native_run_dir(artifact_root: Path) -> Path:
    return artifact_root / "native" / "run"


def run_native_scbench(
    *,
    artifact_root: Path,
    native_problem_root: Path,
    native_config_path: Path,
    problem_id: str,
    mode: str,
    seed: int,
    num_workers: int,
    acceptance_feedback_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    command = [
        "uv",
        "run",
        "slop-code",
        "--overwrite",
        "--quiet",
        "--seed",
        str(seed),
        "run",
        "--config",
        native_config_path.as_posix(),
        "--problem",
        problem_id,
        "--num-workers",
        str(num_workers),
        "--no-live-progress",
    ]
    if mode == "native-dry-run":
        command.append("--dry-run")
    env = os.environ.copy()
    env["SCBENCH_PROBLEMS_PATH"] = native_problem_root.as_posix()
    env.setdefault("UV_CACHE_DIR", (artifact_root / ".uv-cache").as_posix())
    if (
        acceptance_feedback_policy
        and acceptance_feedback_policy.get("enforcement") == "harness_mediated"
    ):
        env["SPECCOMMONS_ACCEPTANCE_GATE"] = "1"
        env["SPECCOMMONS_ACCEPTANCE_SOURCE"] = (
            repo_root_from_script()
            / "experiment"
            / "steps"
            / "acceptance"
            / "standalone_runner.py"
        ).as_posix()
        env["SPECCOMMONS_ACCEPTANCE_GATE_MAX_REPAIRS"] = str(
            int(acceptance_feedback_policy.get("max_repair_attempts", 1))
        )
        env["SPECCOMMONS_ACCEPTANCE_GATE_TIMEOUT_SECONDS"] = str(
            int(acceptance_feedback_policy.get("timeout_seconds", 300))
        )

    started_at = utc_now()
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=repo_root_from_script(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    ended_at = utc_now()
    command_record = {
        "schema_version": 1,
        "command": command,
        "mode": mode,
        "started_at": started_at,
        "ended_at": ended_at,
        "exit_code": completed.returncode,
        "stdout_path": (artifact_root / "native_command.stdout").as_posix(),
        "stderr_path": (artifact_root / "native_command.stderr").as_posix(),
        "native_problem_root": native_problem_root.as_posix(),
        "native_config_path": native_config_path.as_posix(),
        "native_run_dir": native_run_dir(artifact_root).as_posix(),
    }
    write_json(artifact_root / "native_command.json", command_record)
    (artifact_root / "native_command.stdout").write_text(
        completed.stdout,
        encoding="utf-8",
    )
    (artifact_root / "native_command.stderr").write_text(
        completed.stderr,
        encoding="utf-8",
    )
    return command_record


def export_native_run(
    *,
    artifact_root: Path,
    matrix_config: dict[str, Any],
    run_id: str,
    problem_id: str,
    replicate_id: int,
    repo_root: Path,
    experiment_commit: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    export_dir = artifact_root / "normalized"
    summary = export_results.export_runs(
        input_runs=[native_run_dir(artifact_root)],
        output_dir=export_dir,
        repo_root=repo_root,
        overrides={
            "run_id": run_id,
            "condition_id": matrix_config["condition"]["id"],
            "problem_id": problem_id,
            "replicate_id": replicate_id,
            "model": native_model_string(matrix_config),
            "agent_harness": matrix_config["agent_harness"]["id"],
            "agent_version": matrix_config["agent_harness"]["version"],
            "benchmark_commit": matrix_config["runner"]["benchmark_commit"],
            "problems_commit": matrix_config["runner"]["problem_commit"],
        },
    )
    run_rows = export_results.read_jsonl(export_dir / "runs.jsonl")
    checkpoint_rows = export_results.read_jsonl(export_dir / "checkpoints.jsonl")
    if not run_rows:
        raise TrajectoryError(f"native export produced no run rows: {summary}")
    run_record = run_rows[0]
    run_record["experiment_commit"] = experiment_commit
    return run_record, checkpoint_rows


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                payload = json.loads(stripped)
                if isinstance(payload, dict):
                    rows.append(payload)
    return rows


def visible_acceptance_passed(rows: list[dict[str, Any]]) -> bool | None:
    runnable = [row for row in rows if row.get("status") != "skipped"]
    if not runnable:
        return None
    return all(row.get("status") == "passed" for row in runnable)


def sum_duration_ms(rows: list[dict[str, Any]]) -> float | None:
    durations = [
        float(row["duration_ms"])
        for row in rows
        if isinstance(row.get("duration_ms"), int | float)
    ]
    if not durations:
        return None
    return sum(durations)


def merge_visible_acceptance_results(
    *,
    repo_root: Path,
    artifact_root: Path,
    run_id: str,
    problem_id: str,
    checkpoint_rows: list[dict[str, Any]],
) -> None:
    runner_path = repo_root / "experiment/steps/acceptance/standalone_runner.py"
    for row in checkpoint_rows:
        checkpoint_id = str(row["checkpoint_id"])
        checkpoint_dir_rel = row.get("artifact_paths", {}).get("checkpoint_dir")
        if not checkpoint_dir_rel:
            continue
        checkpoint_dir = repo_root / checkpoint_dir_rel
        snapshot_dir = checkpoint_dir / "snapshot"
        output_dir = artifact_root / "visible_acceptance" / checkpoint_id
        gate_summary_path = checkpoint_dir / "acceptance_gate" / "summary.json"
        if gate_summary_path.is_file():
            gate_summary = read_json(gate_summary_path)
            row["acceptance_feedback_observed"] = bool(
                gate_summary.get("feedback_observed")
                or gate_summary.get("attempt_count", 0) > 0
            )
            row["visible_acceptance_executed_by_agent"] = False
            row["visible_acceptance_execution_count"] = gate_summary.get(
                "attempt_count"
            )
            row["visible_acceptance_gate_passed"] = gate_summary.get("passed")
            row["visible_acceptance_gate_mode"] = gate_summary.get("mode")
            row["c2_feedback_status"] = (
                "observed" if row["acceptance_feedback_observed"] else "not_observed"
            )
        else:
            row["c2_feedback_status"] = "unknown"
        command = [
            sys.executable,
            runner_path.as_posix(),
            "--workspace",
            snapshot_dir.as_posix(),
            "--problem-id",
            problem_id,
            "--checkpoint-id",
            checkpoint_id,
            "--through-checkpoint",
            "--output-dir",
            output_dir.as_posix(),
            "--run-id",
            run_id,
        ]
        completed = subprocess.run(  # noqa: S603
            command,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        write_json(
            output_dir / "command.json",
            {
                "schema_version": 1,
                "command": command,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )
        scenario_rows = read_jsonl(output_dir / "scenarios.jsonl")
        passed = visible_acceptance_passed(scenario_rows)
        row["visible_acceptance_passed"] = passed
        row["scenario_results"] = scenario_rows
        row["hidden_failure_after_visible_pass"] = (
            passed is True and row.get("hidden_tests_passed") is False
        )
        technical = dict(row.get("technical_metrics") or {})
        technical["acceptance_runtime_ms"] = sum_duration_ms(scenario_rows)
        row["technical_metrics"] = technical
        artifact_paths = dict(row.get("artifact_paths") or {})
        artifact_paths["visible_acceptance"] = rel_path(output_dir, repo_root)
        if gate_summary_path.is_file():
            artifact_paths["acceptance_gate"] = rel_path(
                gate_summary_path.parent,
                repo_root,
            )
        row["artifact_paths"] = artifact_paths


def lock_before_checkpoint(
    *,
    repo_root: Path,
    lock_policy: dict[str, Any],
    checkpoint_dir: Path,
) -> dict[str, Any] | None:
    if lock_policy["mode"] == "none":
        return None
    locked_paths = [str(path) for path in lock_policy["locked_paths"]]
    manifest = verify_locks.build_manifest(
        root=repo_root,
        locked_paths=locked_paths,
    )
    write_json(checkpoint_dir / "locks" / "before.json", manifest)
    return manifest


def lock_after_checkpoint(
    *,
    repo_root: Path,
    before_manifest: dict[str, Any] | None,
    checkpoint_dir: Path,
) -> dict[str, Any]:
    if before_manifest is None:
        result = {
            "schema_version": 1,
            "checked_at": utc_now(),
            "status": "not_applicable",
            "protocol_violation": False,
            "manifest_hash": None,
            "current_manifest_hash": None,
            "file_count_before": 0,
            "file_count_after": 0,
            "added_files": [],
            "removed_files": [],
            "changed_files": [],
            "missing_patterns_before": [],
            "missing_patterns_after": [],
        }
    else:
        result = verify_locks.verify_manifest(
            baseline_manifest=before_manifest,
            root=repo_root,
        )
    write_json(checkpoint_dir / "locks" / "after.json", result)
    return result


def planned_commands(
    *,
    condition_id: str,
    problem_id: str,
    checkpoint_id: str,
    config_path: Path,
    problems_root: Path,
    prompt_output_dir: Path,
) -> dict[str, str | None]:
    command = prompt_context.acceptance_command_text(
        condition_id=condition_id,
        problem_id=problem_id,
        checkpoint_id=checkpoint_id,
    )
    acceptance = command if condition_id == "C2" else None
    return {
        "render_prompt": (
            "uv run python experiment/scripts/generate_condition_context.py "
            f"--config {config_path.as_posix()} "
            f"--problem {problem_id} "
            f"--checkpoint {checkpoint_id} "
            f"--problems-root {problems_root.as_posix()} "
            f"--output-dir {prompt_output_dir.as_posix()}"
        ),
        "visible_acceptance": acceptance,
        "native_scbench_agent": "not executed in dry-run mode",
        "native_scbench_hidden_eval": "not executed in dry-run mode",
    }


def checkpoint_record(
    *,
    matrix_config: dict[str, Any],
    run_id: str,
    problem_id: str,
    checkpoint_id: str,
    checkpoint_index: int,
    replicate_id: int,
    replicate_seed: int,
    experiment_commit: str,
    prompt_metadata: dict[str, Any],
    lock_result: dict[str, Any],
    checkpoint_dir: Path,
    repo_root: Path,
    started_at: str,
    ended_at: str,
) -> dict[str, Any]:
    condition_id = matrix_config["condition"]["id"]
    status = (
        "invalid_lock_violation"
        if lock_result["protocol_violation"]
        else "dry_run_prepared"
    )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "condition_id": condition_id,
        "problem_id": problem_id,
        "checkpoint_id": checkpoint_id,
        "checkpoint_index": checkpoint_index,
        "replicate_id": replicate_id,
        "replicate_seed": replicate_seed,
        "model": matrix_config["model"]["name"],
        "agent_harness": matrix_config["agent_harness"]["id"],
        "agent_version": matrix_config["agent_harness"]["version"],
        "benchmark_commit": matrix_config["runner"]["benchmark_commit"],
        "problems_commit": matrix_config["runner"]["problem_commit"],
        "experiment_commit": experiment_commit,
        "started_at": started_at,
        "ended_at": ended_at,
        "status": status,
        "prompt_template_id": prompt_metadata["prompt_template_id"],
        "prompt_hash": prompt_metadata["prompt_hash"],
        "context_hash": prompt_metadata["original_spec_hash"],
        "feature_hash": prompt_metadata["gherkin_context_hash"],
        "lock_manifest_hash": lock_result["manifest_hash"],
        "lock_status": lock_result["status"],
        "protocol_violation": lock_result["protocol_violation"],
        "visible_acceptance_passed": None,
        "hidden_tests_passed": None,
        "current_checkpoint_passed": None,
        "prior_regression_count": None,
        "hidden_failure_after_visible_pass": None,
        "scenario_results": [],
        "hidden_test_summary": {},
        "technical_metrics": {},
        "cost_metrics": {},
        "artifact_paths": {
            "checkpoint_dir": rel_path(checkpoint_dir, repo_root),
            "prompt": rel_path(Path(prompt_metadata["prompt_path"]), repo_root)
            if "prompt_path" in prompt_metadata
            else None,
            "prompt_metadata": rel_path(
                Path(prompt_metadata["metadata_path"]), repo_root
            )
            if "metadata_path" in prompt_metadata
            else None,
            "lock_before": rel_path(checkpoint_dir / "locks" / "before.json", repo_root),
            "lock_after": rel_path(checkpoint_dir / "locks" / "after.json", repo_root),
        },
    }


def write_planned_commands(path: Path, commands: dict[str, str | None]) -> None:
    lines = ["# Planned Commands", ""]
    for name, command in commands.items():
        lines.append(f"## {name}")
        lines.append("")
        if command is None:
            lines.append("not applicable")
        else:
            lines.extend(["```bash", command, "```"])
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_trajectory(
    *,
    config_path: Path,
    problem_id: str,
    replicate_id: int,
    problems_root: Path,
    mode: str,
    run_id: str | None = None,
    run_root_override: Path | None = None,
    checkpoint_limit: int | None = None,
) -> TrajectoryResult:
    if mode not in {"dry-run", "native-dry-run", "native-run"}:
        raise TrajectoryError(f"unsupported mode: {mode}")

    repo_root = repo_root_from_script()
    matrix_config = load_run_matrix(config_path)
    condition_id = matrix_config["condition"]["id"]
    matrix_id = matrix_config["matrix_id"]
    validate_problem(matrix_config, problem_id)
    replicate = find_replicate(matrix_config, replicate_id)
    problem_config, checkpoints = ordered_checkpoints(
        problems_root=problems_root,
        problem_id=problem_id,
    )
    selected_checkpoints = checkpoint_limit_slice(checkpoints, checkpoint_limit)
    current_run_id = run_id or default_run_id(
        matrix_id=matrix_id,
        condition_id=condition_id,
        problem_id=problem_id,
        replicate_id=replicate_id,
    )
    root = trajectory_root(
        repo_root=repo_root,
        matrix_config=matrix_config,
        problem_id=problem_id,
        replicate_id=replicate_id,
        run_id=current_run_id,
        run_root_override=run_root_override,
    )
    root.mkdir(parents=True, exist_ok=True)

    experiment_commit = current_git_commit(repo_root)
    started_at = utc_now()
    checkpoint_records: list[dict[str, Any]] = []

    if mode in {"native-dry-run", "native-run"}:
        before_manifest = lock_before_checkpoint(
            repo_root=repo_root,
            lock_policy=matrix_config["lock_policy"],
            checkpoint_dir=root,
        )
        native_problem_root = prepare_native_problem_fixture(
            source_problems_root=problems_root,
            artifact_root=root,
            matrix_config=matrix_config,
            config_path=config_path,
            problem_id=problem_id,
            checkpoint_ids=selected_checkpoints,
        )
        prompt_template_path = write_passthrough_prompt_template(root)
        native_config_path = write_native_run_config(
            repo_root=repo_root,
            artifact_root=root,
            matrix_config=matrix_config,
            problem_id=problem_id,
            prompt_template_path=prompt_template_path,
        )
        command_record = run_native_scbench(
            artifact_root=root,
            native_problem_root=native_problem_root,
            native_config_path=native_config_path,
            problem_id=problem_id,
            mode=mode,
            seed=int(replicate["seed"]),
            num_workers=int(matrix_config.get("runner", {}).get("num_workers", 1)),
            acceptance_feedback_policy=matrix_config["condition"].get(
                "acceptance_feedback_policy"
            ),
        )
        lock_result = lock_after_checkpoint(
            repo_root=repo_root,
            before_manifest=before_manifest,
            checkpoint_dir=root,
        )
        if command_record["exit_code"] != 0:
            run_record = {
                "schema_version": 1,
                "run_id": current_run_id,
                "condition_id": condition_id,
                "problem_id": problem_id,
                "replicate_id": replicate_id,
                "replicate_seed": int(replicate["seed"]),
                "model": native_model_string(matrix_config),
                "agent_harness": matrix_config["agent_harness"]["id"],
                "agent_version": matrix_config["agent_harness"]["version"],
                "benchmark_repo": matrix_config["runner"]["benchmark_repo"],
                "benchmark_commit": matrix_config["runner"]["benchmark_commit"],
                "problems_repo": matrix_config["runner"]["problem_repo"],
                "problems_commit": matrix_config["runner"]["problem_commit"],
                "experiment_commit": experiment_commit,
                "started_at": started_at,
                "ended_at": utc_now(),
                "status": "native_dry_run_failed"
                if mode == "native-dry-run"
                else "infrastructure_failure",
                "mode": mode,
                "checkpoint_count_expected": len(selected_checkpoints),
                "checkpoint_count_completed": 0,
                "strict_survival_checkpoint": None,
                "artifact_root": rel_path(root, repo_root),
                "native_command_exit_code": command_record["exit_code"],
                "lock_status": lock_result["status"],
                "protocol_violation": lock_result["protocol_violation"],
            }
            write_json(root / "run.json", run_record)
            write_jsonl(root / "checkpoints.jsonl", [])
            return TrajectoryResult(
                run_id=current_run_id,
                artifact_root=root,
                run_record=run_record,
                checkpoint_records=[],
            )
        if mode == "native-dry-run":
            run_record = {
                "schema_version": 1,
                "run_id": current_run_id,
                "condition_id": condition_id,
                "problem_id": problem_id,
                "replicate_id": replicate_id,
                "replicate_seed": int(replicate["seed"]),
                "model": native_model_string(matrix_config),
                "agent_harness": matrix_config["agent_harness"]["id"],
                "agent_version": matrix_config["agent_harness"]["version"],
                "benchmark_repo": matrix_config["runner"]["benchmark_repo"],
                "benchmark_commit": matrix_config["runner"]["benchmark_commit"],
                "problems_repo": matrix_config["runner"]["problem_repo"],
                "problems_commit": matrix_config["runner"]["problem_commit"],
                "experiment_commit": experiment_commit,
                "started_at": started_at,
                "ended_at": utc_now(),
                "status": "native_dry_run_prepared",
                "mode": mode,
                "checkpoint_count_expected": len(selected_checkpoints),
                "checkpoint_count_completed": 0,
                "strict_survival_checkpoint": None,
                "artifact_root": rel_path(root, repo_root),
                "native_command_exit_code": command_record["exit_code"],
                "lock_status": lock_result["status"],
                "protocol_violation": lock_result["protocol_violation"],
            }
            write_json(root / "run.json", run_record)
            write_jsonl(root / "checkpoints.jsonl", [])
            return TrajectoryResult(
                run_id=current_run_id,
                artifact_root=root,
                run_record=run_record,
                checkpoint_records=[],
            )
        native_run_record, native_checkpoint_records = export_native_run(
            artifact_root=root,
            matrix_config=matrix_config,
            run_id=current_run_id,
            problem_id=problem_id,
            replicate_id=replicate_id,
            repo_root=repo_root,
            experiment_commit=experiment_commit,
        )
        native_run_record["checkpoint_count_expected"] = len(selected_checkpoints)
        native_run_record["checkpoint_count_completed"] = len(native_checkpoint_records)
        if condition_id == "C2":
            merge_visible_acceptance_results(
                repo_root=repo_root,
                artifact_root=root,
                run_id=current_run_id,
                problem_id=problem_id,
                checkpoint_rows=native_checkpoint_records,
            )
        native_run_record["mode"] = mode
        native_run_record["lock_status"] = lock_result["status"]
        native_run_record["protocol_violation"] = lock_result["protocol_violation"]
        write_json(root / "run.json", native_run_record)
        write_jsonl(root / "checkpoints.jsonl", native_checkpoint_records)
        return TrajectoryResult(
            run_id=current_run_id,
            artifact_root=root,
            run_record=native_run_record,
            checkpoint_records=native_checkpoint_records,
        )

    for checkpoint_index, checkpoint_id in enumerate(selected_checkpoints, start=1):
        checkpoint_started = utc_now()
        checkpoint_dir = root / "checkpoints" / checkpoint_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        before_manifest = lock_before_checkpoint(
            repo_root=repo_root,
            lock_policy=matrix_config["lock_policy"],
            checkpoint_dir=checkpoint_dir,
        )
        rendered = prompt_context.render_condition_context(
            config_path=config_path,
            problem_id=problem_id,
            checkpoint_ref=checkpoint_id,
            problems_root=problems_root,
            output_dir=checkpoint_dir / "prompt_context",
        )
        prompt_metadata = dict(rendered.metadata)
        prompt_metadata["prompt_path"] = rendered.prompt_path.as_posix()
        prompt_metadata["metadata_path"] = rendered.metadata_path.as_posix()
        commands = planned_commands(
            condition_id=condition_id,
            problem_id=problem_id,
            checkpoint_id=checkpoint_id,
            config_path=config_path,
            problems_root=problems_root,
            prompt_output_dir=checkpoint_dir / "prompt_context",
        )
        write_planned_commands(checkpoint_dir / "planned_commands.md", commands)
        lock_result = lock_after_checkpoint(
            repo_root=repo_root,
            before_manifest=before_manifest,
            checkpoint_dir=checkpoint_dir,
        )
        checkpoint_ended = utc_now()
        checkpoint_records.append(
            checkpoint_record(
                matrix_config=matrix_config,
                run_id=current_run_id,
                problem_id=problem_id,
                checkpoint_id=checkpoint_id,
                checkpoint_index=checkpoint_index,
                replicate_id=replicate_id,
                replicate_seed=int(replicate["seed"]),
                experiment_commit=experiment_commit,
                prompt_metadata=prompt_metadata,
                lock_result=lock_result,
                checkpoint_dir=checkpoint_dir,
                repo_root=repo_root,
                started_at=checkpoint_started,
                ended_at=checkpoint_ended,
            )
        )

    ended_at = utc_now()
    protocol_violation = any(row["protocol_violation"] for row in checkpoint_records)
    run_status = (
        "invalid_lock_violation" if protocol_violation else "dry_run_prepared"
    )
    run_record = {
        "schema_version": 1,
        "run_id": current_run_id,
        "condition_id": condition_id,
        "problem_id": problem_id,
        "replicate_id": replicate_id,
        "replicate_seed": int(replicate["seed"]),
        "model": matrix_config["model"]["name"],
        "agent_harness": matrix_config["agent_harness"]["id"],
        "agent_version": matrix_config["agent_harness"]["version"],
        "benchmark_repo": matrix_config["runner"]["benchmark_repo"],
        "benchmark_commit": matrix_config["runner"]["benchmark_commit"],
        "problems_repo": matrix_config["runner"]["problem_repo"],
        "problems_commit": matrix_config["runner"]["problem_commit"],
        "experiment_commit": experiment_commit,
        "started_at": started_at,
        "ended_at": ended_at,
        "status": run_status,
        "mode": mode,
        "checkpoint_count_expected": len(selected_checkpoints),
        "checkpoint_count_completed": len(checkpoint_records),
        "strict_survival_checkpoint": None,
        "artifact_root": rel_path(root, repo_root),
    }

    write_json(root / "run.json", run_record)
    write_jsonl(root / "checkpoints.jsonl", checkpoint_records)
    return TrajectoryResult(
        run_id=current_run_id,
        artifact_root=root,
        run_record=run_record,
        checkpoint_records=checkpoint_records,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--problem", required=True)
    parser.add_argument("--replicate-id", type=int, required=True)
    parser.add_argument(
        "--problems-root",
        type=Path,
        default=repo_root_from_script().parent / "scb-problems",
    )
    parser.add_argument(
        "--mode",
        choices=["dry-run", "native-dry-run", "native-run"],
        default="dry-run",
    )
    parser.add_argument("--run-id")
    parser.add_argument("--run-root", type=Path)
    parser.add_argument(
        "--checkpoint-limit",
        type=int,
        help="Limit the prepared native fixture to the first N checkpoints.",
    )
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_trajectory(
        config_path=args.config.resolve(),
        problem_id=args.problem,
        replicate_id=args.replicate_id,
        problems_root=args.problems_root.resolve(),
        mode=args.mode,
        run_id=args.run_id,
        run_root_override=args.run_root.resolve() if args.run_root else None,
        checkpoint_limit=args.checkpoint_limit,
    )
    if args.print_json:
        print(json.dumps(result.run_record, indent=2, sort_keys=True))
    else:
        print(f"run_id: {result.run_id}")
        print(f"artifact_root: {result.artifact_root}")
        print(f"status: {result.run_record['status']}")
    return 0 if result.run_record["status"] != "invalid_lock_violation" else 1


if __name__ == "__main__":
    raise SystemExit(main())
