# Acceptance Harness Prototype

Status: selected for the first MVP and C0/C1/C2 pilot prototype.

## Runner Decision

Use a custom parser-to-pytest adapter backed by small Python helper modules.

The prototype does not depend on `behave` or `pytest-bdd` yet. Milestone 6
adds the locked helper layer, result schema, and smoke runner. Milestone 7 can
render C2 prompts with the acceptance command, and Milestone 8 can wire the
harness into trajectory execution.

## Options Compared

| Option | Strengths | Weaknesses | Decision |
| --- | --- | --- | --- |
| `behave` | Mature Gherkin runner; natural step-definition model. | Separate runner lifecycle; JSON output requires adapter work; less aligned with SCBench pytest tooling. | Defer. |
| `pytest-bdd` | Fits pytest ecosystem; reusable fixtures and assertions. | Step matching can become brittle for broad CLI/API phrases; plugin dependency and parser behavior would become part of lock surface. | Defer. |
| Custom parser-to-pytest adapter | Minimal dependency surface; explicit JSONL output; easy to lock step helpers and classify failures. | More in-house code; must implement enough Gherkin parsing/step binding later. | Selected for prototype. |

## Prototype Scope

Implemented now:

- CLI helper functions for command execution, stdout/stderr capture, JSONL
  parsing, exit-code assertions, and workspace file creation.
- API helper functions for free-port allocation, server startup, health polling,
  HTTP requests, teardown, and server log capture.
- Scenario result records emitted as JSONL with SCBench-compatible fields.
- Standalone locked C2 runner coverage for the active mini-screen:
  - `code_search` checkpoints 1-3,
  - `file_backup` checkpoints 1-3 for harness validation only,
  - `migrate_configs` checkpoints 1-3 for the EXP-100Y replacement mini-screen.
- Smoke runner covering:
  - `code_search` checkpoint 1 reference solution,
  - `file_backup` checkpoint 1 reference solution,
  - `textdrop` checkpoint 1 reference solution.

Deferred to Milestone 7/8:

- Full Gherkin parsing and automatic scenario-to-step dispatch.
- Condition prompt rendering that exposes only the C2 acceptance command.
- Per-checkpoint trajectory integration and lock-manifest enforcement.

## Failure Classification

The smoke runner records one JSONL row per scenario with:

- `passed`: helper assertions and product behavior matched expectations.
- `failed` / `scenario_failure`: visible scenario assertion failed.
- `failed` / `product_error`: product command exited unexpectedly or the
  reference service failed to satisfy a visible behavior.
- `error` / `harness_error`: harness setup, server lifecycle, or artifact
  capture failed.

## Smoke Command

Run from the repository root:

```bash
uv run python experiment/scripts/run_acceptance_smoke.py \
  --problems-root ../scb-problems \
  --output-dir /tmp/scbench-acceptance-smoke
```

Validate emitted scenario records:

```bash
uv run python experiment/scripts/validate_scenario_results.py \
  /tmp/scbench-acceptance-smoke/scenarios.jsonl
```
