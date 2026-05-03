Review the current implementation for security risks.

Problem: {{ problem_id }}
Checkpoint: {{ checkpoint_id }}

Focus:
- unsafe shell execution,
- path traversal,
- unbounded file reads/writes,
- unsafe deserialization,
- missing input validation,
- leaking secrets in output/logs.

Patch only risks relevant to the problem contract.
Do not modify locked experiment files.

Visible acceptance command, when available:
```bash
{{ acceptance_command.strip() }}
```

Final response:
- files changed,
- risks fixed or explicitly accepted,
- commands run,
- any remaining risks.
