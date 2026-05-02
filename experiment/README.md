# SCBench Gherkin Drift Pilot Experiment Workspace

This directory contains additive experiment infrastructure for the SpecCommons SCBench Gherkin drift pilot.

Current setup status:

- `EXP-002`: fork setup is complete under `acyment`.
- `EXP-003`: local experiment directory skeleton is present.
- `EXP-004`: reproducibility document is present.
- `EXP-010`-`EXP-012`: native SCBench architecture, hidden-test staging, and metric fields are documented.
- `EXP-020`-`EXP-022`: problem inventory, reference-runtime probes, and first pilot selection are present.
- `EXP-030`-`EXP-031`: condition definitions are frozen and run-matrix configs validate.

The experiment is designed to wrap SCBench rather than modify benchmark internals. Keep runner, problem, scoring, and hidden-test behavior pinned and documented.

## Directory Layout

```text
experiment/
  configs/      # MVP and pilot run configs
  prompts/      # condition prompt templates
  features/     # Gherkin feature files by problem/checkpoint
  steps/        # maintainer-authored locked step definitions
  locks/        # protected-file lock manifests
  runs/         # run workspaces and raw artifacts, normally ignored
  results/      # normalized JSONL/SQLite-ready outputs
  scripts/      # orchestration, scoring, export, analysis
  schemas/      # JSON schemas for exported records
```

## Next Setup Step

Continue with Milestone 5, starting at `EXP-040`.
