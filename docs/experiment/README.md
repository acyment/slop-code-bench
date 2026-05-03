# SpecCommons SCBench Gherkin Drift Pilot

This directory is a planning package for a first pilot experiment testing whether structured and executable specifications reduce coding-agent drift over iterative feature work. It does not run the benchmark.

## Goal

Design a reproducible pilot on SlopCodeBench / SCBench that compares:

- `C0`: original checkpoint prose, as close as possible to SCBench baseline.
- `C1`: Gherkin feature files derived from checkpoint prose, provided as spec context only.
- `C2`: the same Gherkin plus a locked executable acceptance harness.

Later roadmap placeholders cover refactor prompts (`C3`), risk probes (`C4`), and agent-authored step automation (`C5`).

## Sources Inspected

Primary sources inspected on 2026-05-02:

- Paper page: https://arxiv.org/abs/2603.24755
- Project site: https://www.scbench.ai/
- Runner repo: https://github.com/SprocketLab/slop-code-bench
- Problem repo: https://github.com/gabeorlanski/scb-problems
- Runner README and docs:
  - https://github.com/SprocketLab/slop-code-bench/blob/main/README.md
  - https://github.com/SprocketLab/slop-code-bench/blob/main/docs/evaluation/README.md
  - https://github.com/SprocketLab/slop-code-bench/blob/main/docs/evaluation/architecture.md
  - https://github.com/SprocketLab/slop-code-bench/blob/main/docs/evaluation/configuration.md
  - https://github.com/SprocketLab/slop-code-bench/blob/main/docs/commands/run.md
  - https://github.com/SprocketLab/slop-code-bench/blob/main/docs/commands/metrics.md
- Runner source files inspected via raw GitHub:
  - `src/slop_code/evaluation/report.py`
  - `src/slop_code/metrics/models.py`
  - `src/slop_code/metrics/checkpoint/composites.py`
  - `src/slop_code/metrics/checkpoint/mass.py`
  - `src/slop_code/metrics/checkpoint/extractors.py`
- Runner source files inspected locally for Milestone 2:
  - `src/slop_code/agent_runner/runner.py`
  - `src/slop_code/agent_runner/reporting.py`
  - `src/slop_code/evaluation/config.py`
  - `src/slop_code/evaluation/collection.py`
  - `src/slop_code/evaluation/pytest_runner.py`
  - `src/slop_code/metrics/quality_io.py`
  - `src/slop_code/entrypoints/evaluation/metrics.py`
  - `src/slop_code/entrypoints/commands/run_agent.py`
- Problem repo files inspected:
  - top-level problem list
  - `config.yaml` for `xjq`, `code_search`, `file_backup`, `file_merger`, `file_query_tool`, `log_query`, `textdrop`, `execution_server`, `recli`, and `dynamic_config_service_api`
  - checkpoint prose for `xjq`, `code_search`, `file_backup`, and `execution_server`
  - representative pytest fixtures/tests for `xjq` and `execution_server`

Pinned upstream commits observed:

- `SprocketLab/slop-code-bench@03bf1f56752bdb4dc3e607d291870972ddd5f214`
- `gabeorlanski/scb-problems@8be2bd10bad43a3c0068bdafd05f8eb065a7dc80`

Important version note: the arXiv abstract describes the paper snapshot as 20 problems and 93 checkpoints. The current project site reports v1.0 with 36 problems and 196 checkpoints. The implementation plan targets the current repos, pinned by commit.

## Key Findings

- SCBench separates runner logic from problem definitions. The runner is `SprocketLab/slop-code-bench`; problem fixtures now live in `gabeorlanski/scb-problems`.
- Problems are directories containing `config.yaml`, `checkpoint_N.md` specs, static files, reference solutions, and pytest tests.
- Checkpoints are represented in `config.yaml`; each checkpoint has version/order/state and may configure timeout and `include_prior_tests`.
- Evaluation is pytest-based. Tests from prior checkpoints are automatically classified as regression when `include_prior_tests` is true.
- Hidden pytest tests are staged only during evaluation by copying selected files into `.evaluation_tests` in an evaluation workspace.
- The runner records structured evaluation output in `evaluation.json` and supports pass policies such as `core-cases` and `all-cases`.
- Metrics already include static quality measures, cost/time/token/step fields, pass rates, and composite `verbosity` and `erosion` summaries.
- SCBench computes verbosity from flagged verbose/slop lines or a fallback of clone ratio plus violation percentage. Erosion is the high-complexity mass share where function mass is `cyclomatic_complexity * sqrt(sloc)` and high complexity means CC greater than 10.

## Files

