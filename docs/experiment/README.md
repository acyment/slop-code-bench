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
