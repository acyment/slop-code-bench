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
- Status: completed in `docs/experiment/CONDITIONS.md`
- Rationale: C0/C1/C2 must isolate different causal factors.
- Description: Review and freeze condition rules, visible/hidden file exposure, lock behavior, and invalid-run policy.
- Dependencies: EXP-011
- Acceptance criteria: `CONDITIONS.md` approved; scripts encode same rules.
- Complexity: S
- Implementation notes: C2+ forbids changes to features, steps, harness, scoring, schemas, and locks.
- Risks/unknowns: exact file lock mechanism depends on runner workspace staging.

### EXP-031 - Define Run Matrix

- Phase: Experiment design finalization
- Status: completed in `experiment/configs/*.yaml`
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
- Status: completed in `experiment/features/README.md`
- Rationale: Feature files must be consistent across problems.
- Description: Write rules for tags, scenario names, step wording, examples, scenario outlines, data tables, and conversion ledgers.
- Dependencies: EXP-030
- Acceptance criteria: style guide exists under `experiment/features/README.md`.
- Complexity: S
- Implementation notes: Include tags for problem, checkpoint, core/regression/edge, positive/negative.
- Risks/unknowns: over-detailed scenarios may leak implementation hints.

### EXP-041 - Convert MVP Problem Features

- Phase: Gherkin conversion prototype
- Status: completed in `experiment/features/code_search/` and `experiment/features/file_backup/`
- Rationale: MVP needs concrete feature files to validate the pipeline.
- Description: Convert all checkpoints for `code_search` and `file_backup` into `.feature` files.
- Dependencies: EXP-040
- Acceptance criteria: feature files exist, pass parser-neutral feature lint, and include conversion ledger entries. Runner-specific parse is deferred to EXP-050.
- Complexity: L
- Implementation notes: Preserve prior behavior in prior checkpoint feature files; avoid hidden-test-derived details.
- Risks/unknowns: original specs may contain examples that need normalization.

### EXP-042 - Convert Full Pilot Features

- Phase: Gherkin conversion prototype
- Status: completed in `experiment/features/`
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
- Status: completed in `docs/experiment/ACCEPTANCE_HARNESS.md`
- Rationale: Runner choice affects speed, lockability, and output schema.
- Description: Compare `pytest-bdd`, `behave`, and a custom parser-to-pytest adapter for CLI/API tasks.
- Dependencies: EXP-041
- Acceptance criteria: decision recorded with rationale and a smoke test.
- Complexity: M
- Implementation notes: Prefer pytest integration if it fits SCBench's existing pytest ecosystem and JSON reporting.
- Risks/unknowns: Gherkin libraries may impose awkward fixtures for subprocess/API tests.

### EXP-051 - Implement CLI Acceptance Helpers

- Phase: Acceptance harness prototype
- Status: completed in `experiment/steps/acceptance/cli.py`
- Rationale: MVP problems are CLI-oriented.
- Description: Add helpers for command execution, stdin, stdout/stderr assertions, JSONL parsing, temp files, and exit-code checks.
- Dependencies: EXP-050
- Acceptance criteria: helpers can run `code_search` and `file_backup` scenarios against reference solutions.
- Complexity: M
- Implementation notes: Keep helpers generic and locked in C2.
- Risks/unknowns: entrypoint handling must match SCBench.

### EXP-052 - Implement API Acceptance Helpers

- Phase: Acceptance harness prototype
- Status: completed in `experiment/steps/acceptance/api.py`
- Rationale: Full pilot may include `textdrop` or another HTTP/API problem.
- Description: Add helpers for server startup, port allocation, HTTP requests, teardown, and runtime capture.
- Dependencies: EXP-050
- Acceptance criteria: helpers pass a smoke scenario against a reference service problem.
- Complexity: L
- Implementation notes: Use deterministic timeouts and clear harness-error classification.
- Risks/unknowns: service lifecycle flakiness.

### EXP-053 - Add Machine-Readable Acceptance Output

