# Implementation Backlog

Each task includes ID, title, phase, rationale, description, dependencies, acceptance criteria, complexity, implementation notes, and risks/unknowns.

## Milestone 1 - Repository Discovery And Fork Setup

### EXP-001 - Pin Canonical Upstreams

- Phase: Repository discovery and fork setup
- Rationale: Reproducibility depends on immutable runner/problem commits.
- Description: Record canonical upstream URLs, default branches, latest commits, licenses, and release tags for `SprocketLab/slop-code-bench` and `gabeorlanski/scb-problems`.
- Dependencies: none
- Acceptance criteria: `experiment/REPRODUCIBILITY.md` records runner commit, problem commit, date, and source URLs.
- Complexity: S
- Implementation notes: Use the commits observed in this planning package unless refreshed intentionally.
- Risks/unknowns: upstream moves quickly; pin before any experiment run.

### EXP-002 - Fork Runner And Problem Repos

- Phase: Repository discovery and fork setup
- Rationale: Experiment changes should be isolated from upstream benchmark code.
- Description: Fork both upstream repos after explicit authorization. Preserve upstream remotes and create `experiment/gherkin-drift-pilot` branches.
- Dependencies: EXP-001
- Acceptance criteria: forks exist, branch exists, `git remote -v` includes `origin` and `upstream`.
- Complexity: S
- Implementation notes: If only one fork is desired, use runner fork plus pinned problem checkout.
- Risks/unknowns: GitHub credentials/ownership not yet authorized.

### EXP-003 - Add Experiment Directory Skeleton

- Phase: Repository discovery and fork setup
- Rationale: Keep additions clean and additive.
- Description: Create `experiment/` with configs, prompts, features, steps, scripts, schemas, locks, runs, and results directories.
- Dependencies: EXP-002
- Acceptance criteria: directory tree matches `REPO_FORK_PLAN.md`; placeholder `.gitkeep` files exist where needed.
- Complexity: S
- Implementation notes: Avoid changing `src/slop_code` initially.
- Risks/unknowns: runner may already have conventions for external configs.

### EXP-004 - Add Reproducibility Document

- Phase: Repository discovery and fork setup
- Rationale: Every run needs commit/model/prompt provenance.
- Description: Add `experiment/REPRODUCIBILITY.md` with required metadata fields and update procedure.
- Dependencies: EXP-003
- Acceptance criteria: document has a checklist for commits, model, agent, environment, prompt hashes, feature hashes, step hashes, run IDs, and deviations.
- Complexity: S
- Implementation notes: Make this human-editable plus machine-updatable later.
- Risks/unknowns: agent harness may not expose all token/cost fields.

## Milestone 2 - Benchmark Architecture Understanding

### EXP-010 - Document Native SCBench Data Flow

- Phase: Benchmark architecture understanding
- Status: completed in `docs/experiment/BENCHMARK_ARCHITECTURE.md`
- Rationale: The experiment should wrap SCBench, not replace it.
- Description: Trace `slop-code run`, `eval`, and `metrics static` outputs from docs/source into a short architecture note.
- Dependencies: EXP-001
- Acceptance criteria: note identifies where checkpoint outputs, `evaluation.json`, quality metrics, inference usage, and summary files are written.
- Complexity: M
- Implementation notes: Confirm with a cheap reference-solution or dry-run command if available.
- Risks/unknowns: output layout may differ by agent harness.

### EXP-011 - Verify Hidden-Test Separation Mechanism

- Phase: Benchmark architecture understanding
- Status: completed in `docs/experiment/HIDDEN_TEST_SEPARATION.md`
- Rationale: Hidden tests must stay hidden from implementation agents.
- Description: Inspect runner prompt construction and workspace staging to confirm tests are not copied into the agent-visible workspace during inference.
- Dependencies: EXP-010
- Acceptance criteria: documented file visibility model and any required lock/exclusion changes.
- Complexity: M
- Implementation notes: SCBench tests are source-available to maintainers but should be hidden from implementation-agent context.
- Risks/unknowns: local runner implementation may stage tests differently than docs imply.

### EXP-012 - Map Native Metric Fields

