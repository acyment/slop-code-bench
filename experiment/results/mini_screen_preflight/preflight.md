# Full Pilot Preflight

Profile: `mini_screen`
Status: `blocked`
Generated at: `2026-05-03T17:09:29.974880Z`

## Matrix

- Total trajectories: `4`
- Total checkpoint executions: `12`

## Gate Checks

| check | status | message |
| --- | --- | --- |
| pilot_artifacts.freeze_manifest | pass | Freeze manifest matches current files. |
| mini_screen_c0.model_agent_selected | pass | Model and agent are selected. |
| mini_screen_c2.model_agent_selected | pass | Model and agent are selected. |
| trajectory.execution_bridge | pass | run_trajectory.py appears to support a non-dry-run execution mode. |
| c2.acceptance_snapshot_bridge | pass | C2 acceptance command points at a workspace-local standalone runner. |
| c2.acceptance_feedback_enforcement | block | C2 visible acceptance is not yet enforced as implementation-time feedback. |
| c2.acceptance_coverage | pass | C2 visible acceptance coverage exists for every selected checkpoint. |
| reduced_drift.evidence_gate | block | Configured run matrix is not evidence-producing: 1 blocker(s). |

## Reduced-Drift Evidence Gate

- Ready: `False`
- Message: Configured run matrix is not evidence-producing: 1 blocker(s).

| blocker | detail |
| --- | --- |
| c2_acceptance_feedback_not_enforced | `{"enforcement": "prompt_only", "matrix_id": "mini_screen_c2", "required_enforcement": ["agent_transcript_audited", "harness_mediated"], "type": "c2_acceptance_feedback_not_enforced"}` |

## Interpretation

The full pilot matrix is blocked. Do not run primary data collection until every gate check passes.
