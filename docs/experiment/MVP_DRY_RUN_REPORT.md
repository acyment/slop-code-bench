# MVP Dry Run Report

Status: Milestone 10 preflight completed on 2026-05-03.

This report records a dry-run validation of the MVP pipeline. It is not an evidence-producing experiment run and should not be interpreted as supporting or refuting the research claim.

## Scope

- Problems: `code_search`, `file_backup`
- Conditions: `C0`, `C2`
- Replicates: `1`
- Mode: `dry-run`
- Agent/model execution: not run
- Hidden SCBench scoring: not run
- Visible C2 acceptance against agent snapshots: not run

## Commands

```bash
uv run python experiment/scripts/run_pilot_subset.py \
  --subset mvp \
  --mode dry-run \
  --problems-root ../scb-problems \
  --run-root /tmp/scbench-m10-mvp-dry-run-v2 \
  --replicate-id 1 \
  --run-id-prefix m10dryv2 \
  --summary-jsonl /tmp/scbench-m10-mvp-dry-run-v2/summary.jsonl

uv run python experiment/scripts/export_results.py \
  --input-root /tmp/scbench-m10-mvp-dry-run-v2 \
  --output-dir experiment/results/m10_mvp_dry_run/export

uv run python experiment/scripts/analyze_results.py \
  --results-dir experiment/results/m10_mvp_dry_run/export \
  --output-dir experiment/results/m10_mvp_dry_run/analysis
```

An earlier native C0 attempt created a partial run directory at `experiment/runs/native_mvp/c0_code_search_r01_codex_spark`. It failed before checkpoint execution because Docker access was blocked in the sandbox. That partial run was exported separately with:

```bash
uv run python experiment/scripts/export_results.py \
  --input-run experiment/runs/native_mvp/c0_code_search_r01_codex_spark \
  --output-dir experiment/results/m10_mvp_dry_run/native_partial_export
```

## Results

- Dry-run trajectories prepared: `4`
- Dry-run checkpoint records prepared: `18`
- `code_search`: 5 checkpoints per condition
- `file_backup`: 4 checkpoints per condition
- C2 lock checks: `unchanged` for all prepared checkpoints
- Hidden-test evaluations: `0`
- Visible acceptance executions: `0`
- Evaluable checkpoint outcomes: `0`

Primary artifacts:

- `experiment/results/m10_mvp_dry_run/export/runs.jsonl`
- `experiment/results/m10_mvp_dry_run/export/checkpoints.jsonl`
- `experiment/results/m10_mvp_dry_run/export/technical_metrics.jsonl`
- `experiment/results/m10_mvp_dry_run/export/artifacts.jsonl`
- `experiment/results/m10_mvp_dry_run/analysis/summary.json`
- `experiment/results/m10_mvp_dry_run/analysis/trajectory_summary.md`
- `experiment/results/m10_mvp_dry_run/analysis/pass_matrix.md`

## Interpretation

The dry-run result is structurally healthy: prompt rendering, checkpoint enumeration, C2 protected-file hashing, normalized export, and trajectory analysis all ran end to end for the MVP matrix.

The result is not promising or unpromising as research evidence because no implementation agent, visible acceptance execution against agent-produced code, or hidden SCBench evaluation ran. The analysis intentionally classifies all four trajectories as `not_evaluated`.

## Blockers Before Evidence-Producing MVP

1. Add an execution bridge that feeds rendered C1/C2 prompts into native SCBench agent runs instead of only writing planned commands.
2. Run native SCBench with Docker access outside the sandbox or with approved Docker escalation.
3. Make C2 visible acceptance run against each agent checkpoint snapshot, not just reference-solution smoke fixtures.
4. Preserve hidden SCBench evaluation as the final judge and export the resulting native `evaluation.json` and `quality_analysis/overall_quality.json` files.
5. Freeze feature, step, prompt, export, and scoring files before collecting any primary pilot data.