- Phase: Benchmark architecture understanding
- Status: completed in `docs/experiment/METRIC_FIELD_MAP.md`
- Rationale: Technical drift should reuse SCBench definitions first.
- Description: Create a field map for native metrics: pass rates, cost, tokens, duration, steps, verbosity, erosion, complexity, clone metrics, and graph metrics.
- Dependencies: EXP-010
- Acceptance criteria: `METRICS.md` or generated field map lists source file and normalized schema field.
- Complexity: M
- Implementation notes: Use `metrics/checkpoint/extractors.py`, `metrics/models.py`, and `metrics/checkpoint/composites.py`.
- Risks/unknowns: not all metrics exist for every language/problem.

## Milestone 3 - Problem Selection

### EXP-020 - Build Problem Inventory Script

- Phase: Problem selection
- Status: completed in `experiment/scripts/select_problems.py`
- Rationale: Selection should be auditable, not hand-picked after results.
- Description: Implement `experiment/scripts/select_problems.py` to parse all problem configs and summarize category, tags, difficulty, checkpoints, dependencies, static assets, and prior-test behavior.
- Dependencies: EXP-003
- Acceptance criteria: script writes `experiment/results/problem_inventory.jsonl`.
- Complexity: M
- Implementation notes: Use PyYAML; no benchmark runs needed.
- Risks/unknowns: configs may have minor schema differences.

### EXP-021 - Measure Reference Test Runtime

- Phase: Problem selection
- Status: completed for selected candidates in `experiment/results/problem_inventory.jsonl`
- Rationale: Avoid unexpectedly expensive first pilot problems.
- Description: Run reference solution tests or available oracle checks for candidate problems and record runtime by checkpoint.
- Dependencies: EXP-020
- Acceptance criteria: `problem_inventory.jsonl` includes `reference_runtime_seconds` and infrastructure failures.
- Complexity: M
- Implementation notes: Use pinned problem repo and SCBench runner if possible.
- Risks/unknowns: Docker setup may be required.

### EXP-022 - Finalize First 5-6 Problems

- Phase: Problem selection
- Status: completed in `docs/experiment/PROBLEM_SELECTION.md`
- Rationale: The pilot needs a fixed problem set before prompt/harness work.
- Description: Apply selection criteria and choose final problems. Final selected set is `code_search`, `file_backup`, `migrate_configs`, `log_query`, `file_merger`, `textdrop`.
- Dependencies: EXP-020, EXP-021
- Acceptance criteria: `PROBLEM_SELECTION.md` updated with final set, exclusions, and rationale.
- Complexity: S
- Implementation notes: Runtime inspection changed MVP to `code_search` and `file_backup`; keep `xjq` as an alternate pending reference mismatch triage.
- Risks/unknowns: provisional set may shift after runtime and fixture inspection.

## Milestone 4 - Experiment Design Finalization

### EXP-030 - Freeze Condition Definitions

- Phase: Experiment design finalization
- Rationale: C0/C1/C2 must isolate different causal factors.
- Description: Review and freeze condition rules, visible/hidden file exposure, lock behavior, and invalid-run policy.
- Dependencies: EXP-011
- Acceptance criteria: `CONDITIONS.md` approved; scripts encode same rules.
- Complexity: S
- Implementation notes: C2+ forbids changes to features, steps, harness, scoring, schemas, and locks.
- Risks/unknowns: exact file lock mechanism depends on runner workspace staging.

### EXP-031 - Define Run Matrix

- Phase: Experiment design finalization
- Rationale: Runs should be paired and reproducible.
- Description: Generate MVP and full pilot config YAML files listing problems, conditions, replicates, model, agent harness, and seeds.
- Dependencies: EXP-022, EXP-030
- Acceptance criteria: `pilot_c0.yaml`, `pilot_c1.yaml`, `pilot_c2.yaml`, `mvp_c0.yaml`, `mvp_c2.yaml` exist and validate against schema.
- Complexity: M
- Implementation notes: Condition order randomization can be config-generated.
- Risks/unknowns: SCBench native config structure must be confirmed.

## Milestone 5 - Gherkin Conversion Prototype

### EXP-040 - Define Gherkin Style Guide

