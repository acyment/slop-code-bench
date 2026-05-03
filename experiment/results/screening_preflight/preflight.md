# Full Pilot Preflight

Profile: `screening`
Status: `blocked`
Generated at: `2026-05-03T17:50:05.928356Z`

## Matrix

- Total trajectories: `12`
- Total checkpoint executions: `57`

## Gate Checks

| check | status | message |
| --- | --- | --- |
| pilot_artifacts.freeze_manifest | pass | Freeze manifest matches current files. |
| screening_c0.model_agent_selected | pass | Model and agent are selected. |
| screening_c1.model_agent_selected | pass | Model and agent are selected. |
| screening_c2.model_agent_selected | pass | Model and agent are selected. |
| trajectory.execution_bridge | pass | run_trajectory.py appears to support a non-dry-run execution mode. |
| c2.acceptance_snapshot_bridge | pass | C2 acceptance command points at a workspace-local standalone runner. |
| c2.acceptance_feedback_enforcement | pass | C2 requires executed acceptance feedback and the runner can audit or enforce it. |
| c2.acceptance_coverage | block | C2 visible acceptance coverage is partial: 13 of 19 selected checkpoint slots are missing locked scenarios. |
| reduced_drift.evidence_gate | block | Configured run matrix is not evidence-producing: 1 blocker(s). |

## Reduced-Drift Evidence Gate

- Ready: `False`
- Message: Configured run matrix is not evidence-producing: 1 blocker(s).

| blocker | detail |
| --- | --- |
| incomplete_c2_acceptance_coverage | `{"missing_checkpoint_slots": [{"checkpoint_index": 4, "problem_id": "code_search"}, {"checkpoint_index": 5, "problem_id": "code_search"}, {"checkpoint_index": 4, "problem_id": "file_backup"}, {"checkpoint_index": 1, "problem_id": "migrate_configs"}, {"checkpoint_index": 2, "problem_id": "migrate_configs"}, {"checkpoint_index": 3, "problem_id": "migrate_configs"}, {"checkpoint_index": 4, "problem_id": "migrate_configs"}, {"checkpoint_index": 5, "problem_id": "migrate_configs"}, {"checkpoint_index": 1, "problem_id": "log_query"}, {"checkpoint_index": 2, "problem_id": "log_query"}, {"checkpoint_index": 3, "problem_id": "log_query"}, {"checkpoint_index": 4, "problem_id": "log_query"}, {"checkpoint_index": 5, "problem_id": "log_query"}], "type": "incomplete_c2_acceptance_coverage"}` |

## Interpretation

The full pilot matrix is blocked. Do not run primary data collection until every gate check passes.
