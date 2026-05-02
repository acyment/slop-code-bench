# Repository And Fork Plan

## Canonical Upstreams

Runner:

- URL: https://github.com/SprocketLab/slop-code-bench
- Observed main commit: `03bf1f56752bdb4dc3e607d291870972ddd5f214`
- License: MIT
- Purpose: agent runner, checkpoint execution, evaluation, metrics, summaries.

Problems:

- URL: https://github.com/gabeorlanski/scb-problems
- Observed main commit: `8be2bd10bad43a3c0068bdafd05f8eb065a7dc80`
- License: Apache-2.0
- Purpose: problem specs, tests, reference solutions, static assets.

## Fork Policy

Do not fork automatically unless GitHub credentials are available and explicit user authorization is given.

Actual fork names used for EXP-002:

- `acyment/slop-code-bench`
- `acyment/scb-problems`

The originally proposed `speccommons` organization was not available to the authenticated account during setup.

Recommended branch:

```bash
git checkout -b experiment/gherkin-drift-pilot
```

## Exact Setup Commands

Runner fork:

```bash
git clone https://github.com/acyment/slop-code-bench.git
cd slop-code-bench
git remote add upstream https://github.com/SprocketLab/slop-code-bench.git
git fetch upstream
git checkout -b experiment/gherkin-drift-pilot upstream/main
```

Problems fork:

```bash
git clone https://github.com/acyment/scb-problems.git
cd scb-problems
git remote add upstream https://github.com/gabeorlanski/scb-problems.git
git fetch upstream
git checkout -b experiment/gherkin-drift-pilot upstream/main
```

If the experiment should live in one repo, prefer the runner repo and pin the problem repo by URL/commit in experiment config. Do not vendor the entire problem repo unless the runner cannot cleanly load a pinned external problem path.

## Proposed Directory Design

Add this under the runner repo unless local inspection suggests a better integration point:

```text
experiment/
  README.md
  REPRODUCIBILITY.md
  configs/
    pilot_c0.yaml
    pilot_c1.yaml
    pilot_c2.yaml
    mvp_c0.yaml
    mvp_c2.yaml
  prompts/
    baseline_prose.md
    gherkin_spec_only.md
    gherkin_executable.md
    refactor_only.md
    architecture_probe.md
    security_probe.md
    test_blind_spot_probe.md
    test_harness_performance_probe.md
    dependency_creep_probe.md
  features/
    <problem_id>/
      checkpoint_001.feature
      checkpoint_002.feature
  steps/
    <problem_id>/
      steps.py
  locks/
    lock_manifest.json
  runs/
    .gitkeep
  results/
    .gitkeep
  scripts/
    select_problems.py
    generate_condition_context.py
    run_trajectory.py
    score_trajectory.py
    export_results.py
    analyze_results.py
    verify_locks.py
  schemas/
    run_result.schema.json
    checkpoint_result.schema.json
```

## Integration Strategy

Prefer additive integration:

- leave SCBench runner/evaluation logic unchanged,
- add an experiment wrapper that calls existing `slop-code run`, `slop-code eval`, and `slop-code metrics static`,
- add prompt templates and condition context generation outside core runner modules,
- add acceptance harness under `experiment/` and invoke it as a separate visible check,
- export a normalized result table after SCBench has produced native outputs.

Modify upstream runner code only if required for:

- custom prompt packaging,
- lock enforcement inside the agent workspace,
- per-checkpoint visible acceptance command hooks,
- missing machine-readable metadata.

Every unavoidable change must be recorded in `experiment/REPRODUCIBILITY.md` with:

- file path,
- reason,
- behavior change,
- expected effect on SCBench comparability,
- test evidence.

## Lock Enforcement

For C2+ runs, compute a manifest before each checkpoint:

- `.feature` file hashes,
- step definition hashes,
- harness script hashes,
- scoring script hashes,
- schemas/config hashes.

After implementation and before scoring:

- recompute hashes,
- fail run as `invalid_lock_violation` if a protected file changed,
- store diff paths in result artifacts,
- do not silently restore files before scoring.

## Reproducibility File

Add `experiment/REPRODUCIBILITY.md` if the runner repo lacks an equivalent experiment-level file. It should record:

- runner upstream URL and commit,
- problem upstream URL and commit,
- experiment branch and commit,
- model and agent harness versions,
- environment config,
- Docker image digests if available,
- prompt template hashes,
- feature and step hashes,
- run IDs and timestamps,
- random seeds,
- known deviations from upstream SCBench.

## Scripts To Add

- `select_problems.py`: inventory problem configs, checkpoint counts, tags, dependencies, static assets, and suitability flags.
- `generate_condition_context.py`: build prompt context for C0/C1/C2 without changing benchmark specs.
- `run_trajectory.py`: orchestrate one `(condition, problem, replicate)` trajectory.
- `score_trajectory.py`: run visible acceptance and hidden SCBench scoring per checkpoint.
- `verify_locks.py`: enforce protected-file hashes.
- `export_results.py`: normalize native outputs to JSONL/SQLite schema.
- `analyze_results.py`: create pass matrices, survival curves, regression summaries, and quality slopes.
