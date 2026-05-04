# Full Pilot Preflight

Profile: `mini_screen`
Status: `blocked`
Generated at: `2026-05-04T01:18:36.195330Z`

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
| problem_selection.evidence_disabled | block | One or more configured problems are currently disabled for evidence-producing drift runs. |
| trajectory.execution_bridge | pass | run_trajectory.py appears to support a non-dry-run execution mode. |
| c2.acceptance_snapshot_bridge | pass | C2 acceptance command points at a workspace-local standalone runner. |
| c2.acceptance_feedback_enforcement | pass | C2 requires executed acceptance feedback and the runner can audit or enforce it. |
| c2.acceptance_coverage | pass | C2 visible acceptance coverage exists for every selected checkpoint. |
| c2.feature_runner_coverage | pass | C2 feature scenarios are mapped to locked executable runner coverage or documented as spec-only. |
| reduced_drift.evidence_gate | block | Configured run matrix is not evidence-producing: 3 blocker(s). |

## Reduced-Drift Evidence Gate

- Ready: `False`
- Message: Configured run matrix is not evidence-producing: 3 blocker(s).

| blocker | detail |
| --- | --- |
| evidence_disabled_problem | `{"condition_id": "C0", "decision_id": "EXP-100X", "matrix_id": "mini_screen_c0", "problem_id": "file_backup", "reason": "All C0/C1/C2 EXP-100R replicates failed checkpoint 1; keep this problem out of evidence-producing drift screens until a post-fix smoke demonstrates multi-checkpoint feasibility.", "status": "harness_validation_only", "type": "evidence_disabled_problem"}` |
| evidence_disabled_problem | `{"condition_id": "C1", "decision_id": "EXP-100X", "matrix_id": "mini_screen_c1", "problem_id": "file_backup", "reason": "All C0/C1/C2 EXP-100R replicates failed checkpoint 1; keep this problem out of evidence-producing drift screens until a post-fix smoke demonstrates multi-checkpoint feasibility.", "status": "harness_validation_only", "type": "evidence_disabled_problem"}` |
| evidence_disabled_problem | `{"condition_id": "C2", "decision_id": "EXP-100X", "matrix_id": "mini_screen_c2", "problem_id": "file_backup", "reason": "All C0/C1/C2 EXP-100R replicates failed checkpoint 1; keep this problem out of evidence-producing drift screens until a post-fix smoke demonstrates multi-checkpoint feasibility.", "status": "harness_validation_only", "type": "evidence_disabled_problem"}` |

## Interpretation

The full pilot matrix is blocked. Do not run primary data collection until every gate check passes.
