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

The gate currently blocks primary execution for three reasons:

1. `pilot_c0.yaml`, `pilot_c1.yaml`, and `pilot_c2.yaml` still contain `TBD_*` model and agent placeholders.
2. `run_trajectory.py` is dry-run only and does not yet call native SCBench implementation-agent execution.
3. C2 acceptance still points at the smoke/reference runner instead of running against each agent checkpoint snapshot.

## Required Work Before EXP-101

Before running the full pilot matrix:

1. Select and record the fixed model/provider and agent harness/version in all pilot configs.
2. Implement a native execution bridge that feeds rendered C0/C1/C2 prompts into SCBench checkpoint runs.
3. Run C2 visible acceptance against agent-produced checkpoint snapshots.
4. Preserve native hidden SCBench evaluation as the final judge.
5. Re-run the freeze verifier and full-pilot preflight.

Until those gates pass, Milestone 11 is frozen/preflighted but not evidence-producing.
