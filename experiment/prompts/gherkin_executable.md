You are implementing checkpoint {{ checkpoint_id }} for SCBench problem {{ problem_id }}.

Objective:
Make the product satisfy the current and prior Gherkin scenarios while preserving behavior from earlier checkpoints.

Visible acceptance command:
```bash
{{ acceptance_command.strip() }}
```

Execution requirement:
Run the visible acceptance command after every material product-code change and again after your final product-code change before ending this checkpoint. If it fails, use the visible failure output to repair the product code and rerun it. A C2 checkpoint is not complete until this command has been executed and its result is reported.

The experiment harness will independently execute the same visible acceptance command after your checkpoint draft. If it fails, the harness may feed the visible failure output back for a bounded repair attempt before hidden benchmark scoring.

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
- The visible acceptance command was executed after the final product-code change.
- The visible acceptance command passes for a successful checkpoint; any remaining failure must be reported as a failed checkpoint.
- Product code implements the current checkpoint.
- Prior checkpoint behavior remains intact.
- Locked files are unchanged.
- Final response reports changed files, acceptance command result, other commands run, and known failures.
