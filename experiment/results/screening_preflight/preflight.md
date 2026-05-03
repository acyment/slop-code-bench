# Full Pilot Preflight

Profile: `screening`
Status: `blocked`
Generated at: `2026-05-03T15:57:13.390337Z`

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
| c2.acceptance_coverage | block | C2 visible acceptance coverage is partial: 17 of 19 selected checkpoint slots are missing locked scenarios. |

## Interpretation

The full pilot matrix is blocked. Do not run primary data collection until every gate check passes.
