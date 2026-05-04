# Screening Subset

Status: selected before any evidence-producing run; partially superseded by the EXP-100X `file_backup` decision.

The screening subset is a smaller C0/C1/C2 matrix intended to detect obvious directional signal and pipeline problems before spending on the full EXP-101 matrix. It is not a replacement for the full pilot and should not be treated as conclusive.

## Selected Problems

Use:

1. `code_search`
2. `file_backup` for historical comparison and harness validation only
3. `migrate_configs`
4. `log_query`

## Rationale

These four problems are the best first screening set because they cover the behaviors most relevant to the specification-drift claim while avoiding avoidable infrastructure confounds:

- `code_search`: code-oriented CLI search/refactoring behavior with five checkpoints and strong concrete examples.
- `file_backup`: stateful file-system behavior with prior behavior preservation and four checkpoints; after EXP-100X, do not use it as an evidence-producing drift problem until a post-fix smoke shows checkpoint-1 survival.
- `migrate_configs`: structured configuration migration with parsing, validation, transformation, and five checkpoints.
- `log_query`: query-language behavior over NDJSON with parsing/filtering/aggregation pressure and five checkpoints.

Together they cover CLI tools, file processing, structured transformations, query behavior, cumulative prior-test preservation, and example-rich Gherkin conversion. All have reference probes with no SCBench infrastructure failures.

EXP-100X update: `file_backup` failed checkpoint 1 in every C0/C1/C2 EXP-100R replicate, so it is down-ranked to harness-validation-only. The next representative evidence mini-screen should promote `migrate_configs` as the replacement after locked C2 coverage and reference acceptance pass.

## Deferred From Screening

- `file_merger`: good full-pilot candidate, but deferred from the screening subset because `pyarrow`/Parquet adds dependency and runtime cost that can confound the first signal check.
- `textdrop`: good full-pilot service/API candidate, but deferred from the screening subset because service lifecycle handling should be validated after the CLI/file/query bridge is stable.

## Screening Matrix

The matrix files are:

- `experiment/configs/screening_c0.yaml`
- `experiment/configs/screening_c1.yaml`
- `experiment/configs/screening_c2.yaml`

Shape:

- Conditions: `C0`, `C1`, `C2`
- Replicates: `1`
- Trajectories: `12`
- Checkpoint executions: `57`

Run the dry-run/preflight form with:

```bash
uv run python experiment/scripts/run_pilot_subset.py \
  --subset screening \
  --mode dry-run \
  --problems-root ../scb-problems \
  --run-root /tmp/scbench-screening-dry-run \
  --run-id-prefix screening
```

The evidence-producing screening run remains blocked until the replacement problem decision is reflected in configs, locked C2 acceptance coverage exists for every included checkpoint slot, and preflight returns `ready`.
