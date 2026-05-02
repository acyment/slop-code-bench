# Roadmap

## Phase 0 - Planning Package

Status: complete in this directory.

Deliverables:

- source inspection notes,
- experiment design,
- backlog,
- problem selection plan,
- data schema,
- metrics plan,
- prompt templates,
- risk register.

## Phase 1 - Repository Setup

Deliverables:

- forked runner and problem repos,
- experiment branch,
- pinned upstream commits,
- experiment directory,
- reproducibility file,
- lock manifest implementation.

## Phase 2 - MVP Pipeline

Scope:

- `code_search`, `file_backup`,
- C0 vs C2,
- one model/harness,
- one replicate.

Deliverables:

- feature files for two problems,
- maintainer-authored step definitions,
- visible acceptance runner,
- prompt/context generator,
- trajectory wrapper,
- hidden scoring wrapper,
- result JSONL export,
- MVP report.

## Phase 3 - First Pilot

Scope:

- `code_search`, `file_backup`, `migrate_configs`, `log_query`, `file_merger`, and `textdrop`,
- C0/C1/C2,
- one model/harness,
- 3 replicates if budget allows.

Deliverables:

- complete selected feature packages,
- C1/C2 prompt templates,
- acceptance harness coverage report,
- full pass/fail matrix,
- functional drift metrics,
- technical drift slopes,
- cost/runtime summary.

## Phase 4 - C3 Refactoring Cadence

Scope:

- add refactor-only turns after every 2-3 checkpoints.

Deliverables:

- refactor prompt template,
- checkpoint insertion scheduler,
- behavior preservation report,
- comparison of C2 vs C3 slopes and regressions.

## Phase 5 - C4 Risk Probes

Scope:

- rotating prompts for architecture, security, test blind spots, harness performance, dependency creep, and readability.

Deliverables:

- probe templates,
- probe scheduler,
- risk findings schema,
- comparison of C3 vs C4.

## Phase 6 - C5 Agent-Authored Step Automation

Scope:

- allow implementation agent to create missing step definitions.

Deliverables:

- harness-quality rubric,
- tests of generated steps against reference solutions,
- brittleness and overfit analysis,
- performance comparison against maintainer-authored steps.

## Phase 7 - Broader Generalization

Scope:

- more problems,
- second model/harness,
- information-parity Gherkin ablation,
- possibly cross-language tracks if SCBench tooling supports them.

Deliverables:

- expanded study design,
- multi-model report,
- limitations and external-validity analysis.