- `BACKLOG.md`: task-level implementation backlog.
- `BENCHMARK_ARCHITECTURE.md`: native runner/problem/evaluation/metrics data flow.
- `ACCEPTANCE_HARNESS.md`: Milestone 6 runner decision, helper scope, and smoke command.
- `EXPERIMENT_DESIGN.md`: pilot design, MVP cut, decision log.
- `HIDDEN_TEST_SEPARATION.md`: file visibility model and C2 lock requirements.
- `REPO_FORK_PLAN.md`: upstream/fork/branch and integration plan.
- `PROBLEM_SELECTION.md`: selection criteria and provisional first problem set.
- `CONDITIONS.md`: definitions for C0-C5.
- `PROMPT_TEMPLATES.md`: templates for implementation-agent prompts.
- `METRICS.md`: metric definitions and extraction plan.
- `METRIC_FIELD_MAP.md`: native SCBench field-to-schema map.
- `DATA_SCHEMA.md`: JSONL/SQLite-friendly data schema.
- `RISK_REGISTER.md`: risks and mitigations.
- `ROADMAP.md`: phased plan beyond the first pilot.
- `../../experiment/configs/*.yaml`: MVP and first-pilot run matrix configs.
- `../../experiment/schemas/run_matrix.schema.json`: schema for run matrix configs.
- `../../experiment/features/README.md`: Gherkin conversion style guide.
- `../../experiment/features/CONVERSION_LEDGER.md`: source and information-level ledger for converted feature files.
- `../../experiment/steps/acceptance/`: locked CLI/API/result helpers for visible acceptance execution.
- `../../experiment/schemas/scenario_result.schema.json`: schema for visible scenario result JSONL rows.
- `../../experiment/prompts/*.md`: materialized condition prompt templates.
- `../../experiment/scripts/generate_condition_context.py`: C0/C1/C2 prompt renderer.
- `../../experiment/scripts/validate_prompt_contexts.py`: prompt stability and condition-boundary validator.
- `../../experiment/scripts/verify_locks.py`: protected-file manifest creation and verification.
- `../../experiment/scripts/validate_locks.py`: lock violation smoke check using temporary files.
- `../../experiment/scripts/run_trajectory.py`: one-trajectory dry-run integration wrapper.
- `../../experiment/scripts/run_pilot_subset.py`: MVP/pilot subset dry-run wrapper.
- `../../experiment/scripts/export_results.py`: normalized result exporter for wrapper dry-runs and native SCBench artifacts.
- `../../experiment/scripts/analyze_results.py`: trajectory and technical-drift summary generator.
- `../../experiment/scripts/freeze_pilot_artifacts.py`: pre-execution artifact freeze manifest generator and verifier.
- `../../experiment/scripts/validate_full_pilot_preflight.py`: full-pilot readiness gate.
- `../../experiment/scripts/generate_pilot_report.py`: limitation-aware report generator.
- `../../experiment/scripts/archive_artifacts.py`: reproducibility archive builder.
- `MVP_DRY_RUN_REPORT.md`: Milestone 10 preflight run report.
- `FULL_PILOT_RUN_GATE.md`: Milestone 11 freeze and full-pilot execution gate.
- `PILOT_REPORTING.md`: Milestone 12 reporting and archive commands.

## Proposed First Pilot

- Problems: `code_search`, `file_backup`, `migrate_configs`, `log_query`, `file_merger`, and `textdrop`.
- Conditions: C0, C1, C2.
- Model/agent: one fixed model and one fixed agent harness.
- Replicates: 3 per condition if cost permits.
- Unit of analysis: full problem trajectory.
- Evaluation: hidden SCBench pytest evaluation remains the final correctness judge; visible Gherkin acceptance is an intervention and diagnostic.

## Minimum Viable Pilot

- Problems: `code_search` and `file_backup`.
- Conditions: C0 and C2 only.
- Model/agent: one fixed model and one fixed agent harness.
- Replicates: 1.
- Purpose: validate repository setup, prompt generation, lock enforcement, acceptance execution, hidden scoring, metric extraction, and export end to end.

## Run Matrix Configs

Milestone 4 freezes five initial run matrices:

- `experiment/configs/mvp_c0.yaml`
- `experiment/configs/mvp_c2.yaml`
- `experiment/configs/pilot_c0.yaml`
- `experiment/configs/pilot_c1.yaml`
- `experiment/configs/pilot_c2.yaml`

Validate them with:

```bash
uv run python experiment/scripts/validate_run_matrix.py
```

## Gherkin Feature Package

Milestone 5 adds parser-neutral Gherkin feature files for all selected first-pilot problems:

- MVP: `code_search`, `file_backup`
- Full pilot: `migrate_configs`, `log_query`, `file_merger`, `textdrop`

Validate feature structure and required tags with:

```bash
uv run python experiment/scripts/validate_features.py
```

## Acceptance Harness Prototype

Milestone 6 selects a custom parser-to-pytest adapter path and adds the locked helper layer. The current smoke runner validates the helper layer against reference solutions for `code_search`, `file_backup`, and `textdrop`.