- Phase: Acceptance harness prototype
- Status: completed in `experiment/steps/acceptance/results.py` and `experiment/schemas/scenario_result.schema.json`
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
- Status: completed in `experiment/prompts/*.md`
- Rationale: Prompts must be versioned and hashable.
- Description: Move templates from `PROMPT_TEMPLATES.md` into `experiment/prompts/*.md` with render variables.
- Dependencies: EXP-030
- Acceptance criteria: template files exist and are rendered in tests.
- Complexity: S
- Implementation notes: Keep C0 close to upstream `just-solve.jinja`.
- Risks/unknowns: runner may require Jinja templates rather than markdown.

### EXP-061 - Generate Condition Context

- Phase: Condition prompt templates
- Status: completed in `experiment/scripts/generate_condition_context.py`
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
- Status: completed in `experiment/scripts/verify_locks.py`
- Rationale: C2 validity depends on protected-file integrity.
- Description: Implement `verify_locks.py` to hash protected files before and after a checkpoint run.
- Dependencies: EXP-003
- Acceptance criteria: intentional modification to a feature file marks run invalid.
- Complexity: M
- Implementation notes: Store manifest hash in checkpoint records.
- Risks/unknowns: files copied into workspaces may need path mapping.

### EXP-071 - Implement Trajectory Wrapper

- Phase: Runner integration
- Status: completed for dry-run and native execution in `experiment/scripts/run_trajectory.py`; one paid C2 smoke is recorded in `docs/experiment/SCREENING_RUN_STATUS.md`
- Rationale: Need a single command per `(condition, problem, replicate)`.
- Description: Implement `run_trajectory.py` to prepare workspace, render prompts, call SCBench runner, run visible acceptance for C2, run hidden eval, verify locks, and collect artifacts.
- Dependencies: EXP-031, EXP-061, EXP-070
- Acceptance criteria: dry run, mocked runner, and native smoke produce expected artifact trees and JSONL rows.
- Complexity: XL
- Implementation notes: Start with MVP; keep SCBench native outputs intact. Native smoke success is pipeline evidence only, not reduced-drift evidence.
- Risks/unknowns: integrating per-checkpoint hooks may require runner changes.

### EXP-072 - Add Pilot Subset Scripts

- Phase: Runner integration
- Status: completed for dry-run subsets in `experiment/scripts/run_pilot_subset.py`
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
- Status: completed in `experiment/scripts/export_results.py`
- Rationale: Analysis should consume normalized tables.
- Description: Implement `export_results.py` to parse native SCBench output and emit `runs.jsonl`, `checkpoints.jsonl`, and `technical_metrics.jsonl`.
- Dependencies: EXP-071, EXP-012
- Acceptance criteria: exported rows validate against the normalized required-field contract and export wrapper dry-runs plus partial native SCBench run directories.
- Complexity: L
- Implementation notes: Preserves links to native artifacts and writes `runs.jsonl`, `checkpoints.jsonl`, `technical_metrics.jsonl`, `artifacts.jsonl`, and `export_summary.json`.
- Risks/unknowns: missing metric files for failed checkpoints.

### EXP-081 - Compute Drift Metrics

- Phase: Metrics extraction
- Status: completed in `experiment/scripts/analyze_results.py`
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
- Status: completed as dry-run/preflight in `docs/experiment/MVP_DRY_RUN_REPORT.md`; native paid smoke completed for one C2 checkpoint and remains non-evidence
- Rationale: Validate the whole pipeline before spending on full pilot.
- Description: Run 2 problems, C0 vs C2, 1 replicate, 1 model/harness.
- Dependencies: EXP-041, EXP-051, EXP-071, EXP-080
- Acceptance criteria: 4 dry-run trajectories prepare successfully or fail with classified reasons; exports and report are generated; a single native smoke can run end-to-end. Evidence-producing interpretation remains blocked until paired counterfactuals, minimum checkpoint depth, and C2 coverage gates pass.
- Complexity: L
- Implementation notes: Do not interpret results as evidence beyond pipeline validation.
- Risks/unknowns: agent cost/API availability.

