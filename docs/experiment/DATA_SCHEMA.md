# Data Schema

Use append-only JSONL as the canonical artifact format and load it into SQLite or DuckDB for analysis.

## Files

```text
experiment/results/runs.jsonl
experiment/results/checkpoints.jsonl
experiment/results/scenarios.jsonl
experiment/results/technical_metrics.jsonl
experiment/results/cost_events.jsonl
experiment/results/artifacts.jsonl
```

## Run Record

One row per full trajectory.

```json
{
  "schema_version": 1,
  "run_id": "20260502-c2-code-search-r01",
  "condition_id": "C2",
  "problem_id": "code_search",
  "replicate_id": 1,
  "model": "provider/model",
  "agent_harness": "codex|claude_code|other",
  "agent_version": "string-or-null",
  "benchmark_repo": "SprocketLab/slop-code-bench",
  "benchmark_commit": "03bf1f56752bdb4dc3e607d291870972ddd5f214",
  "problems_repo": "gabeorlanski/scb-problems",
  "problems_commit": "8be2bd10bad43a3c0068bdafd05f8eb065a7dc80",
  "experiment_commit": "git-sha",
  "branch": "experiment/gherkin-drift-pilot",
  "started_at": "2026-05-02T12:00:00Z",
  "ended_at": "2026-05-02T12:30:00Z",
  "status": "completed|failed|invalid_lock_violation|infrastructure_failure",
  "checkpoint_count_expected": 5,
  "checkpoint_count_completed": 5,
  "strict_survival_checkpoint": "checkpoint_3",
  "artifact_root": "experiment/runs/..."
}
```

## Checkpoint Record

One row per trajectory checkpoint.

```json
{
  "schema_version": 1,
  "run_id": "20260502-c2-code-search-r01",
  "condition_id": "C2",
  "problem_id": "code_search",
  "checkpoint_id": "checkpoint_3",
  "checkpoint_index": 3,
  "replicate_id": 1,
  "model": "provider/model",
  "agent_harness": "codex",
  "agent_version": "version",
  "benchmark_commit": "03bf1f56752bdb4dc3e607d291870972ddd5f214",
  "problems_commit": "8be2bd10bad43a3c0068bdafd05f8eb065a7dc80",
  "experiment_commit": "git-sha",
  "started_at": "2026-05-02T12:10:00Z",
  "ended_at": "2026-05-02T12:15:00Z",
  "prompt_template_id": "gherkin_executable.v1",
  "prompt_hash": "sha256",
  "context_hash": "sha256",
  "feature_hash": "sha256-or-null",
  "step_hash": "sha256-or-null",
  "lock_manifest_hash": "sha256-or-null",
  "lock_status": "unchanged|changed|not_applicable",
  "visible_acceptance_passed": true,
  "hidden_tests_passed": true,
  "current_checkpoint_passed": true,
  "prior_regression_count": 0,
  "hidden_failure_after_visible_pass": false,
  "scbench": {
    "strict_pass_rate": 1.0,
    "isolated_pass_rate": 1.0,
    "core_pass_rate": 1.0,
    "total_tests": 25,
    "passed_tests": 25,
    "core_total": 5,
    "core_passed": 5,
    "regression_total": 20,
    "regression_passed": 20,
    "functionality_total": 0,
    "functionality_passed": 0,
    "error_total": 0,
    "error_passed": 0,
    "infrastructure_failure": false
  },
  "scenario_results": [],
  "hidden_test_summary": {},
  "technical_metrics": {},
  "cost_metrics": {},
  "artifact_paths": {}
}
```

## Scenario Record

One row per visible Gherkin scenario execution.

```json
{
  "schema_version": 1,
  "run_id": "20260502-c2-code-search-r01",
  "problem_id": "code_search",
  "checkpoint_id": "checkpoint_3",
  "scenario_id": "code_search.cp003.literal-query-basic",
  "feature_path": "experiment/features/code_search/checkpoint_003.feature",
  "scenario_name": "Find matching code lines with a literal query",
  "tags": ["problem:code_search", "checkpoint:3", "core", "positive"],
  "status": "passed|failed|error|skipped",
  "failure_type": "scenario_failure|step_error|product_error|harness_error|null",
  "duration_ms": 123.4,
  "stdout_path": "path-or-null",
  "stderr_path": "path-or-null"
}
```

## Technical Metric Record

One row per checkpoint, split out for easier analytics.

```json
{
  "schema_version": 1,
  "run_id": "20260502-c2-code-search-r01",
  "problem_id": "code_search",
  "checkpoint_id": "checkpoint_3",
  "condition_id": "C2",
  "replicate_id": 1,
  "loc": 400,
  "sloc": 320,
  "verbosity": 0.12,
  "erosion": 0.08,
  "cc_max": 9,
  "cc_mean": 2.4,
  "cc_high_count": 0,
  "clone_lines": 10,
  "cloned_pct": 0.03,
  "lines_added": 80,
  "lines_removed": 12,
  "files_changed": 3,
  "dependencies_added": [],
  "acceptance_runtime_ms": 900.0,
  "hidden_eval_runtime_ms": 2300.0
}
```

## SQLite Mapping

Load JSONL files into tables:

- `runs`
- `checkpoints`
- `scenarios`
- `technical_metrics`
- `cost_events`
- `artifacts`

Primary keys:

- `runs`: `run_id`
- `checkpoints`: `(run_id, checkpoint_id)`
- `scenarios`: `(run_id, checkpoint_id, scenario_id)`
- `technical_metrics`: `(run_id, checkpoint_id)`
