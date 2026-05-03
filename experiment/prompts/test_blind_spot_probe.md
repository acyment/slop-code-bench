Review visible acceptance coverage for likely blind spots.

Problem: {{ problem_id }}
Checkpoint: {{ checkpoint_id }}

Focus:
- prior behavior not covered by visible scenarios,
- edge cases implied by the spec but not represented,
- overfitting risks,
- hidden-test conflicts.

Do not modify locked feature files or step definitions in C2-C4.
You may add product-side checks only when they implement the existing spec.

Visible acceptance command, when available:
```bash
{{ acceptance_command.strip() }}
```

Final response:
- files changed,
- blind spots considered,
- commands run,
- any remaining risks.
