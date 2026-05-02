# Conditions

Status: frozen for the first MVP and C0/C1/C2 pilot design. Any later change must update the run-matrix configs in `experiment/configs/` and rerun `experiment/scripts/validate_run_matrix.py`.

## Common Rules For C0-C2

- Hidden SCBench pytest tests are never visible to the implementation agent.
- Native hidden SCBench evaluation remains the final correctness judge.
- Visible Gherkin acceptance checks, when present, are intervention diagnostics and workflow feedback, not replacements for hidden scoring.
- All conditions preserve native SCBench checkpoint ordering and prior-snapshot handoff behavior.
- All conditions use the same selected problems, model, agent harness, upstream commits, environment config, pass policy, and replicate seeds within a comparison block.
- Implementation agents must preserve prior behavior at every checkpoint.
- Native evaluator stdout/stderr and hidden-test failure details are not fed back to the implementation agent during a trajectory unless a later condition explicitly pre-registers that feedback.

## File Visibility Matrix

| File or artifact | C0 | C1 | C2 |
| --- | --- | --- | --- |
| Native checkpoint prose | visible | converted into Gherkin context | converted into Gherkin context |
| Gherkin `.feature` files | hidden/not used | visible as read-only spec context | visible and locked |
| Gherkin step definitions | hidden/not used | hidden/not used | visible enough to run, locked against edits |
| Visible acceptance command | hidden/not used | hidden/not used | visible/runnable |
| Native SCBench pytest tests | hidden | hidden | hidden |
| Experiment scripts/schemas/locks | hidden from prompt unless needed by command docs | locked where referenced | locked |
| Native hidden evaluation result | external scorer only | external scorer only | external scorer only |

## Lock And Invalid-Run Policy

For C1 and C2, experiment-owned spec and harness files are protected by a before/after checkpoint manifest. For C2 this includes:

- `experiment/features/**`
- `experiment/steps/**`
- `experiment/prompts/**`
- `experiment/scripts/**`
- `experiment/schemas/**`
- `experiment/locks/**`

If a locked file changes during an implementation run:

- record `locked_file_violation: true`,
- preserve the changed artifact for audit,
- still run native hidden evaluation when feasible,
- mark the trajectory as a protocol violation,
- exclude the trajectory from the primary causal comparison unless a robustness analysis explicitly includes protocol violations.

## C0 - Baseline Prose

The implementation agent receives the original SCBench checkpoint spec, as close as possible to the benchmark's intended baseline.

Rules:

- Use the upstream `just-solve.jinja` style unless a local runner integration requires minimal wrapping.
- Do not include Gherkin.
- Do not expose hidden pytest tests.
- Do not expose acceptance harness files.
- Preserve SCBench checkpoint order and prior solution handoff.
- No experiment lock manifest is needed because no experiment spec/harness files are exposed.

Primary purpose: baseline comparability.

## C1 - Gherkin Spec Package

The implementation agent receives Gherkin `.feature` files derived from the checkpoint specs.

Rules:

- Include current checkpoint features and prior checkpoint features.
- Provide Gherkin as readable spec context only.
- Do not provide runnable Gherkin commands.
- Do not expose step definitions.
- Do not expose hidden SCBench pytest tests.
- Verify feature/prompt/context files before and after each checkpoint.

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
- Feature, step, prompt, script, schema, and lock files are verified before and after each checkpoint.

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