- Phase: Gherkin conversion prototype
- Rationale: Feature files must be consistent across problems.
- Description: Write rules for tags, scenario names, step wording, examples, scenario outlines, data tables, and conversion ledgers.
- Dependencies: EXP-030
- Acceptance criteria: style guide exists under `experiment/features/README.md`.
- Complexity: S
- Implementation notes: Include tags for problem, checkpoint, core/regression/edge, positive/negative.
- Risks/unknowns: over-detailed scenarios may leak implementation hints.

### EXP-041 - Convert MVP Problem Features

- Phase: Gherkin conversion prototype
- Rationale: MVP needs concrete feature files to validate the pipeline.
- Description: Convert all checkpoints for `code_search` and `file_backup` into `.feature` files.
- Dependencies: EXP-040
- Acceptance criteria: feature files exist, parse with selected Gherkin parser, and include conversion ledger entries.
- Complexity: L
- Implementation notes: Preserve prior behavior in prior checkpoint feature files; avoid hidden-test-derived details.
- Risks/unknowns: original specs may contain examples that need normalization.

### EXP-042 - Convert Full Pilot Features

- Phase: Gherkin conversion prototype
- Rationale: Full pilot needs complete C1/C2 context.
- Description: Convert final 5-6 selected problems after MVP validation.
- Dependencies: EXP-041, EXP-022
- Acceptance criteria: all selected problem checkpoints have features and ledger entries.
- Complexity: XL
- Implementation notes: Batch conversion by problem; review each against original prose.
- Risks/unknowns: conversion workload may dominate setup time.

## Milestone 6 - Acceptance Harness Prototype

### EXP-050 - Select Gherkin Runner

- Phase: Acceptance harness prototype
- Rationale: Runner choice affects speed, lockability, and output schema.
- Description: Compare `pytest-bdd`, `behave`, and a custom parser-to-pytest adapter for CLI/API tasks.
- Dependencies: EXP-041
- Acceptance criteria: decision recorded with rationale and a smoke test.
- Complexity: M
- Implementation notes: Prefer pytest integration if it fits SCBench's existing pytest ecosystem and JSON reporting.
- Risks/unknowns: Gherkin libraries may impose awkward fixtures for subprocess/API tests.

### EXP-051 - Implement CLI Acceptance Helpers

- Phase: Acceptance harness prototype
- Rationale: MVP problems are CLI-oriented.
- Description: Add helpers for command execution, stdin, stdout/stderr assertions, JSONL parsing, temp files, and exit-code checks.
- Dependencies: EXP-050
- Acceptance criteria: helpers can run `code_search` and `file_backup` scenarios against reference solutions.
- Complexity: M
- Implementation notes: Keep helpers generic and locked in C2.
- Risks/unknowns: entrypoint handling must match SCBench.

### EXP-052 - Implement API Acceptance Helpers

- Phase: Acceptance harness prototype
- Rationale: Full pilot may include `textdrop` or another HTTP/API problem.
- Description: Add helpers for server startup, port allocation, HTTP requests, teardown, and runtime capture.
- Dependencies: EXP-050
- Acceptance criteria: helpers pass a smoke scenario against a reference service problem.
- Complexity: L
- Implementation notes: Use deterministic timeouts and clear harness-error classification.
- Risks/unknowns: service lifecycle flakiness.

### EXP-053 - Add Machine-Readable Acceptance Output

- Phase: Acceptance harness prototype
- Rationale: Scenario results need to merge with hidden SCBench scoring.
- Description: Emit JSONL scenario records with status, tags, duration, failure type, stdout/stderr paths.
- Dependencies: EXP-051
- Acceptance criteria: `scenarios.jsonl` conforms to `DATA_SCHEMA.md`.
- Complexity: M
- Implementation notes: Distinguish scenario failure, step error, product error, and harness error.
- Risks/unknowns: mapping framework exceptions to failure types may need adapters.

## Milestone 7 - Condition Prompt Templates

### EXP-060 - Implement Prompt Files

- Phase: Condition prompt templates
- Rationale: Prompts must be versioned and hashable.
- Description: Move templates from `PROMPT_TEMPLATES.md` into `experiment/prompts/*.md` with render variables.
- Dependencies: EXP-030
- Acceptance criteria: template files exist and are rendered in tests.
- Complexity: S
- Implementation notes: Keep C0 close to upstream `just-solve.jinja`.
- Risks/unknowns: runner may require Jinja templates rather than markdown.

