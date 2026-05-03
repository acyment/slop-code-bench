# SpecCommons SCBench Gherkin Drift Pilot Report

Generated at: `2026-05-03T14:47:49.861115Z`
Report status: `pre_evidence_blocked`
Freeze hash: `6b523b863cc816ed671ba717f531684915f58f3d05b747aaedc70d23b298964e`

## Bottom Line

No causal or directional research conclusion can be drawn from the current artifacts. The available data are dry-run and preflight outputs only: no implementation agent trajectory, visible acceptance execution against agent snapshots, hidden SCBench evaluation, cost trace, or technical drift measurement has run.

What is complete is the reporting pipeline: normalized exports can be summarized, blocked readiness is explicit, and the archive manifest can preserve the current pre-evidence state.

## Current Data

- Normalized runs: `4`
- Normalized checkpoints: `18`
- Evaluable checkpoints: `0`
- Visible acceptance checkpoint results: `0`
- Dry-run checkpoints: `18`

## Full Pilot Gate

- Preflight status: `blocked`
- Planned trajectories: `54`
- Planned checkpoint executions: `261`

| id | status | message |
| --- | --- | --- |
| pilot_c0.model_agent_selected | block | Model/provider and agent harness/version still contain TBD placeholders. |
| pilot_c1.model_agent_selected | block | Model/provider and agent harness/version still contain TBD placeholders. |
| pilot_c2.model_agent_selected | block | Model/provider and agent harness/version still contain TBD placeholders. |
| trajectory.execution_bridge | block | run_trajectory.py is still dry-run only. |
| c2.acceptance_snapshot_bridge | block | C2 acceptance command still points at the smoke/reference runner, not agent checkpoint snapshots. |

## Functional Drift Metrics

Strict survival, regression rate, and hidden-failure-after-visible-pass metrics are implemented in the analysis summary, but the current values are not evidence-bearing because all checkpoints are dry-run/not evaluated.

### Trajectory Summary

| condition_id | problem_id | replicate_id | status | strict_survival_index | checkpoint_count_expected | hidden_checkpoint_pass_rate | regression_rate | hidden_failure_after_visible_pass_count | not_evaluated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C0 | code_search | 1 | dry_run_prepared | 0 | 5 |  |  | 0 | True |
| C2 | code_search | 1 | dry_run_prepared | 0 | 5 |  |  | 0 | True |
| C0 | file_backup | 1 | dry_run_prepared | 0 | 4 |  |  | 0 | True |
| C2 | file_backup | 1 | dry_run_prepared | 0 | 4 |  |  | 0 | True |

### Pass Matrix

| condition | problem | replicate | checkpoint | visible | hidden | regressions | lock | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C0 | code_search | 1 | checkpoint_1 | n/a | n/a |  | not_applicable | dry_run_prepared |
| C0 | code_search | 1 | checkpoint_2 | n/a | n/a |  | not_applicable | dry_run_prepared |
| C0 | code_search | 1 | checkpoint_3 | n/a | n/a |  | not_applicable | dry_run_prepared |
| C0 | code_search | 1 | checkpoint_4 | n/a | n/a |  | not_applicable | dry_run_prepared |
| C0 | code_search | 1 | checkpoint_5 | n/a | n/a |  | not_applicable | dry_run_prepared |
| C0 | file_backup | 1 | checkpoint_1 | n/a | n/a |  | not_applicable | dry_run_prepared |
| C0 | file_backup | 1 | checkpoint_2 | n/a | n/a |  | not_applicable | dry_run_prepared |
| C0 | file_backup | 1 | checkpoint_3 | n/a | n/a |  | not_applicable | dry_run_prepared |
| C0 | file_backup | 1 | checkpoint_4 | n/a | n/a |  | not_applicable | dry_run_prepared |
| C2 | code_search | 1 | checkpoint_1 | n/a | n/a |  | unchanged | dry_run_prepared |
| C2 | code_search | 1 | checkpoint_2 | n/a | n/a |  | unchanged | dry_run_prepared |
| C2 | code_search | 1 | checkpoint_3 | n/a | n/a |  | unchanged | dry_run_prepared |
| C2 | code_search | 1 | checkpoint_4 | n/a | n/a |  | unchanged | dry_run_prepared |
| C2 | code_search | 1 | checkpoint_5 | n/a | n/a |  | unchanged | dry_run_prepared |
| C2 | file_backup | 1 | checkpoint_1 | n/a | n/a |  | unchanged | dry_run_prepared |
| C2 | file_backup | 1 | checkpoint_2 | n/a | n/a |  | unchanged | dry_run_prepared |
| C2 | file_backup | 1 | checkpoint_3 | n/a | n/a |  | unchanged | dry_run_prepared |
| C2 | file_backup | 1 | checkpoint_4 | n/a | n/a |  | unchanged | dry_run_prepared |

### Condition And Problem Summary

| condition_id | problem_id | run_count | mean_strict_survival_index | mean_hidden_checkpoint_pass_rate | mean_regression_rate | not_evaluated_run_count |
| --- | --- | --- | --- | --- | --- | --- |
| C0 | code_search | 1 | 0 |  |  | 1 |
| C0 | file_backup | 1 | 0 |  |  | 1 |
| C2 | code_search | 1 | 0 |  |  | 1 |
| C2 | file_backup | 1 | 0 |  |  | 1 |

## Technical Drift Metrics

Technical slope extraction is wired, but no slope is meaningful yet because no agent-produced checkpoint snapshots or static metric files were evaluated.

| condition | problem | replicate | loc_points | verbosity_points | erosion_points | hidden_eval_runtime_points |
| --- | --- | --- | --- | --- | --- | --- |
| C0 | code_search | 1 | 0 | 0 | 0 | 0 |
| C2 | code_search | 1 | 0 | 0 | 0 | 0 |
| C0 | file_backup | 1 | 0 | 0 | 0 | 0 |
| C2 | file_backup | 1 | 0 | 0 | 0 | 0 |

## Cost Metrics

- Cost data available: `False`
- Reason: no implementation-agent run has executed in the current artifacts.

## Reproducibility Artifacts

- Freeze manifest: `experiment/locks/pilot_artifact_freeze.json`
- M10 normalized export: `experiment/results/m10_mvp_dry_run/export/`
- M10 analysis: `experiment/results/m10_mvp_dry_run/analysis/`
- M11 preflight: `experiment/results/m11_full_pilot_preflight/`
- M12 report summary: `experiment/results/m12_pilot_report/report_summary.json`

## Limitations

- The C0/C1/C2 comparison has not run.
- Hidden SCBench tests have not judged any agent-produced code.
- Visible Gherkin acceptance has not run against agent checkpoint snapshots.
- Model, provider, agent harness, and version are still placeholders in pilot configs.
- The current report validates analysis/reporting mechanics only.

## Required Next Step

Implement the native execution bridge and C2 snapshot acceptance integration, select the fixed model/agent settings, regenerate the freeze manifest, rerun preflight until it is `ready`, and only then run the primary full-pilot matrix.