Run smoke checks with:

```bash
uv run python experiment/scripts/run_acceptance_smoke.py \
  --problems-root ../scb-problems \
  --output-dir /tmp/scbench-acceptance-smoke
uv run python experiment/scripts/validate_scenario_results.py \
  /tmp/scbench-acceptance-smoke/scenarios.jsonl
```

## Condition Prompt Rendering

Milestone 7 materializes the condition prompt templates and renders prompt context without exposing hidden scoring internals. C0 uses checkpoint prose only, C1 adds current/prior feature-file context without runnable acceptance commands, and C2 adds the locked feature context plus the visible acceptance command.

Render one prompt with:

```bash
uv run python experiment/scripts/generate_condition_context.py \
  --config experiment/configs/mvp_c2.yaml \
  --problem code_search \
  --checkpoint checkpoint_1 \
  --problems-root ../scb-problems \
  --output-dir /tmp/scbench-prompt-contexts
```

Validate prompt stability and condition separation with:

```bash
uv run python experiment/scripts/validate_prompt_contexts.py \
  --problems-root ../scb-problems \
  --output-dir /tmp/scbench-prompt-contexts
```

## Runner Integration Dry Run

Milestone 8 adds the first runner-integration layer. It does not launch an implementation agent and does not run hidden evaluation. It prepares the trajectory artifact tree, renders prompts for every checkpoint, hashes protected files before/after each checkpoint, and emits `run.json` plus `checkpoints.jsonl` records.

Validate lock enforcement with:

```bash
uv run python experiment/scripts/validate_locks.py
```

Render a single C2 trajectory dry run with:

```bash
uv run python experiment/scripts/run_trajectory.py \
  --config experiment/configs/mvp_c2.yaml \
  --problem code_search \
  --replicate-id 1 \
  --problems-root ../scb-problems \
  --mode dry-run \
  --run-root /tmp/scbench-m8-runs \
  --run-id milestone8-smoke
```

Render an MVP subset dry run with:

```bash
uv run python experiment/scripts/run_pilot_subset.py \
  --subset mvp \
  --mode dry-run \
  --problem code_search \
  --replicate-id 1 \
  --problems-root ../scb-problems \
  --run-root /tmp/scbench-m8-mvp-subset \
  --run-id-prefix milestone8 \
  --summary-jsonl /tmp/scbench-m8-mvp-subset/summary.jsonl
```

Execution mode remains a later task: the wrapper currently records planned native SCBench and visible acceptance commands without running model agents or hidden scoring.

## Metrics Export And MVP Dry Run

Milestone 9 adds normalized export and analysis scripts. Milestone 10 ran the MVP preflight as a dry-run across `code_search` and `file_backup`, C0 and C2, one replicate each. The dry-run produced 4 trajectory records and 18 checkpoint records, all classified as `dry_run_prepared` and `not_evaluated`.

Export a dry-run root and analyze it with:

```bash
uv run python experiment/scripts/export_results.py \
  --input-root /tmp/scbench-m10-mvp-dry-run-v2 \
  --output-dir experiment/results/m10_mvp_dry_run/export

uv run python experiment/scripts/analyze_results.py \
  --results-dir experiment/results/m10_mvp_dry_run/export \
  --output-dir experiment/results/m10_mvp_dry_run/analysis
```

The current MVP result is a pipeline validation only. It does not execute implementation agents, visible acceptance tests against agent snapshots, or hidden SCBench scoring.

## Full Pilot Freeze And Gate

Milestone 11 freezes the pre-execution pilot artifact package and adds a full-pilot gate. The freeze manifest is `experiment/locks/pilot_artifact_freeze.json`; the preflight output is `experiment/results/m11_full_pilot_preflight/`.

Verify the freeze and run the gate with:

```bash
uv run python experiment/scripts/freeze_pilot_artifacts.py verify \
  --manifest experiment/locks/pilot_artifact_freeze.json

uv run python experiment/scripts/validate_full_pilot_preflight.py \
  --freeze-manifest experiment/locks/pilot_artifact_freeze.json \
  --problems-root ../scb-problems \
  --output-dir experiment/results/m11_full_pilot_preflight \
  --allow-blocked
```

The gate currently blocks primary data collection because model/agent values are still placeholders, the trajectory wrapper is dry-run only, and C2 acceptance is not yet wired to agent checkpoint snapshots.

## Reporting And Archive

Milestone 12 adds the report and archive pipeline. The current report is intentionally pre-evidence: it summarizes the M10 dry-run and M11 blocked preflight, and it marks the research claim as `not_tested`.

Generate the current report and archive with:

```bash
uv run python experiment/scripts/generate_pilot_report.py \
  --output-dir experiment/results/m12_pilot_report

uv run python experiment/scripts/archive_artifacts.py \
  --output-dir experiment/results/m12_archive/pre_evidence_archive
```
