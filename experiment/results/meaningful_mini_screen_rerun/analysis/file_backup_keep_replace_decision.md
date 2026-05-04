# EXP-100X `file_backup` Keep/Replace Decision

Decision date: 2026-05-04

## Decision

Down-rank `file_backup` to harness-validation-only for now. Do not use it as an evidence-producing reduced-drift mini-screen problem until a post-fix smoke shows that the selected model can survive checkpoint 1 and reach at least one later checkpoint.

Nominate `migrate_configs` as the first replacement candidate for the next representative mini-screen, pending locked C2 acceptance coverage for checkpoints 1-3. Keep `log_query` as the fallback candidate.

The current `mini_screen_*` configs are treated as historical/replay configs for EXP-100R. They are not updated in this task because a replacement is not promoted until its C2 coverage and reference acceptance pass. Preflight now blocks evidence-producing profiles that still include `file_backup` with this EXP-100X decision.

## Evidence

EXP-100R reran `file_backup` across C0, C1, and C2 with 3 replicates:

| condition | checkpoint | hidden pass rows | strict survival | mean hidden subtest pass rate |
| --- | --- | ---: | ---: | ---: |
| C0 | checkpoint_1 | 0 / 3 | 0 | 0.281 |
| C1 | checkpoint_1 | 0 / 3 | 0 | 0.115 |
| C2 | checkpoint_1 | 0 / 3 | 0 | 0.104 |

This means `file_backup` currently measures checkpoint-1 feasibility more than long-horizon drift. There are no later checkpoint observations for survival slope, regression rate, change amplification across checkpoints, or accumulated technical drift.

C2 also produced 3 hidden-failure-after-visible-pass rows for `file_backup` checkpoint 1. EXP-100U added `file_backup.cp001.safe-dump-shape`, which catches the known brittle parser failure from the old EXP-100R C2 snapshots while the reference checkpoint 1 solution passes. That improves harness fidelity, but it does not establish that C0/C1/C2 can now produce comparable multi-checkpoint trajectories.

Reference probes remain useful but insufficient: the reference solution can pass, yet all observed model trajectories failed checkpoint 1.

## Rationale

`file_backup` is still useful as a harness-validation problem because it exposed:

- visible example overfitting,
- valid YAML fixture-shape mismatch,
- product-entrypoint parity issues,
- hidden-failure-after-visible-pass reporting gaps.

It is not currently useful as a representative drift problem because strict trajectory survival is zero for every condition and replicate. A drift experiment needs runs that reach later checkpoints often enough for prior-behavior preservation and regression opportunities to matter.

## Replacement Candidate

Use `migrate_configs` first if the next task can add locked C2 coverage:

- CLI/file-processing task,
- structured config migration domain maps cleanly to Gherkin,
- five checkpoints,
- reference probe passed all hidden tests,
- no service lifecycle or heavyweight dependency confound.

Use `log_query` second if `migrate_configs` coverage or smoke feasibility is poor.

## Next Gate

Before another evidence-producing mini-screen:

1. Add locked C2 acceptance coverage for `migrate_configs` checkpoints 1-3.
2. Run reference acceptance against copied reference snapshots.
3. Run preflight; require no C2 coverage gaps.
4. If budget allows, run a one-replicate C0/C1/C2 checkpoint-prefix smoke.
5. Update `mini_screen_c0.yaml`, `mini_screen_c1.yaml`, and `mini_screen_c2.yaml` only after the replacement is promoted.