### EXP-091 - Fix Pipeline Issues From MVP

- Phase: Pilot dry run
- Status: completed for dry-run/preflight and native smoke fixes; evidence-producing run gaps are tracked under EXP-100A through EXP-100E.
- Rationale: MVP should surface prompt, lock, harness, and export bugs.
- Description: Triage failures, patch harness/wrapper/export code, and rerun MVP if needed.
- Dependencies: EXP-090
- Acceptance criteria: MVP dry-run can be reproduced from clean checkout; native smoke can run from frozen artifacts; remaining evidence blockers are recorded before larger costly runs.
- Complexity: M
- Implementation notes: Record all changes in reproducibility/deviation logs.
- Risks/unknowns: fixing harness after seeing outcomes can bias full pilot; freeze before full run.

## Milestone 11 - Full Pilot Run

### EXP-100 - Freeze Pilot Artifacts

- Phase: Full pilot run
- Status: completed as pre-execution freeze in `experiment/locks/pilot_artifact_freeze.json`
- Rationale: Features, steps, prompts, and schemas must be fixed before data collection.
- Description: Tag or commit the experiment artifacts and write hashes to reproducibility docs.
- Dependencies: EXP-091, EXP-042
- Acceptance criteria: immutable experiment commit selected, artifact freeze manifest written, and freeze verifier passes.
- Complexity: S
- Implementation notes: No feature/step/prompt/schema/script edits after freeze except documented invalidation and a regenerated freeze manifest.
- Risks/unknowns: late-discovered harness bugs.

### EXP-100A - Define Reduced-Drift Evidence Gate

- Phase: Full pilot run
- Status: completed in `experiment/scripts/validate_full_pilot_preflight.py`; now intentionally blocks `--profile mini_screen` until C2 executed-feedback enforcement is implemented
- Rationale: A successful pipeline smoke is not evidence of reduced drift without matched counterfactual trajectories and enough checkpoint depth.
- Description: Add an explicit preflight gate that marks a configured run as evidence-producing only when it includes matched C0 and C2 trajectories, or matched C0/C1/C2 trajectories, for the same problems, checkpoint prefix, replicate IDs, model, and agent harness; includes at least 3 checkpoints per selected problem; has no C2 acceptance coverage gaps for included checkpoints; and has mandatory C2 executed acceptance feedback audited or harness-enforced before checkpoint completion.
- Dependencies: EXP-100
- Acceptance criteria: preflight output reports `evidence_gate.ready` and structured blockers for missing counterfactuals, insufficient checkpoint depth, incomplete C2 coverage, missing C2 executed-feedback enforcement, model/harness mismatches, and incomplete lock snapshots.
- Complexity: M
- Implementation notes: This gate should support both the mini-screen and full screening profiles. Any report using data that fails this gate must be labeled pipeline-only or smoke-only.
- Risks/unknowns: A 3-checkpoint prefix can show directional regression/survival behavior, but still does not represent the full long-horizon benchmark.

### EXP-100B - Complete C2 Acceptance Coverage For Mini-Screen

- Phase: Full pilot run
- Status: completed for `code_search` and `file_backup` checkpoints 1-3 in `experiment/steps/acceptance/standalone_runner.py`
- Rationale: C2 cannot be compared against C0 unless every included checkpoint has locked, maintainer-authored visible acceptance scenarios and steps.
- Description: Author and lock C2 feature and step coverage for a reduced-drift mini-screen, initially `code_search` and `file_backup` through checkpoint 3 unless problem inspection recommends replacing one. Keep the implementation agent forbidden from modifying `.feature`, step, harness, scoring, prompt-template, schema, and lock files.
- Dependencies: EXP-051, EXP-052, EXP-100A
- Acceptance criteria: standalone acceptance runner reports scenario coverage for every included C2 problem/checkpoint slot; reference-solution or snapshot smoke passes; preflight coverage gate passes for the mini-screen profile; updated freeze manifest includes the new locked files.
- Complexity: L
- Implementation notes: Prefer observable CLI/file behavior and reuse step wording across checkpoints. Record any enriched examples that go beyond original prose in the Gherkin conversion notes.
- Risks/unknowns: Coverage expansion can accidentally add information beyond the original checkpoint spec; mitigate by labeling parity versus enriched examples.

