# Prompt Templates

These are implementation-agent prompt templates. The materialized templates live in `experiment/prompts/*.md`. The runner should render variables and record `prompt_hash` for every checkpoint.

## Shared Variables

- `{{problem_id}}`
- `{{checkpoint_id}}`
- `{{checkpoint_index}}`
- `{{condition_id}}`
- `{{entry_command}}`
- `{{original_checkpoint_spec}}`
- `{{gherkin_context}}`
- `{{acceptance_command}}`
- `{{hidden_eval_command}}`
- `{{allowed_paths}}`
- `{{forbidden_paths}}`
- `{{protected_file_manifest}}`

## C0 Baseline Prose

```text
You are implementing checkpoint {{checkpoint_id}} for SCBench problem {{problem_id}}.

Objective:
Implement the requested behavior from the original checkpoint specification.

Original checkpoint specification:
{{original_checkpoint_spec}}

Allowed files:
{{allowed_paths}}

Forbidden files:
{{forbidden_paths}}

Do not inspect or modify benchmark tests, experiment harness files, result schemas, or scoring scripts.
Preserve behavior from all prior checkpoints.

Completion criteria:
- The product code implements the current checkpoint.
- Prior checkpoint behavior remains intact.
- Required dependency files are updated only if needed.
- Final response reports changed files, commands run, and any known failures.
```

## C1 Gherkin Spec Only

```text
You are implementing checkpoint {{checkpoint_id}} for SCBench problem {{problem_id}}.

Objective:
Implement the behavior described by the Gherkin feature package.

The Gherkin scenarios are specification context. They are not a runnable harness in this condition.

Gherkin specification context:
{{gherkin_context}}

Original checkpoint specification:
{{original_checkpoint_spec}}

Allowed files:
{{allowed_paths}}

Forbidden files:
{{forbidden_paths}}

Do not inspect or modify benchmark tests, experiment harness files, result schemas, or scoring scripts.
Preserve all prior checkpoint behavior described in prior scenarios.

Completion criteria:
- The product code implements the current checkpoint scenarios.
- Prior checkpoint scenarios remain behaviorally true.
- Final response reports changed files, commands run, and any known failures.
```

## C2 Gherkin Plus Executable Harness

```text
You are implementing checkpoint {{checkpoint_id}} for SCBench problem {{problem_id}}.

Objective:
Make the product satisfy the current and prior Gherkin scenarios.

You may run the visible acceptance suite:
{{acceptance_command}}

Locked files:
{{protected_file_manifest}}

Forbidden files:
{{forbidden_paths}}

You must not modify:
- `.feature` files,
- step definition files,
- experiment harness files,
- scoring scripts,
- result schemas,
- lock manifests.

Gherkin specification context:
{{gherkin_context}}

Original checkpoint specification:
{{original_checkpoint_spec}}

Preserve all prior checkpoint behavior.

Completion criteria:
- The visible acceptance command passes, or you explain the remaining failures.
- Product code implements the current checkpoint.
- Locked files are unchanged.
- Final response reports changed files, acceptance command result, other commands run, and known failures.
```

## C3 Refactor-Only Prompt

```text
You are performing a refactor-only checkpoint for {{problem_id}}.

Objective:
Improve maintainability without changing behavior.

Allowed:
- reduce duplication,
- split large or high-complexity functions,
- improve names using domain language,
- isolate parsing, validation, execution, formatting, and persistence responsibilities,
- simplify control flow.

Forbidden:
- adding new product behavior,
- changing public CLI/API behavior,
- modifying `.feature` files,
- modifying step definitions,
- modifying experiment/scoring files.

Commands to run:
{{acceptance_command}}
{{hidden_eval_command}}

Completion criteria:
- All previously passing visible acceptance checks still pass.
- Hidden benchmark evaluation does not regress when run by the scorer.
- Final response lists refactors and behavior-preservation evidence.
```

## C4 Architecture Drift Probe

```text
Review the current implementation for architecture drift before continuing.

Focus:
- misplaced responsibilities,
- growing god functions/classes,
- duplicated parsing/validation/execution logic,
- brittle coupling between CLI/API parsing and domain logic.

Make only low-risk changes that preserve behavior and reduce future change cost.
Do not modify locked experiment files.
Run visible acceptance if available.
```

## C4 Security Probe

```text
Review the current implementation for security risks.

Focus:
- unsafe shell execution,
- path traversal,
- unbounded file reads/writes,
- unsafe deserialization,
- missing input validation,
- leaking secrets in output/logs.

Patch only risks relevant to the problem contract.
Do not modify locked experiment files.
Run visible acceptance if available.
```

## C4 Test Blind Spot Probe

```text
Review visible acceptance coverage for likely blind spots.

Focus:
- prior behavior not covered by visible scenarios,
- edge cases implied by the spec but not represented,
- overfitting risks,
- hidden-test conflicts.

Do not modify locked feature files or step definitions in C2-C4.
You may add product-side checks only when they implement the existing spec.
```

## C4 Test Harness Performance Probe

```text
Review acceptance and local test runtime.

Focus:
- slow setup/teardown,
- repeated subprocess startup,
- excessive fixture data generation,
- flaky waits,
- nondeterminism.

Do not weaken assertions or remove scenarios.
Do not modify locked experiment files unless this is a harness-maintainer phase.
```

## C4 Dependency Creep Probe

```text
Review dependencies added so far.

Focus:
- unnecessary packages,
- packages used for trivial behavior,
- incompatible licenses,
- heavyweight dependencies that increase install/runtime cost,
- dependencies added but no longer used.

Remove unnecessary dependencies only when behavior remains unchanged.
Do not modify locked experiment files.
```
