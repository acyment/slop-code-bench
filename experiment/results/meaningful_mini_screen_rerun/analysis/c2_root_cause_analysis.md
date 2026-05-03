# C2 Root-Cause Analysis After EXP-100R

Generated: 2026-05-03

## Question

Why did C2 not show better strict-survival performance after the executable acceptance harness was strengthened and rerun?

## Short Answer

C2 did not improve strict survival because the visible acceptance suite passed on the first attempt for every C2 checkpoint. That means the executable harness ran, but it produced no failing feedback for the agent to repair against. The suite was still too weak or misaligned at the exact failure points.

There are two distinct causes:

- `code_search`: C2 substantially improved hidden subtest pass rate at checkpoint 3, but strict survival remained zero because a few pattern-matching semantics were still not covered tightly enough by visible acceptance.
- `file_backup`: the problem is not useful for drift measurement yet. Every condition fails checkpoint 1, and the visible C2 suite allowed a parser that handles the hand-written Gherkin YAML examples but fails benchmark-style valid YAML fixtures.

## Evidence Summary

All 12 C2 acceptance gates passed on their first attempt:

| problem | C2 checkpoint rows | acceptance passed | repair attempts used | hidden failures after visible pass |
| --- | ---: | ---: | ---: | ---: |
| code_search | 9 | 9 | 0 | 3 |
| file_backup | 3 | 3 | 0 | 3 |
| total | 12 | 12 | 0 | 6 |

So C2 was executed, but the executable harness did not create a corrective signal in this rerun.

## `code_search` Diagnosis

Strict survival says C0 and C2 both failed checkpoint 3, but subtest pass rates show a different pattern:

| condition | checkpoint 3 rows | hidden-passed rows | mean strict pass rate | mean passed tests |
| --- | ---: | ---: | ---: | ---: |
| C0 | 3 | 0 | 0.589 | 27.7 / 47 |
| C1 | 2 | 0 | 0.894 | 42.0 / 47 |
| C2 | 3 | 0 | 0.943 | 44.3 / 47 |

C2 appears directionally better than C0 on `code_search` hidden subtests, but the strict trajectory metric only counts all-hidden-tests-passing checkpoints. A single hidden failure keeps strict survival at checkpoint 2.

Remaining C2 checkpoint 3 failure clusters:

| replicate | failed hidden test clusters | likely root cause |
| --- | --- | --- |
| r01 | optional metavariable | Visible acceptance allowed a no-capture optional match to include an empty `captures` object; hidden scoring expects exact JSON shape with no `captures` key when nothing is captured. |
| r02 | optional metavariable; special characters in captures | Same no-capture JSON-shape gap plus insufficient visible coverage for JavaScript string/backtick capture boundaries. |
| r03 | simple Python/C++ patterns; multiline C++; list comprehensions; special characters | Pattern matcher remained under-generalized. Visible examples did not require enough repeated/simple-expression/multiline/list-comprehension cases to force a robust matcher. |

Interpretation:

- This is not a total C2 failure. For `code_search`, C2 moved many hidden subtests in the right direction.
- The visible acceptance scenarios still underspecified exact JSON schema and breadth of pattern semantics.
- Strict survival is too coarse to show near-miss improvement. We should continue reporting strict survival, but add a near-miss metric for hidden subtest pass-rate deltas at failed checkpoints.

## `file_backup` Diagnosis

All conditions fail `file_backup` checkpoint 1, so this problem currently contributes no long-horizon drift information.

Mean checkpoint 1 hidden subtest pass rate:

| condition | hidden-passed rows | mean strict pass rate | mean passed tests |
| --- | ---: | ---: | ---: |
| C0 | 0 / 3 | 0.281 | 9.0 / 32 |
| C1 | 0 / 3 | 0.115 | 3.7 / 32 |
| C2 | 0 / 3 | 0.104 | 3.3 / 32 |

