# Reduced-Drift Mini-Screen Report

Generated at: `2026-05-03T17:09:34.577902Z`
Status: `blocked_not_evidence`
Claim status: `not_interpretable`

## Bottom Line

This report is directional only. It can indicate whether the paired C0 vs C2 mini-screen pipeline is worth inspecting, but it cannot support a causal research claim. Treat C2 as primary evidence only after visible acceptance execution is audited or harness-enforced as implementation-time feedback.

## Data Shape

- Runs: `4`
- Checkpoints: `8`
- Evaluable checkpoints: `8`

## Paired Trajectories

| problem | replicate | paired | c0_survival | c2_survival | survival_delta_c2_minus_c0 | c0_regression_rate | c2_regression_rate | regression_delta_c2_minus_c0 | c2_hidden_after_visible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| code_search | 1 | True | 2 | 2 | 0 | 0 | 0 | 0 | 1 |
| file_backup | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

## Checkpoint Matrix

| problem | replicate | checkpoint | c0_hidden | c2_hidden | c2_visible | c0_regressions | c2_regressions | c2_hidden_after_visible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| code_search | 1 | checkpoint_1 | pass | pass | pass | 0 | 0 | no |
| code_search | 1 | checkpoint_2 | pass | pass | pass | 0 | 0 | no |
| code_search | 1 | checkpoint_3 | fail | fail | pass | 0 | 0 | yes |
| file_backup | 1 | checkpoint_1 | fail | fail | pass | 0 | 0 | yes |

## Technical Drift Slopes

| condition | problem | replicate | loc_slope | sloc_slope | cc_max_slope | clone_lines_slope | cloned_pct_slope | acceptance_runtime_ms_slope | loc_points |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C0 | code_search | 1 | 209 | 176.5 | 6.5 | 15 | 0.03043 |  | 3 |
| C2 | code_search | 1 | 173.5 | 141.5 | 1.5 | 10 | 0.02137 | 67.25 | 3 |
| C0 | file_backup | 1 |  |  |  |  |  |  | 1 |
| C2 | file_backup | 1 |  |  |  |  |  |  | 1 |

## Cost Summary

| agent_steps | api_cost_usd | checkpoint_rows_with_cost | input_tokens_net | output_tokens_net | reasoning_tokens_net |
| --- | --- | --- | --- | --- | --- |
| 150 | 0.2901 | 8 | 2820654 | 88810 | 42569 |

## Limitations

- One replicate and two problems are underpowered and directional only.
- Visible acceptance tests are an intervention; hidden SCBench tests remain the correctness judge.
- C2 agent-side visible acceptance execution must be audited or harness-enforced as implementation-time feedback; scorer-only post-hoc reruns are measurement, not the intervention.
- Technical drift slopes over three checkpoints are noisy and should be treated as secondary.
- Before scaling, inspect C2 asset staging so future checkpoint scenarios are not exposed early.
