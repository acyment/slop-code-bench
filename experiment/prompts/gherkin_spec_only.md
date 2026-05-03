You are implementing checkpoint {{ checkpoint_id }} for SCBench problem {{ problem_id }}.

Objective:
Implement the behavior described by the Gherkin feature package and preserve all prior checkpoint behavior.

The Gherkin scenarios below are specification context only in this condition. They are not a runnable acceptance suite for this run.

Gherkin specification context:
{{ gherkin_context.strip() }}

Original checkpoint specification:
{{ original_checkpoint_spec.strip() }}

Allowed files:
{{ allowed_paths.strip() }}

Forbidden files:
{{ forbidden_paths.strip() }}

Do not inspect or modify benchmark tests, experiment harness files, result schemas, or scoring scripts.

Completion criteria:
- The product code implements the current checkpoint scenarios.
- Prior checkpoint scenarios remain behaviorally true.
- Required dependency files are updated only if needed.
- Final response reports changed files, commands run, and any known failures.
