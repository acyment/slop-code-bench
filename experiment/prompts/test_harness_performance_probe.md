Review acceptance and local test runtime.

Problem: {{ problem_id }}
Checkpoint: {{ checkpoint_id }}

Focus:
- slow setup/teardown,
- repeated subprocess startup,
- excessive fixture data generation,
- flaky waits,
- nondeterminism.

Do not weaken assertions or remove scenarios.
Do not modify locked experiment files unless this is a harness-maintainer phase.

Visible acceptance command, when available:
```bash
{{ acceptance_command.strip() }}
```

Final response:
- files changed,
- runtime improvements or reasons for no change,
- commands run,
- any remaining risks.