### EXP-061 - Generate Condition Context

- Phase: Condition prompt templates
- Rationale: C0/C1/C2 differ mainly by supplied context and commands.
- Description: Implement `generate_condition_context.py` that renders C0 prose, C1 Gherkin context, and C2 Gherkin plus acceptance commands.
- Dependencies: EXP-060, EXP-041
- Acceptance criteria: generated prompts have stable hashes and no forbidden file contents.
- Complexity: M
- Implementation notes: Add tests that C0 excludes Gherkin and C1 excludes runnable commands.
- Risks/unknowns: prompt length may grow for later checkpoints.

## Milestone 8 - Runner Integration

### EXP-070 - Implement Lock Manifest

- Phase: Runner integration
- Rationale: C2 validity depends on protected-file integrity.
- Description: Implement `verify_locks.py` to hash protected files before and after a checkpoint run.
- Dependencies: EXP-003
- Acceptance criteria: intentional modification to a feature file marks run invalid.
- Complexity: M
- Implementation notes: Store manifest hash in checkpoint records.
- Risks/unknowns: files copied into workspaces may need path mapping.

### EXP-071 - Implement Trajectory Wrapper

- Phase: Runner integration
- Rationale: Need a single command per `(condition, problem, replicate)`.
- Description: Implement `run_trajectory.py` to prepare workspace, render prompts, call SCBench runner, run visible acceptance for C2, run hidden eval, verify locks, and collect artifacts.
- Dependencies: EXP-031, EXP-061, EXP-070
- Acceptance criteria: dry run or mocked runner produces expected artifact tree and JSONL rows.
- Complexity: XL
- Implementation notes: Start with MVP; keep SCBench native outputs intact.
- Risks/unknowns: integrating per-checkpoint hooks may require runner changes.

### EXP-072 - Add Pilot Subset Scripts

- Phase: Runner integration
- Rationale: Runs should be easy to reproduce.
- Description: Add scripts or Make targets for MVP and pilot subsets.
- Dependencies: EXP-071
- Acceptance criteria: documented commands rerun MVP C0/C2 and selected single trajectories.
- Complexity: S
- Implementation notes: Do not hard-code credentials.
- Risks/unknowns: local Docker availability.

## Milestone 9 - Metrics Extraction

### EXP-080 - Export Native SCBench Results

- Phase: Metrics extraction
- Rationale: Analysis should consume normalized tables.
- Description: Implement `export_results.py` to parse native SCBench output and emit `runs.jsonl`, `checkpoints.jsonl`, and `technical_metrics.jsonl`.
- Dependencies: EXP-071, EXP-012
- Acceptance criteria: exported rows validate against schemas.
- Complexity: L
- Implementation notes: Preserve links to native artifacts.
- Risks/unknowns: missing metric files for failed checkpoints.

### EXP-081 - Compute Drift Metrics

- Phase: Metrics extraction
- Rationale: Need trajectory-level comparisons.
- Description: Implement strict survival, regression rate, hidden failure after visible pass, verbosity/erosion slopes, change amplification, dependency creep, and runtime growth.
- Dependencies: EXP-080
- Acceptance criteria: `analyze_results.py` writes summary JSON and markdown tables.
- Complexity: L
- Implementation notes: Treat missing checkpoints as failures for survival.
- Risks/unknowns: small sample sizes limit inference.

## Milestone 10 - Pilot Dry Run

### EXP-090 - Run MVP

- Phase: Pilot dry run
- Rationale: Validate the whole pipeline before spending on full pilot.
- Description: Run 2 problems, C0 vs C2, 1 replicate, 1 model/harness.
- Dependencies: EXP-041, EXP-051, EXP-071, EXP-080
- Acceptance criteria: 4 trajectories complete or fail with classified reasons; exports and report are generated.
- Complexity: L
- Implementation notes: Do not interpret results as evidence beyond pipeline validation.
- Risks/unknowns: agent cost/API availability.