The main C2 failure mode is a brittle custom YAML parser:

- The visible Gherkin and runner scenarios use hand-written YAML examples with nested lists indented under `jobs:`.
- Benchmark fixtures materialize valid YAML in a different shape, including top-level sequence entries not indented under the parent mapping key.
- The C2 parser handles the visible examples but returns failure for the benchmark fixture shape before producing any events.
- The broad `except Exception: return 1` in the generated product code makes these parser failures look like empty-output command failures.

There is also a harness-fidelity issue to fix:

- Hidden evaluation invokes the benchmark entrypoint (`uv run backup_scheduler.py`).
- Visible acceptance invokes the product script through the experiment runner's Python interpreter.
- Current reproduction shows the benchmark fixture shape fails under both invocation styles, so the parser gap is the immediate cause here.
- Still, the visible harness should use the same entrypoint form as hidden evaluation wherever possible, because interpreter/entrypoint drift can otherwise become an unmeasured confound.

Interpretation:

- `file_backup` is currently a bad drift-measurement problem for this mini-screen. It fails at checkpoint 1 across all conditions.
- C2 may be worse than C0 here because the added Gherkin examples encouraged a bespoke parser that overfit to the visible examples rather than relying on a robust YAML parser.
- Before using `file_backup` in a reduced-drift comparison, the visible acceptance suite must include legal YAML formatting variants representative of benchmark fixture materialization, or the problem should be replaced/down-ranked.

## Cross-Cutting Causes

1. **The executable harness did not fail.**
   C2 acceptance passed first attempt in all 12 C2 checkpoint rows. Execution alone cannot help if the visible tests do not reject the flawed implementation.

2. **Visible examples still underspecified exact output contracts.**
   `code_search` shows this clearly: empty optional captures and exact capture boundaries are observable behavior, but not enforced tightly enough.

3. **Strict survival hides near-miss improvements.**
   C2 improved `code_search` checkpoint 3 subtest pass rate relative to C0, but strict survival remained unchanged because all three C2 rows still had at least one hidden failure.

4. **One selected problem is unsuitable in its current state.**
   `file_backup` fails checkpoint 1 for C0/C1/C2. It is measuring first-checkpoint task difficulty and fixture/harness mismatch, not long-horizon drift.

5. **The visible runner is not yet fully benchmark-entrypoint-equivalent.**
   This was not the immediate cause of the `file_backup` hidden failures reproduced here, but it is a protocol risk and should be fixed before another meaningful run.

## Recommended Fixes Before Another Mini-Screen

1. Align C2 visible acceptance invocation with the benchmark entrypoint form, or explicitly record why a problem requires a different command.
2. Add a visible acceptance smoke that uses benchmark-style fixture materialization for `file_backup`, including valid YAML shapes generated by `yaml.safe_dump`.
3. Tighten `code_search` checkpoint 3 visible assertions:
   - no `captures` key when an optional metavariable captures nothing,
   - multiple present optional captures, not just one,
   - JavaScript string/backtick capture boundaries,
   - simple numeric/expression captures in Python and C++,
   - list-comprehension patterns,
   - multiline C++ block patterns.
4. Add a near-miss analysis table for failed checkpoints: hidden subtest pass rate, failed cluster count, and failed cluster labels by condition.
5. Reconsider `file_backup` for the first representative subset unless checkpoint 1 can be made useful. If it remains all-condition-fail at checkpoint 1 after harness-fidelity fixes, replace it with a problem that reaches at least 2-3 checkpoints under C0.

## Current Interpretation For The Thesis

EXP-100R should not be read as evidence against executable specs. It shows that the current C2 intervention is not strong enough yet:

- For `code_search`, C2 looks directionally useful on hidden subtest coverage but misses strict success.
- For `file_backup`, the visible examples were not representative enough and may have promoted overfitting.
- The next run should happen only after the visible harness can fail the current flawed C2 snapshots for the right reasons.
