# Experiment Design

## Research Claim Under Test

Long-horizon coding-agent tasks may drift less when the agent receives structured behavioral examples, especially when those examples are backed by a locked executable acceptance harness.

This pilot is not intended to prove the claim. It is designed to validate a pipeline and produce early paired evidence for:

- functional/spec drift reduction,
- regression reduction,
- hidden-test failure after visible pass,
- possible changes in technical drift slope,
- cost/runtime tradeoffs.

## Conditions

| ID | Name | Intervention |
| --- | --- | --- |
| C0 | Baseline prose | Agent receives original SCBench checkpoint prose using the benchmark's prompt style as closely as possible. |
| C1 | Gherkin spec package | Agent receives derived `.feature` files as context, but no runnable Gherkin acceptance suite. |
| C2 | Gherkin plus executable harness | Agent receives the same `.feature` files and commands for a locked acceptance suite. |

Later conditions:

- `C3`: C2 plus refactor-only turns every 2-3 checkpoints.
- `C4`: C3 plus rotating risk probes.
- `C5`: agent-authored Gherkin step automation.

## Unit Of Analysis

The major unit of analysis is a full problem trajectory: one agent run through all checkpoints for one problem under one condition and one replicate.

Checkpoint-level rows are still recorded for pass/fail matrices, regression counts, cost, runtime, and quality slopes.

## Pilot Shape

- Problems: 5-6 selected SCBench problems.
- Conditions: C0, C1, C2.
- Model/agent harness: one fixed model and agent harness.
- Replicates: 3 per condition if budget allows.
- Total trajectories: 45-54 for 5-6 problems x 3 conditions x 3 replicates.
- Checkpoints: full trajectories for each selected problem.
- Preferred tasks: CLI, file-processing, and small HTTP/API tasks where Gherkin can express observable behavior without UI automation.

## Minimum Viable Pilot

Use this cut before spending on the full pilot:

- Problems: `xjq`, `code_search`.
- Conditions: C0 and C2.
- Model/agent: one fixed model and one fixed harness.
- Replicates: 1.
- Total trajectories: 4.

MVP must keep:

- pinned runner and problem commits,
- prompt generation,
- lock enforcement for C2,
- visible acceptance result capture,
- hidden SCBench scoring,
- static metric extraction,
- JSONL export,
- run artifact manifest.

MVP may skip:

- C1,
- 3x replication,
- statistical tests beyond descriptive comparison,
- enriched reporting dashboard,
- LLM judge metrics,
- C3-C5 prompt interventions,
- broad problem inventory automation if the two MVP problems are manually pinned.

## Comparability Rules

1. Preserve SCBench checkpoint ordering and agent handoff behavior.
2. Do not replace hidden SCBench pytest tests.
3. Treat SCBench hidden evaluation as final correctness judgment.
4. Keep visible Gherkin acceptance checks as intervention diagnostics, not final truth.
5. Use paired comparisons by problem/checkpoint/replicate wherever possible.
6. Run all conditions against the same upstream commits and environment configs.
7. Never let implementation agents edit experiment harness files in C2+.

## Information Levels

The first pilot should use example-enriched Gherkin, because the intervention under study is a practical executable example-spec workflow. Add a later ablation for information-parity Gherkin that rewrites the prose into Gherkin without adding new examples or edge cases.

Record every added example and classify it:

- direct restatement of original prose,
- concrete instance of original abstract rule,
- edge case inferred from original rule,
- new behavior not present in original spec.

The last category should be avoided in the first pilot.

## Randomization And Pairing

- Use stable problem order within each trajectory to preserve SCBench semantics.
- Randomize condition order across replicates to reduce time/model drift confounds.
- Pair replicates by `(problem_id, replicate_id)` across conditions.
- Use unique run IDs containing date, condition, problem, model, agent, and replicate.

## Analysis Plan

Primary descriptive comparisons:

- strict trajectory survival by condition,
- regression rate by condition,
- hidden failure after visible pass for C2,
- checkpoint pass/fail matrix,
- verbosity and erosion slopes over checkpoint index,
- cost/runtime/test-run differences.

Suggested first statistical treatment after data exists:

- paired sign tests or Wilcoxon signed-rank tests for trajectory survival,
- mixed-effects model with random intercepts for problem and replicate if sample size permits,
- slope comparison per trajectory for verbosity/erosion,
- bootstrap confidence intervals over trajectories.

## Decision Log

| Date | Decision | Status | Rationale |
| --- | --- | --- | --- |
| 2026-05-02 | Target current SCBench repos, not only the paper snapshot. | Proposed | Current site/repo have more problems/checkpoints; pin commits for reproducibility. |
| 2026-05-02 | Keep hidden SCBench pytest evaluation as final correctness judge. | Proposed | Preserves comparability with SCBench. |
| 2026-05-02 | Use C0/C1/C2 only in first pilot. | Proposed | Separates spec format effect from executable harness effect. |
| 2026-05-02 | Author C2 step definitions as experiment-maintainer code. | Proposed | Avoids confounding harness generation with implementation quality. |
| 2026-05-02 | Use example-enriched Gherkin first, with an information-parity ablation later. | Proposed | Tests the intended workflow first while recording added information. |
| 2026-05-02 | Expose prior checkpoint feature files to C1/C2 agents. | Proposed | Prior behavior preservation is part of the intended intervention. |
| 2026-05-02 | Treat harness edits in C2+ as invalid run unless caused by benchmark tooling. | Proposed | Lock violation corrupts the condition. |
| 2026-05-02 | Start with one model/harness. | Proposed | Reduces cost and design confounds for pipeline validation. |

## Unresolved Questions

- Which exact fork owner should be used once GitHub credentials and authorization are available?
- Should C2 acceptance tests be run by the agent during implementation, externally after each turn, or both? Proposed: expose commands and allow the agent to run them, while also running scorer-side verification.
- Should C1 use only `.feature` files or also a generated markdown spec package with examples extracted from Gherkin?
- Should locked `.feature` files be visible but read-only, or copied outside the implementation workspace and only rendered into prompt context?
- Should hidden SCBench tests be evaluated after every checkpoint or only at trajectory end? Proposed: every checkpoint, matching SCBench.