### EXP-091 - Fix Pipeline Issues From MVP

- Phase: Pilot dry run
- Rationale: MVP should surface prompt, lock, harness, and export bugs.
- Description: Triage failures, patch harness/wrapper/export code, and rerun MVP if needed.
- Dependencies: EXP-090
- Acceptance criteria: MVP can be reproduced from clean checkout.
- Complexity: M
- Implementation notes: Record all changes in reproducibility/deviation logs.
- Risks/unknowns: fixing harness after seeing outcomes can bias full pilot; freeze before full run.

## Milestone 11 - Full Pilot Run

### EXP-100 - Freeze Pilot Artifacts

- Phase: Full pilot run
- Rationale: Features, steps, prompts, and schemas must be fixed before data collection.
- Description: Tag or commit the experiment artifacts and write hashes to reproducibility docs.
- Dependencies: EXP-091, EXP-042
- Acceptance criteria: immutable experiment commit selected.
- Complexity: S
- Implementation notes: No feature/step edits after freeze except documented invalidation.
- Risks/unknowns: late-discovered harness bugs.

### EXP-101 - Run Full Pilot Matrix

- Phase: Full pilot run
- Rationale: Collect paired C0/C1/C2 trajectories.
- Description: Run selected problems across C0/C1/C2 and 3 replicates if budget allows.
- Dependencies: EXP-100
- Acceptance criteria: all configured trajectories have completed/failed/invalid status and artifacts.
- Complexity: XL
- Implementation notes: Randomize condition order by replicate.
- Risks/unknowns: cost/runtime may require partial matrix.

## Milestone 12 - Analysis And Reporting

### EXP-110 - Generate Pilot Report

- Phase: Analysis/reporting
- Rationale: Results need transparent interpretation and limitations.
- Description: Produce report with inspected setup, run matrix, pass/fail matrix, survival, regressions, hidden-after-visible failures, quality slopes, and cost metrics.
- Dependencies: EXP-101, EXP-081
- Acceptance criteria: report clearly states no causal proof; includes data and scripts.
- Complexity: L
- Implementation notes: Include per-problem paired plots and tables.
- Risks/unknowns: small samples may be noisy.

### EXP-111 - Archive Artifacts

- Phase: Analysis/reporting
- Rationale: Runs need to be reproducible and reviewable.
- Description: Export artifacts, configs, prompts, hashes, logs, and normalized data to an archive directory.
- Dependencies: EXP-110
- Acceptance criteria: archive manifest lists every artifact and hash.
- Complexity: M
- Implementation notes: Exclude secrets and raw API credentials.
- Risks/unknowns: artifact size.

## Milestone 13 - Later-Phase Roadmap

### EXP-120 - Implement C3 Refactor Cadence

- Phase: Later-phase roadmap
- Rationale: Test whether scheduled refactoring slows technical drift.
- Description: Insert refactor-only turns after every 2-3 checkpoints and compare C2 vs C3.
- Dependencies: EXP-110
- Acceptance criteria: C3 run matrix and prompts exist; refactor turns are marked separately in data.
- Complexity: L
- Implementation notes: No new behavior allowed.
- Risks/unknowns: refactor turns may increase cost without benefit.

### EXP-121 - Implement C4 Risk Probes

- Phase: Later-phase roadmap
- Rationale: Test security/architecture/test/dependency probes separately from executable specs.
- Description: Add rotating risk probe prompts and result schema.
- Dependencies: EXP-120
- Acceptance criteria: probe outcomes are traceable and separated from feature checkpoints.
- Complexity: L
- Implementation notes: Keep probes narrow.
- Risks/unknowns: probes may become generic lint prompts.

### EXP-122 - Implement C5 Agent-Authored Steps

- Phase: Later-phase roadmap
- Rationale: Evaluate generated acceptance automation quality.
- Description: Let agents implement missing step definitions and score harness correctness, brittleness, runtime, and overfit.
- Dependencies: EXP-110
- Acceptance criteria: generated steps are compared to maintainer-authored steps on reference solutions and hidden outcomes.
- Complexity: XL
- Implementation notes: Requires separate harness-quality rubric.
- Risks/unknowns: generated harness may encode wrong behavior.
