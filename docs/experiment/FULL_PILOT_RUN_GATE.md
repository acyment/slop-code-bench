# Full Pilot Run Gate

Status: Milestone 11 preflight gate.

The first full pilot matrix is defined, but primary data collection must not run until the gate checks pass. This keeps the project from spending model budget on a run that would not isolate C0/C1/C2 correctly.

## Frozen Artifacts

The pre-execution freeze manifest is:

```text
experiment/locks/pilot_artifact_freeze.json
```

It freezes:

- experiment docs,
- pilot run matrices,
- Gherkin feature files,
- prompt templates,
- locked acceptance helpers,
- experiment scripts,
- result schemas.

Verify the freeze with:

```bash
uv run python experiment/scripts/freeze_pilot_artifacts.py verify \
  --manifest experiment/locks/pilot_artifact_freeze.json
```

Any changed frozen file before primary data collection requires a new manifest and a documented deviation.

## Full Pilot Matrix

The current full pilot matrix covers:

- Conditions: `C0`, `C1`, `C2`
- Problems: `code_search`, `file_backup`, `migrate_configs`, `log_query`, `file_merger`, `textdrop`
- Replicates: `1`, `2`, `3`
- Total trajectories: `54`
- Total checkpoint executions: `261`

## Gate Checks

Run the gate with:

```bash
uv run python experiment/scripts/validate_full_pilot_preflight.py \
  --freeze-manifest experiment/locks/pilot_artifact_freeze.json \
  --problems-root ../scb-problems \
  --output-dir experiment/results/m11_full_pilot_preflight \
  --allow-blocked
```

The gate currently blocks primary execution for these reasons:

1. Representative C2 visible acceptance coverage is incomplete for selected checkpoint slots.
2. C2 visible acceptance is not yet audited or harness-enforced as implementation-time feedback before checkpoint completion.
3. Any freeze mismatch after protocol edits must be resolved before primary execution.

## Required Work Before EXP-101

Before running the full pilot matrix:

1. Implement EXP-100F so C2 requires executed visible acceptance feedback and records whether that feedback was observed by the implementation agent.
2. Complete C2 visible acceptance coverage for selected checkpoints.
3. Preserve native hidden SCBench evaluation as the final judge.
4. Re-run the freeze verifier and full-pilot preflight.

Until those gates pass, Milestone 11 is frozen/preflighted but not evidence-producing.
