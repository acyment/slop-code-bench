# Gherkin Feature Style Guide

This directory contains maintainer-authored Gherkin derived from visible SCBench
checkpoint prose. Do not use hidden tests, fixture assertions, or private
evaluation outputs as conversion input.

## File Layout

- Put features under `experiment/features/<problem_id>/checkpoint_NNN.feature`.
- Use three-digit checkpoint numbers matching SCBench order.
- Keep one checkpoint per feature file.
- Add a conversion entry for every feature file in `CONVERSION_LEDGER.md`.

## Tags

Every feature file starts with problem and checkpoint tags:

```gherkin
@problem_code_search @checkpoint_001
```

Every scenario includes behavior tags:

- `@core`: behavior directly required by the checkpoint.
- `@regression`: prior-checkpoint behavior that must continue to pass.
- `@edge`: boundary, error, or uncommon case.
- `@positive`: successful user path.
- `@negative`: rejected input or error path.
- Optional domain tags such as `@cli`, `@api`, `@file_io`, `@jsonl`,
  `@markdown`, `@storage`, `@sorting`, or `@validation`.

## Scenario Shape

- Write from a user/operator perspective.
- Prefer observable inputs and outputs over implementation details.
- Use concrete examples when the source prose provides them or when they are
  direct instances of an abstract rule.
- Keep step wording stable across problems so step definitions can be reused.
- Prefer `Scenario Outline` with `Examples` for repeated value cases.
- Use tables for compact input/output matrices.
- Use doc strings for file contents, request bodies, stdout/stderr, and JSONL.

Preferred reusable step vocabulary:

```gherkin
Given the command line tool is available
Given the HTTP service is running
And a file named "..." contains:
And a JSON file named "..." contains:
And an NDJSON file named "..." contains:
And a schedule file named "..." contains:
When I run the tool with arguments:
When I submit a request:
Then the exit status is 0
Then stdout is empty
Then stdout is JSON Lines containing exactly:
Then stderr is empty
Then the response status is 200
Then the response body is JSON:
Then the file "..." contains:
Then the directory "..." contains files:
```

## Conversion Rules

- Preserve original checkpoint intent.
- Preserve prior behavior visibly in later checkpoint files where it matters.
- Do not assert hidden-test-only details.
- Do not over-specify internal algorithms unless the checkpoint prose makes the
  algorithm user-observable.
- Distinguish examples copied from prose from examples that instantiate an
  abstract rule.
- Keep generated examples small enough for acceptance tests to run quickly.
- Avoid adding new behavior. If a useful behavior is inferred but not explicit,
  record it as a later-review item in the ledger instead of including it.

## Information Levels

The first pilot uses example-enriched Gherkin:

- Direct examples from visible checkpoint prose are preserved where practical.
- Abstract prose rules may be represented by small concrete examples.
- Added examples must stay inside the original behavioral envelope.

A later ablation should create information-parity Gherkin that rewrites prose
without adding new concrete examples.

