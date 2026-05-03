# Meaningful Mini-Screen Interpretation

Generated after the first bounded C0/C1/C2 mini-screen over `code_search` and `file_backup`, checkpoints 1-3, three matched replicates per condition.

## Bottom line

This mini-screen does not show a reduced-drift benefit for C1 or C2. It is more useful as a protocol validation and blind-spot diagnostic than as positive evidence for the research claim.

## Functional survival

| problem | condition | replicates | mean strict survival index | hidden checkpoint pass rate |
| --- | --- | --- | --- | --- |
| code_search | C0 | 3 | 2.0 | 0.6667 |
| code_search | C1 | 3 | 2.0 | 0.6667 |
| code_search | C2 | 3 | 2.0 | 0.6667 |
| file_backup | C0 | 3 | 0.0 | 0.0 |
| file_backup | C1 | 3 | 0.0 | 0.0 |
| file_backup | C2 | 3 | 0.0 | 0.0 |

For `code_search`, all conditions passed checkpoints 1 and 2 and failed checkpoint 3 in all three replicates. For `file_backup`, all conditions failed checkpoint 1 in all three replicates.

## C2 execution check

C2 behaved as an executable-spec intervention, not just as passive context:

- `code_search`: 9 of 9 C2 checkpoint rows have `c2_feedback_status=observed`.
- `file_backup`: 3 of 3 evaluated C2 checkpoint rows have `c2_feedback_status=observed`.
- All evaluated C2 visible acceptance checks passed.

## Main diagnostic finding

Every evaluated C2 failure was a hidden failure after visible acceptance passed:

- `code_search`: 3 hidden-failure-after-visible-pass cases, all at checkpoint 3.
- `file_backup`: 3 hidden-failure-after-visible-pass cases, all at checkpoint 1.

This indicates the current visible acceptance suite is not aligned strongly enough with the hidden benchmark checks for these selected failure modes. The next protocol work should focus on acceptance coverage audits before scaling the experiment.

## Interpretation constraints

This is still a small, bounded screen: two problems, one model/agent harness, three replicates, and early stopping after hidden-test failures. It should not be used to claim that executable specs do or do not reduce drift in general.