### EXP-100C - Add Paired Mini-Screen Run Matrix

- Phase: Full pilot run
- Status: completed in `experiment/configs/mini_screen_c0.yaml` and `experiment/configs/mini_screen_c2.yaml`
- Rationale: Reduced-drift tendency requires paired trajectories, not isolated condition results.
- Description: Add a mini-screen config for `code_search` and `file_backup`, checkpoints 1-3, C0 vs C2 at minimum, optionally C0/C1/C2 if cost allows, one replicate, one model, one agent harness. The config must use identical problem/checkpoint prefixes and replicate IDs across conditions.
- Dependencies: EXP-031, EXP-100A, EXP-100B
- Acceptance criteria: config validation and preflight pass the reduced-drift evidence gate; generated run plan lists matched condition pairs per problem/checkpoint prefix; randomized execution order is recorded.
- Complexity: M
- Implementation notes: Keep this separate from the 5-6 problem full screening profile so the first evidence-producing run is affordable and easy to inspect.
- Risks/unknowns: One replicate is only directional; do not use significance language.

### EXP-100D - Run Paired Reduced-Drift Probe

- Phase: Full pilot run
- Status: completed in `experiment/runs/reduced_drift_probe/` with normalized exports in `experiment/results/reduced_drift_probe/`; retrospective classification is directional/pipeline-only for C2 because agent-side acceptance execution was not audited as mandatory feedback
- Rationale: The first interpretable signal should compare C0 and C2 on the same problem trajectories and checkpoint depth.
- Description: Execute the mini-screen matrix after EXP-100A through EXP-100C pass. Collect native SCBench hidden-test outcomes, visible acceptance outcomes for C2, lock verification, artifacts, prompts, cost, token, latency, turn, command, and test-run counts.
- Dependencies: EXP-100C, EXP-071, EXP-080
- Acceptance criteria: all configured paired trajectories have completed, failed, or invalid status; exports contain checkpoint-level rows for each condition/problem/checkpoint/replicate; invalid runs are classified separately from behavioral failures.
- Complexity: L
- Implementation notes: Stop and document if lock violations, missing hidden tests, or harness errors appear. Do not patch acceptance files after seeing condition outcomes without invalidating and rerunning affected trajectories.
- Risks/unknowns: Codex subscription limits, transient agent/tool failures, and local environment variance may reduce usable pairs.

### EXP-100E - Report Directional Reduced-Drift Signal

- Phase: Full pilot run
- Status: completed in `experiment/results/reduced_drift_probe/report/reduced_drift_report.md`; report must be read with the added limitation that C2 execution feedback was not yet audited/enforced
- Rationale: The first useful report should answer whether there is a directional tendency worth scaling, while avoiding proof claims.
- Description: Generate a reduced-drift mini-screen report with paired strict survival, regression rate, hidden failure after visible pass, checkpoint pass/fail matrix, technical drift slopes where available, and cost/runtime metrics. Label the report as directional and underpowered.
- Dependencies: EXP-100D, EXP-081, EXP-110
- Acceptance criteria: report includes paired C0 vs C2 tables by problem and checkpoint; identifies whether C2 improved, matched, or worsened survival/regression on each pair; lists missing or invalid data; states that no causal claim is supported by the mini-screen alone.
- Complexity: M
- Implementation notes: If C1 is included, report C0 vs C1 and C1 vs C2 separately to preserve the spec-format versus executable-harness distinction.
- Risks/unknowns: Technical-drift metrics may be noisy over only 3 checkpoints; keep them secondary to functional/spec drift.

