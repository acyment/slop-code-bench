# Conditions

## C0 - Baseline Prose

The implementation agent receives the original SCBench checkpoint spec, as close as possible to the benchmark's intended baseline.

Rules:

- Use the upstream `just-solve.jinja` style unless a local runner integration requires minimal wrapping.
- Do not include Gherkin.
- Do not expose hidden pytest tests.
- Do not expose acceptance harness files.
- Preserve SCBench checkpoint order and prior solution handoff.

Primary purpose: baseline comparability.

## C1 - Gherkin Spec Package

The implementation agent receives Gherkin `.feature` files derived from the checkpoint specs.

Rules:

- Include current checkpoint features and prior checkpoint features.
- Provide Gherkin as readable spec context only.
- Do not provide runnable Gherkin commands.
- Do not expose step definitions.
- Do not expose hidden SCBench pytest tests.

Gherkin requirements:

- preserve original checkpoint intent,
- use user/domain language,
- emphasize observable behavior,
- include concrete examples,
- reuse step wording for repeated concepts,
- tag by problem, checkpoint, behavior type, core/regression/edge, positive/negative path,
- avoid implementation internals.

Primary purpose: isolate spec format/example effect.

## C2 - Gherkin Plus Executable Acceptance Harness

The implementation agent receives the same Gherkin plus a runnable acceptance suite backed by locked step definitions.

Rules:

- `.feature` files are read-only/protected.
- step definitions are read-only/protected.
- experiment scripts, scoring scripts, schemas, and lock manifests are read-only/protected.
- Agent may run acceptance commands.
- Scorer independently reruns acceptance and hidden SCBench tests after each checkpoint.
- Hidden SCBench pytest tests remain hidden from the implementation agent.

Primary purpose: isolate executable behavioral harness effect.

## C3 - C2 Plus Periodic Refactoring Prompts

After every 2-3 feature/checkpoint additions, insert a refactor-only turn.

Rules:

- no new behavior,
- preserve all visible and hidden behavior,
- reduce duplication,
- split god functions,
- improve naming using domain language,
- isolate parsing, validation, execution, and formatting responsibilities,
- do not modify locked experiment files.

Primary purpose: test refactoring cadence effect.

## C4 - C3 Plus Periodic Risk Probes

Add rotating probes for:

- architecture drift,
- security risks,
- test-suite blind spots,
- test harness performance,
- dependency creep,
- readability/maintainability.

Rules:

- probes should be narrow and auditable,
- record whether the probe changed code or only produced notes,
- preserve behavior and locked files.

Primary purpose: test risk-mitigation prompt effect.

## C5 - Agent-Authored Gherkin Step Automation

The implementation agent may implement missing step definitions.

Rules:

- maintainers provide feature files,
- agent-authored step code is evaluated separately for correctness, brittleness, speed, and overfit,
- hidden SCBench tests still judge product behavior,
- compare to maintainer-authored locked steps from C2.

Primary purpose: evaluate whether generated acceptance automation is reliable enough to be part of the workflow.

