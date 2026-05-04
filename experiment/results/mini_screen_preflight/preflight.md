# Pilot Preflight

Profile: `mini_screen`
Status: `ready`
Generated at: `2026-05-04T01:42:48.079647Z`

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
| problem_selection.evidence_disabled | pass | All configured problems are enabled for evidence-producing drift runs. |
| trajectory.execution_bridge | pass | run_trajectory.py appears to support a non-dry-run execution mode. |
| c2.acceptance_snapshot_bridge | pass | C2 acceptance command points at a workspace-local standalone runner. |
| c2.acceptance_feedback_enforcement | pass | C2 requires executed acceptance feedback and the runner can audit or enforce it. |
| c2.acceptance_coverage | pass | C2 visible acceptance coverage exists for every selected checkpoint. |
| c2.feature_runner_coverage | pass | C2 feature scenarios are mapped to locked executable runner coverage or documented as spec-only. |
| reduced_drift.evidence_gate | pass | Configured run matrix is evidence-producing for a directional reduced-drift probe. |

## Reduced-Drift Evidence Gate

- Ready: `True`
- Message: Configured run matrix is evidence-producing for a directional reduced-drift probe.

## Interpretation

The `mini_screen` matrix is ready to execute.
