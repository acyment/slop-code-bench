# Native SCBench Architecture Notes

Status: EXP-010 implementation note.

Inspected on 2026-05-02 against:

- Runner fork: `SprocketLab/slop-code-bench@03bf1f56752bdb4dc3e607d291870972ddd5f214`
- Problem fork: `gabeorlanski/scb-problems@8be2bd10bad43a3c0068bdafd05f8eb065a7dc80`

This note documents the benchmark path the Gherkin drift pilot should wrap. The pilot should preserve this native path unless a later implementation task records a necessary deviation.

## Repository Boundary

SCBench currently separates benchmark execution from fixtures:

- `slop-code-bench`: runner, agent adapters, evaluation, metrics, reporting, docs.
- `scb-problems`: problem fixtures, checkpoint prose, pytest tests, reference solutions, and static assets.

The local problem checkout contains 36 problem configs, 196 checkpoint prose files, and 196 checkpoint pytest files at the pinned commit.

## Problem Fixture Format

Each problem is a directory under the problem repo. Representative fields:

- `config.yaml`: metadata, `entry_file`, timeout, tags, difficulty, optional `test_dependencies`, optional `static_assets`, and ordered checkpoints.
- `checkpoint_N.md`: prose specification exposed to the implementation agent for checkpoint `N`.
- `tests/test_checkpoint_N.py`: pytest tests used during benchmark evaluation.
- `tests/conftest.py` and helper files: shared pytest fixtures and CLI/API helpers.
- `solutions/checkpoint_N/`: reference or example solution material, not part of implementation-agent context.

Checkpoint config fields loaded by `src/slop_code/evaluation/config.py` include:

- `name`
- `version`
- `order`
- `state`
- `timeout`
- `env`
- `include_prior_tests`

`ProblemConfig.get_checkpoint_spec()` reads `checkpoint_N.md` from the problem root. This is the native prose source for C0.

## Native Run Flow

The normal `slop-code run` path is:

1. Resolve runner config from CLI flags, config YAML, built-in defaults, and overrides.
2. Load problem configs with `ProblemConfig.from_yaml()`.
3. Iterate checkpoints by `(order, name)`.
4. Create a checkpoint output directory and write `checkpoint.yaml`.
5. Render an agent prompt from:
   - checkpoint prose from `checkpoint_N.md`;
   - configured prompt template;
   - formatted entry file;
   - agent-visible entry command.
6. Save the rendered prompt as `prompt.txt`.
7. Run the agent against an inference session created with `is_agent_infer=True`.
8. Finish the checkpoint session and save a code snapshot under `snapshot/`.
9. Save inference artifacts:
   - `inference_result.json`
   - `diff.json`
   - `agent/` or `agent.tar.gz`
10. If evaluation is enabled, evaluate the saved `snapshot/` through the pytest evaluator.
11. Save correctness output as `evaluation.json` plus pytest stdout/stderr/report artifacts.
12. Measure static quality on the saved snapshot and write `quality_analysis/`.
13. After all selected problems complete, write run-level `checkpoint_results.jsonl` and `result.json`.

Primary runner files:

- `src/slop_code/agent_runner/runner.py`
- `src/slop_code/agent_runner/reporting.py`
- `src/slop_code/evaluation/config.py`
- `src/slop_code/evaluation/collection.py`
- `src/slop_code/evaluation/pytest_runner.py`
- `src/slop_code/evaluation/report.py`
- `src/slop_code/entrypoints/commands/run_agent.py`

## Native Evaluation Flow

Checkpoint evaluation is pytest based:

1. `run_checkpoint_pytest()` delegates to `run_checkpoint_with_collection()`.
2. Collection prepares a separate evaluation session with `is_agent_infer=False`.
3. Checkpoint-relevant tests are copied from `<problem>/tests` into `.evaluation_tests` in the evaluation workspace.
4. Test collection runs pytest in collect-only passes to compute a deterministic `test_collection_hash`.
5. `PytestRunner.run()` executes pytest against `.evaluation_tests`.
6. Results are parsed from `pytest-json-report` first, with CTRF as fallback.
7. Tests are grouped into `Core`, `Functionality`, `Regression`, and `Error`.
8. `CorrectnessResults.save()` writes:
   - `evaluation.json`
   - `evaluation/stdout.txt`
   - `evaluation/stderr.txt`
   - `evaluation/report.json` when available.

Prior checkpoint behavior is included when `include_prior_tests: true`. In that mode the evaluator copies `test_checkpoint_1.py` through the current checkpoint's test file. Prior checkpoint tests are classified as `Regression`.

## Native Metrics Flow

Quality metrics are generated from the saved snapshot, not from live agent state:

1. `measure_snapshot_quality()` analyzes the checkpoint `snapshot/`.
2. `save_quality_metrics()` writes:
   - `quality_analysis/overall_quality.json`
   - `quality_analysis/files.jsonl`
   - `quality_analysis/symbols.jsonl`
   - `quality_analysis/ast_grep.jsonl`
3. `create_problem_reports()` flattens checkpoint-level artifacts into run-level rows.
4. `display_and_save_summary()` computes and saves run-level `result.json`.

Primary metrics files:

- `src/slop_code/metrics/quality_io.py`
- `src/slop_code/metrics/checkpoint/extractors.py`
- `src/slop_code/metrics/checkpoint/composites.py`
- `src/slop_code/metrics/checkpoint/mass.py`
- `src/slop_code/entrypoints/evaluation/metrics.py`
- `src/slop_code/entrypoints/utils.py`

## Output Layout

Native output path is resolved as:

```text
<save_dir>/<save_template>/
```

A typical run layout after inference, evaluation, and static metrics:

```text
<run_dir>/
  config.yaml
  checkpoint_results.jsonl
  result.json
  <problem_id>/
    problem.yaml
    environment.yaml
    run_info.yaml
    checkpoint_1/
      checkpoint.yaml
      prompt.txt
      inference_result.json
      diff.json
      snapshot/
      agent/
      evaluation.json
      evaluation/
        stdout.txt
        stderr.txt
        report.json
      quality_analysis/
        overall_quality.json
        files.jsonl
        symbols.jsonl
        ast_grep.jsonl
    checkpoint_2/
      ...
```

Some files are optional depending on whether evaluation, quality analysis, artifact compression, or failure handling ran successfully.

## Pilot Integration Points

Recommended first-pilot wrapping strategy:

- C0 should reuse the native checkpoint prose path as closely as possible.
- C1 should generate alternate prompt context from experiment-owned Gherkin files without changing native `checkpoint_N.md`.
- C2 should add an experiment-owned visible acceptance harness that runs before or after native evaluation, but must not replace `evaluation.json` as the final correctness judge.
- Experiment scripts should append experiment metadata and visible-acceptance results into experiment-owned artifacts under `experiment/results/` or run-local sidecar files.
- Native SCBench hidden pytest tests should remain in the problem repo and be invoked only through native evaluation.
- Any required changes under `src/slop_code` must be recorded in `REPO_FORK_PLAN.md` and linked to a task.

## Open Implementation Questions

- Whether C1/C2 prompt generation should be implemented as new SCBench prompt templates or as an experiment wrapper that materializes prompt files before invoking the agent.
- Whether visible acceptance results should be written into native `checkpoint_results.jsonl` as extra fields or stored in a separate experiment JSONL joined by run/problem/checkpoint.
- Whether the lock mechanism should be implemented in the agent workspace setup, the experiment wrapper, or both.
- Whether dry-run/reference-solution commands are cheap enough to add to Milestone 3 runtime inspection.
