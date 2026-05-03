You are performing a refactor-only checkpoint for SCBench problem {{ problem_id }}.

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
```bash
{{ acceptance_command.strip() }}
```

External scoring:
{{ hidden_eval_command.strip() }}

Completion criteria:
- All previously passing visible acceptance checks still pass.
- Hidden benchmark evaluation does not regress when run by the scorer.
- Final response lists refactors and behavior-preservation evidence.
