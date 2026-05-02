# Metrics

## Correctness And Functional Drift

### Strict Trajectory Survival

For each trajectory, compute the largest checkpoint index `k` such that all checkpoints `1..k` pass the strict policy.

Strict pass should use SCBench's full current-plus-prior hidden evaluation where available. If SCBench exports `strict_pass_rate`, require `strict_pass_rate == 1.0`.

### Regression Rate

For checkpoint `n`, count prior-checkpoint tests that previously passed but fail after checkpoint `n`.

Use SCBench regression group counts when available:

- `regression_total`
- `regression_passed`

Also compute scenario-level visible regressions for C2:

- prior visible scenarios passed at checkpoint `n-1`,
- same scenarios failed at checkpoint `n`.

### Hidden Failure After Visible Pass

For C2:

```text
visible_acceptance_passed == true
hidden_tests_passed == false
```

Report by problem, checkpoint, replicate, and scenario tags active at that checkpoint.

### Checkpoint Pass/Fail Matrix

Build a matrix over:

```text
condition_id x problem_id x checkpoint_id x replicate_id
```

Columns:

- visible acceptance pass,
- hidden strict pass,
- hidden isolated pass,
- hidden core pass,
- regression pass,
- infrastructure failure,
- invalid lock violation.

## SCBench Technical Drift Metrics

Reuse SCBench metrics first.

Observed in SCBench:

- `verbosity`: checkpoint-owned composite score.
- `erosion`: checkpoint-owned composite score.
- cyclomatic complexity fields such as `cc_max`, `cc_mean`, `cc_high_count`, `high_cc_mean`.
- clone fields such as `clone_lines`, `cloned_pct`.
- line fields such as `loc`, `sloc`, `total_lines`.
- AST-grep and slop violation fields.
- graph fields where available: cyclic dependency mass, propagation cost, dependency entropy.

Observed definitions:

- Verbosity uses `verbosity_flagged_pct` when present. Fallback is clone ratio plus AST-grep violation percentage.
- Erosion uses `mass.high_cc_pct`.
- Function mass is `cyclomatic_complexity * sqrt(sloc)`.
- High-complexity mass uses functions/methods with CC greater than 10.

## Additional Technical Drift Metrics

### Structural Erosion Slope

Fit slope of `erosion` over checkpoint index per trajectory.

Also store:

- first checkpoint erosion,
- final checkpoint erosion,
- delta,
- max.

### Verbosity/Bloat Slope

Fit slope of `verbosity`, `loc`, `sloc`, and `total_lines` over checkpoint index.

Normalize LOC growth by checkpoint index and by number of hidden tests when useful.

### Cyclomatic Complexity

Record per checkpoint:

- `cc_max`,
- `cc_mean`,
- `cc_high_count`,
- `cc_extreme_count`,
- `high_cc_mean`,
- `cc_top20`,
- max function length if available.

### Duplication

Record:

- `clone_lines`,
- `cloned_pct`,
- files with clones if available.

### Change Amplification

Compute from git or SCBench diff artifacts:

- files changed per checkpoint,
- lines added/removed,
- functions touched per checkpoint,
- modified files touching prior-domain responsibilities.

### Dependency Creep

Compare dependency manifests across checkpoints:

- `requirements.txt`,
- `pyproject.toml`,
- lock files if present.

Record:

- dependency count,
- added dependencies,
- removed dependencies,
- dependencies unused by import scan where feasible.

### Test Runtime Growth

Record:

- visible acceptance runtime,
- hidden SCBench evaluation runtime,
- total test count,
- visible scenario count.

Fit runtime slope per trajectory.

## Experiment Cost Metrics

Record when available:

- wall-clock runtime,
- agent duration,
- input/output/cache/reasoning tokens,
- API cost,
- number of agent turns/steps,
- failed commands,
- retried commands,
- visible acceptance invocations,
- hidden evaluation invocations.

SCBench already exports cost, duration, steps, and token categories from inference result files where the agent harness provides them.

