# Full Pilot Preflight

Profile: `pilot`
Status: `blocked`
Generated at: `2026-05-03T17:09:30.089448Z`

## Matrix

- Total trajectories: `54`
- Total checkpoint executions: `261`

## Gate Checks

| check | status | message |
| --- | --- | --- |
| pilot_artifacts.freeze_manifest | pass | Freeze manifest matches current files. |
| pilot_c0.model_agent_selected | block | Model/provider and agent harness/version still contain TBD placeholders. |
| pilot_c1.model_agent_selected | block | Model/provider and agent harness/version still contain TBD placeholders. |
| pilot_c2.model_agent_selected | block | Model/provider and agent harness/version still contain TBD placeholders. |
| trajectory.execution_bridge | pass | run_trajectory.py appears to support a non-dry-run execution mode. |
| c2.acceptance_snapshot_bridge | pass | C2 acceptance command points at a workspace-local standalone runner. |
| c2.acceptance_feedback_enforcement | block | C2 visible acceptance is not yet enforced as implementation-time feedback. |
| c2.acceptance_coverage | block | C2 visible acceptance coverage is partial: 23 of 29 selected checkpoint slots are missing locked scenarios. |
| reduced_drift.evidence_gate | block | Configured run matrix is not evidence-producing: 2 blocker(s). |

## Reduced-Drift Evidence Gate

- Ready: `False`
- Message: Configured run matrix is not evidence-producing: 2 blocker(s).

| blocker | detail |
| --- | --- |
| c2_acceptance_feedback_not_enforced | `{"enforcement": "prompt_only", "matrix_id": "pilot_c2", "required_enforcement": ["agent_transcript_audited", "harness_mediated"], "type": "c2_acceptance_feedback_not_enforced"}` |
| incomplete_c2_acceptance_coverage | `{"missing_checkpoint_slots": [{"checkpoint_index": 4, "problem_id": "code_search"}, {"checkpoint_index": 5, "problem_id": "code_search"}, {"checkpoint_index": 4, "problem_id": "file_backup"}, {"checkpoint_index": 1, "problem_id": "migrate_configs"}, {"checkpoint_index": 2, "problem_id": "migrate_configs"}, {"checkpoint_index": 3, "problem_id": "migrate_configs"}, {"checkpoint_index": 4, "problem_id": "migrate_configs"}, {"checkpoint_index": 5, "problem_id": "migrate_configs"}, {"checkpoint_index": 1, "problem_id": "log_query"}, {"checkpoint_index": 2, "problem_id": "log_query"}, {"checkpoint_index": 3, "problem_id": "log_query"}, {"checkpoint_index": 4, "problem_id": "log_query"}, {"checkpoint_index": 5, "problem_id": "log_query"}, {"checkpoint_index": 1, "problem_id": "file_merger"}, {"checkpoint_index": 2, "problem_id": "file_merger"}, {"checkpoint_index": 3, "problem_id": "file_merger"}, {"checkpoint_index": 4, "problem_id": "file_merger"}, {"checkpoint_index": 1, "problem_id": "textdrop"}, {"checkpoint_index": 2, "problem_id": "textdrop"}, {"checkpoint_index": 3, "problem_id": "textdrop"}, {"checkpoint_index": 4, "problem_id": "textdrop"}, {"checkpoint_index": 5, "problem_id": "textdrop"}, {"checkpoint_index": 6, "problem_id": "textdrop"}], "type": "incomplete_c2_acceptance_coverage"}` |

## Interpretation

The full pilot matrix is blocked. Do not run primary data collection until every gate check passes.
