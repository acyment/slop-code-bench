# Acceptance Coverage Audit

Status: `block`
Generated at: `2026-05-03T19:59:32.092851Z`
Ledger: `experiment/steps/acceptance/coverage_ledger.yaml`
Runner: `experiment/steps/acceptance/standalone_runner.py`

## Summary

- Feature scenarios: `18`
- Executable scenarios: `10`
- Spec-only scenarios: `5`
- Required missing scenarios: `3`
- Blockers: `3`

## By Problem And Checkpoint

| problem | checkpoint | feature scenarios | executable | spec-only | required missing | blockers |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| code_search | 1 | 3 | 1 | 2 | 0 | 0 |
| code_search | 2 | 3 | 2 | 1 | 0 | 0 |
| code_search | 3 | 3 | 2 | 0 | 1 | 1 |
| file_backup | 1 | 3 | 1 | 0 | 2 | 2 |
| file_backup | 2 | 3 | 3 | 0 | 0 | 0 |
| file_backup | 3 | 3 | 1 | 2 | 0 | 0 |

## Blockers

| problem | checkpoint | scenario | coverage | reason |
| --- | ---: | --- | --- | --- |
| code_search | 3 | Nested expressions bind as a single metavariable value | required | Required before rerunning the mini-screen; EXP-100N found checkpoint 3 hidden failures around capture boundaries and expression matching. |
| file_backup | 1 | Determine whether jobs are due inside the inclusive simulation window | required | Required before rerunning the mini-screen; EXP-100N found checkpoint 1 hidden failures around schedule due windows, weekly/once jobs, defaults, and inclusive boundaries. |
| file_backup | 1 | Disabled jobs emit no job events | required | Required before rerunning the mini-screen; disabled/default-enabled behavior is part of the original checkpoint prose and failed hidden coverage. |

## Omitted Or Pending Scenarios

| problem | checkpoint | scenario | coverage | reason |
| --- | ---: | --- | --- | --- |
| code_search | 1 | Ignore non-Python files and skip files that cannot be decoded | spec_only | The first mini-screen did not show C2 checkpoint 1 hidden failures; keep this as spec-only until the acceptance suite is broadened beyond observed blind spots. |
| code_search | 1 | Reject invalid rule definitions | spec_only | Error-path validation is intentionally deferred; not implicated by the first C2 visible-pass hidden-fail cases. |
| code_search | 2 | Reject a rule that names an unsupported language | spec_only | Error-path validation is intentionally deferred; not implicated by the first C2 visible-pass hidden-fail cases. |
| code_search | 3 | Nested expressions bind as a single metavariable value | required | Required before rerunning the mini-screen; EXP-100N found checkpoint 3 hidden failures around capture boundaries and expression matching. |
| file_backup | 1 | Determine whether jobs are due inside the inclusive simulation window | required | Required before rerunning the mini-screen; EXP-100N found checkpoint 1 hidden failures around schedule due windows, weekly/once jobs, defaults, and inclusive boundaries. |
| file_backup | 1 | Disabled jobs emit no job events | required | Required before rerunning the mini-screen; disabled/default-enabled behavior is part of the original checkpoint prose and failed hidden coverage. |
| file_backup | 3 | First run writes full backups into destination job directories | spec_only | Deferred until file_backup survives checkpoint 1; not evaluated in the first mini-screen because every condition failed checkpoint 1. |
| file_backup | 3 | Pack strategy does not use file-level incremental state | spec_only | Deferred until file_backup survives checkpoint 1; not evaluated in the first mini-screen because every condition failed checkpoint 1. |
