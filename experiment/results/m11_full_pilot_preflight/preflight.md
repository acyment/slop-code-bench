# Full Pilot Preflight

Status: `blocked`
Generated at: `2026-05-03T14:41:37.108217Z`

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
| trajectory.execution_bridge | block | run_trajectory.py is still dry-run only. |
| c2.acceptance_snapshot_bridge | block | C2 acceptance command still points at the smoke/reference runner, not agent checkpoint snapshots. |

## Interpretation

The full pilot matrix is blocked. Do not run primary data collection until every gate check passes.
