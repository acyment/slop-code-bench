# Blind-Spot Inspection After Meaningful Mini-Screen

Inspection target: C2 rows where visible acceptance passed and hidden benchmark tests failed.

## Summary

C2 execution is working: every evaluated C2 checkpoint had harness-mediated feedback observed and visible acceptance passed. The failure mode is acceptance coverage, not harness execution.

The current acceptance runner automates one representative scenario per covered checkpoint. The feature files often contain more behavior than the runner executes, and the original checkpoint prose contains additional edge semantics that are not exercised by the visible runner. This makes the current C2 mini-screen a useful protocol test, but a weak test of the executable-spec thesis.

## `code_search` Checkpoint 3

Observed result:

- C2 visible acceptance passed in all 3 replicates.
- Hidden checkpoint 3 failed in all 3 replicates.
- Strict survival stayed at checkpoint 2, matching C0 and C1.

Failure clusters across C2 replicates:

- Multiple distinct metavariables in the same pattern.
- Optional metavariable behavior.
- Literal dollar escaping with `$$`.
- Multiline Python pattern capture boundaries.
- Language-specific pattern filtering.
- Pattern matches across multiple files with deterministic ordering.
- Captures containing special characters or multiline string syntax.
- Some list-comprehension and whitespace-sensitive capture boundaries.

Coverage diagnosis:

- The Gherkin file includes examples for repeated metavariables and nested expressions, but the runner only executes the first checkpoint 3 scenario.
- The runner does not execute a scenario for nested expression binding.
- The runner does not exercise optional metavariables or literal `$$`, both of which are stated in the original prose.
- The runner checks capture presence and repeated ranges, but it does not assert enough exact capture text/range boundaries to catch over-capturing.

Recommended acceptance additions:

- Automate the existing nested-expression Gherkin scenario.
- Add original-spec-parity visible examples for:
  - two different metavariables in one pattern,
  - optional metavariable absent/present behavior,
  - `$$` literal dollar matching,
  - multiline Python pattern capture boundary,
  - language-specific pattern rules over mixed Python/JavaScript files,
  - deterministic ordering across multiple files.
- Tighten assertions to compare exact `match`, capture `text`, and capture `ranges` for at least one Python and one JavaScript pattern.

## `file_backup` Checkpoint 1

Observed result:

- C2 visible acceptance passed in all 3 replicates.
- Hidden checkpoint 1 failed in all 3 replicates.
- Strict survival stayed at 0, matching C0 and C1.

Primary implementation failure:

- The generated YAML parser accepted the visible schedule shape but crashed on benchmark schedule shapes with block-list syntax. The visible acceptance schedule used inline lists for exclusions; the original prose shows block lists for fields such as `exclude`, `days`, and `tags`.

Failure clusters across C2 replicates:

- Core due daily schedule with block-list YAML.
- Disabled/default-enabled jobs.
- Inclusive duration and exact-boundary scheduling.
- Weekly and once scheduling.
- Timezone/default-timezone behavior.
- Glob operators beyond the visible example: `?`, character classes, `**`, first-pattern-wins, case sensitivity.
- Error handling for malformed schedule YAML.
- Relative mount/source behavior and multiple-job sorting.

Coverage diagnosis:

- The feature file has scenario outlines for due-window behavior and disabled jobs, but the runner currently executes only the event-history scenario.
- The visible event-history scenario does test relative paths, first matching exclusion pattern, job sorting, selected/excluded counts, and stderr cleanliness.
- It does not test block-style YAML lists, weekly/once schedules, default fields, malformed YAML, or the broader glob surface.

Recommended acceptance additions:

- Add a block-style YAML schedule equivalent to the prose schema, including `exclude` as a YAML list.
- Automate the existing due-window scenario outline for daily, weekly, and once jobs.
- Automate the disabled-job scenario already present in the feature file.
- Add representative original-spec-parity examples for:
  - omitted `timezone` defaulting to UTC,
  - omitted `enabled` defaulting to true,
  - inclusive duration boundary,
  - malformed YAML returning a non-zero status,
  - `?`, `[]`, and `**` glob behavior.

## Protocol Implication

The next run should not scale to more problems until C2 has a coverage gate that checks:

- every Gherkin scenario intended for C2 has an executable counterpart, or is explicitly marked as spec-only,
- all original prose semantics have at least one visible parity check or a documented reason for omission,
- visible-pass/hidden-fail cases from this mini-screen have been triaged into acceptable hidden-only coverage versus missing visible acceptance.