### EXP-100F - Enforce Executed C2 Acceptance Feedback

- Phase: Full pilot run
- Status: implemented with a harness-mediated repair loop for future native C2 runs; existing reduced-drift probe artifacts remain directional because they were collected before this gate
- Rationale: The C2 thesis is about an executable spec workflow that is actually executed and used for repair. A harness that is merely present, or only rerun by the scorer after checkpoint completion, cannot prevent drift during implementation.
- Description: Implement mandatory C2 acceptance execution before checkpoint completion. Choose one enforcement path and pre-register it: transcript-audited agent execution, where the agent must run the visible command and the runner parses artifacts/transcripts to confirm execution after the final product-code change; or a harness-mediated repair loop, where the experiment runner runs visible acceptance after the agent draft, feeds visible failures back for repair, and reruns before closing the checkpoint. Preserve post-hoc scorer reruns as measurement, not the intervention.
- Dependencies: EXP-071, EXP-080, EXP-100A, EXP-100B
- Acceptance criteria: C2 prompt requires visible acceptance execution after material code changes and after the final product-code change; native C2 runs set a harness-mediated acceptance gate before hidden scoring; result rows record `acceptance_feedback_observed`, execution count, gate mode, and gate pass/fail; missing execution is classified as `c2_feedback_not_observed` or protocol-invalid; preflight `c2.acceptance_feedback_enforcement` passes only when audit or harness enforcement is configured; rerun mini-screen artifacts show the C2 feedback gate passing.
- Complexity: XL
- Implementation notes: Implemented through the native checkpoint loop using `SPECCOMMONS_ACCEPTANCE_GATE=1`. The runner executes `.scbench_acceptance/runner.py` after the draft, records `acceptance_gate/summary.json`, feeds visible failures back for one repair attempt, and still preserves scorer-side visible acceptance reruns as measurement. Future checkpoint scenario staging still needs inspection before scale-up.
- Risks/unknowns: Native SCBench may not expose enough transcript detail to prove command timing; a repair loop can change comparability with the original benchmark if not carefully documented.

### EXP-101 - Run Full Pilot Matrix

- Phase: Full pilot run
- Status: blocked by screening preflight in `experiment/results/screening_preflight/preflight.json`; current C2 coverage exists for 6 of 19 selected checkpoint slots and C2 executed-feedback enforcement is not implemented
- Rationale: Collect paired C0/C1/C2 trajectories.
- Description: Run selected problems across C0/C1/C2 and 3 replicates if budget allows.
- Dependencies: EXP-100A, EXP-100B, EXP-100C, EXP-100D, EXP-100E, EXP-100F
- Acceptance criteria: all configured trajectories have completed/failed/invalid status and artifacts once C2 acceptance coverage, paired-run, minimum checkpoint-depth, fixed model/agent config, and lock gates pass.
- Complexity: XL
- Implementation notes: Randomize condition order by replicate. Do not scale to the 5-6 problem matrix until the reduced-drift mini-screen has produced a complete paired dataset.
- Risks/unknowns: cost/runtime may require partial matrix.

## Milestone 12 - Analysis And Reporting

### EXP-110 - Generate Pilot Report

- Phase: Analysis/reporting
- Status: completed as pre-evidence report scaffold in `experiment/results/m12_pilot_report/`
- Rationale: Results need transparent interpretation and limitations.
- Description: Produce report with inspected setup, run matrix, pass/fail matrix, survival, regressions, hidden-after-visible failures, quality slopes, and cost metrics.
- Dependencies: EXP-101, EXP-081
- Acceptance criteria: report clearly states no causal proof; includes data and scripts. Current output is explicitly marked `not_tested` because EXP-101 remains blocked.
- Complexity: L
- Implementation notes: Include per-problem paired plots and tables.
- Risks/unknowns: small samples may be noisy.

### EXP-111 - Archive Artifacts

- Phase: Analysis/reporting
- Status: completed as pre-evidence archive scaffold in `experiment/results/m12_archive/`
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
