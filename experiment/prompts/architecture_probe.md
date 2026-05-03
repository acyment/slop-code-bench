Review the current implementation for architecture drift before continuing.

Problem: {{ problem_id }}
Checkpoint: {{ checkpoint_id }}

Focus:
- misplaced responsibilities,
- growing god functions/classes,
- duplicated parsing/validation/execution logic,
- brittle coupling between CLI/API parsing and domain logic.

Make only low-risk changes that preserve behavior and reduce future change cost.
Do not modify locked experiment files.

Visible acceptance command, when available:
```bash
{{ acceptance_command.strip() }}
```

Final response:
- files changed,
- refactors made,
- commands run,
- any remaining risks.
