# Full Pilot Preflight

Profile: `mini_screen`
Status: `blocked`
Generated at: `2026-05-03T19:59:01.678436Z`

## Matrix

- Total trajectories: `18`
- Total checkpoint executions: `54`

## Gate Checks

| check | status | message |
| --- | --- | --- |
| pilot_artifacts.freeze_manifest | pass | Freeze manifest matches current files. |
| mini_screen_c0.model_agent_selected | pass | Model and agent are selected. |
| mini_screen_c1.model_agent_selected | pass | Model and agent are selected. |
| mini_screen_c2.model_agent_selected | pass | Model and agent are selected. |
| trajectory.execution_bridge | pass | run_trajectory.py appears to support a non-dry-run execution mode. |
| c2.acceptance_snapshot_bridge | pass | C2 acceptance command points at a workspace-local standalone runner. |
| c2.acceptance_feedback_enforcement | pass | C2 requires executed acceptance feedback and the runner can audit or enforce it. |
| c2.acceptance_coverage | pass | C2 visible acceptance coverage exists for every selected checkpoint. |
| c2.feature_runner_coverage | block | C2 feature-to-runner coverage has blockers: 3 required/missing scenario(s) need locked executable coverage. |
| reduced_drift.evidence_gate | block | Configured run matrix is not evidence-producing: 1 blocker(s). |

## Reduced-Drift Evidence Gate

- Ready: `False`
- Message: Configured run matrix is not evidence-producing: 1 blocker(s).

| blocker | detail |
| --- | --- |
| incomplete_c2_feature_runner_coverage | `{"blocker_count": 3, "blockers": [{"checkpoint_index": 3, "coverage": "required", "feature_scenario": "Nested expressions bind as a single metavariable value", "problem_id": "code_search", "reason": "Required before rerunning the mini-screen; EXP-100N found checkpoint 3 hidden failures around capture boundaries and expression matching."}, {"checkpoint_index": 1, "coverage": "required", "feature_scenario": "Determine whether jobs are due inside the inclusive simulation window", "problem_id": "file_backup", "reason": "Required before rerunning the mini-screen; EXP-100N found checkpoint 1 hidden failures around schedule due windows, weekly/once jobs, defaults, and inclusive boundaries."}, {"checkpoint_index": 1, "coverage": "required", "feature_scenario": "Disabled jobs emit no job events", "problem_id": "file_backup", "reason": "Required before rerunning the mini-screen; disabled/default-enabled behavior is part of the original checkpoint prose and failed hidden coverage."}], "invalid_coverage_count": 0, "missing_ledger_count": 0, "required_missing_count": 3, "type": "incomplete_c2_feature_runner_coverage"}` |

## Interpretation

The full pilot matrix is blocked. Do not run primary data collection until every gate check passes.
