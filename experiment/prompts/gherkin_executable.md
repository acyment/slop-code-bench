You are implementing checkpoint {{ checkpoint_id }} for SCBench problem {{ problem_id }}.

Objective:
Make the product satisfy the current and prior Gherkin scenarios while preserving behavior from earlier checkpoints.

Visible acceptance command:
```bash
{{ acceptance_command.strip() }}
```

Locked experiment files:
{{ protected_file_manifest.strip() }}

Forbidden files:
{{ forbidden_paths.strip() }}

You must not modify:
- `.feature` files,
- step definition files,
- experiment harness files,
- scoring scripts,
- result schemas,
- lock manifests.

Gherkin specification context:
{{ gherkin_context.strip() }}

Original checkpoint specification:
{{ original_checkpoint_spec.strip() }}

Completion criteria:
- The visible acceptance command passes, or you explain the remaining failures.
- Product code implements the current checkpoint.
- Prior checkpoint behavior remains intact.
- Locked files are unchanged.
- Final response reports changed files, acceptance command result, other commands run, and known failures.
