# Screening Subset

Status: selected before any evidence-producing run.

The screening subset is a smaller C0/C1/C2 matrix intended to detect obvious directional signal and pipeline problems before spending on the full EXP-101 matrix. It is not a replacement for the full pilot and should not be treated as conclusive.

## Selected Problems

Use:

1. `code_search`
2. `file_backup`
3. `migrate_configs`
4. `log_query`

## Rationale

These four problems are the best first screening set because they cover the behaviors most relevant to the specification-drift claim while avoiding avoidable infrastructure confounds:

- `code_search`: code-oriented CLI search/refactoring behavior with five checkpoints and strong concrete examples.
- `file_backup`: stateful file-system behavior with prior behavior preservation and four checkpoints.
- `migrate_configs`: structured configuration migration with parsing, validation, transformation, and five checkpoints.
- `log_query`: query-language behavior over NDJSON with parsing/filtering/aggregation pressure and five checkpoints.

Together they cover CLI tools, file processing, structured transformations, query behavior, cumulative prior-test preservation, and example-rich Gherkin conversion. All have reference probes with no SCBench infrastructure failures.

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

The evidence-producing screening run remains blocked until the native execution bridge and C2 snapshot acceptance integration are implemented.
