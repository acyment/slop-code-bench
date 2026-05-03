# EXP-100R Comparison Report

Generated: 2026-05-03

## Scope

EXP-100R reran the same meaningful mini-screen after strengthening the locked C2 visible acceptance suite for the two mini-screen problems.

- Prior run: `experiment/results/meaningful_mini_screen/`
- Rerun: `experiment/results/meaningful_mini_screen_rerun/`
- Problems: `code_search`, `file_backup`
- Conditions: `C0`, `C1`, `C2`
- Replicates: 3 per condition/problem
- Model/agent: `codex_auth/gpt-5.3-codex-spark` via Codex CLI `0.128.0`
- Benchmark commit: `03bf1f56752bdb4dc3e607d291870972ddd5f214`
- Problems commit: `8be2bd10bad43a3c0068bdafd05f8eb065a7dc80`
- Experiment commit at run start: `1eecea785e3e70bef52d540b48e029bbe33be4e2`

Run command:

```bash
uv run python experiment/scripts/run_pilot_subset.py \
  --subset mini_screen \
  --mode native-run \
  --problems-root ../scb-problems \
  --run-root experiment/runs/meaningful_mini_screen_rerun \
  --run-id-prefix meaningful-rerun \
  --summary-jsonl experiment/results/meaningful_mini_screen_rerun/run_summary.jsonl
```

Export and analysis:

```bash
uv run python experiment/scripts/export_results.py \
  --input-root experiment/runs/meaningful_mini_screen_rerun \
  --output-dir experiment/results/meaningful_mini_screen_rerun/exported

uv run python experiment/scripts/analyze_results.py \
  --results-dir experiment/results/meaningful_mini_screen_rerun/exported \
  --output-dir experiment/results/meaningful_mini_screen_rerun/analysis
```

## Rerun Data Quality

| item | value |
| --- | ---: |
| Trajectories | 18 |
| Exported checkpoint rows | 35 |
| C2 visible-acceptance checkpoint rows | 12 |
| C2 rows with visible gate execution recorded | 12 |
| C2 visible acceptance passes | 12 |
| C2 hidden failures after visible pass | 6 |
| Protocol violations | 0 |
| Lock status | 12 locked rows unchanged; 6 C0 rows not applicable |

One C1 `code_search` replicate stopped at checkpoint 2, so the rerun has 35 exported checkpoint rows instead of the prior run's 36.

## Aggregate Result Deltas

| condition | problem | prior survival | rerun survival | delta | prior hidden pass rate | rerun hidden pass rate | prior regression | rerun regression |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C0 | code_search | 2.000 | 2.000 | 0.000 | 0.667 | 0.667 | 0.000 | 0.000 |
| C0 | file_backup | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C1 | code_search | 2.000 | 1.667 | -0.333 | 0.667 | 0.611 | 0.000 | 0.167 |
| C1 | file_backup | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C2 | code_search | 2.000 | 2.000 | 0.000 | 0.667 | 0.667 | 0.000 | 0.000 |
| C2 | file_backup | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

Rerun checkpoint matrix:

| condition | problem | checkpoint | rows | hidden passes | visible passes | hidden-after-visible |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| C0 | code_search | checkpoint_1 | 3 | 3 | 0 | 0 |
| C0 | code_search | checkpoint_2 | 3 | 3 | 0 | 0 |
| C0 | code_search | checkpoint_3 | 3 | 0 | 0 | 0 |
| C0 | file_backup | checkpoint_1 | 3 | 0 | 0 | 0 |
| C1 | code_search | checkpoint_1 | 3 | 3 | 0 | 0 |
| C1 | code_search | checkpoint_2 | 3 | 2 | 0 | 0 |
| C1 | code_search | checkpoint_3 | 2 | 0 | 0 | 0 |
| C1 | file_backup | checkpoint_1 | 3 | 0 | 0 | 0 |
| C2 | code_search | checkpoint_1 | 3 | 3 | 3 | 0 |
| C2 | code_search | checkpoint_2 | 3 | 3 | 3 | 0 |
| C2 | code_search | checkpoint_3 | 3 | 0 | 3 | 3 |
| C2 | file_backup | checkpoint_1 | 3 | 0 | 3 | 3 |

## Hidden Failure After Visible Pass

| problem | prior C2 count | rerun C2 count | delta |
| --- | ---: | ---: | ---: |
| code_search | 3 | 3 | 0 |
| file_backup | 3 | 3 | 0 |
| total | 6 | 6 | 0 |

The strengthened C2 acceptance suite did not reduce hidden-failure-after-visible-pass count in this rerun. The remaining blind spots are:

- `code_search` checkpoint 3: visible acceptance passed in all three C2 replicates, while hidden tests failed.
- `file_backup` checkpoint 1: visible acceptance passed in all three C2 replicates, while hidden tests failed.

## Cost And Runtime

| condition | prior cost | rerun cost | delta | rerun checkpoints | rerun mean agent seconds/checkpoint |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 | $0.3400 | $0.3285 | -$0.0116 | 12 | 26.0 |
| C1 | $0.2984 | $0.3040 | +$0.0056 | 11 | 25.0 |
| C2 | $0.5449 | $0.7268 | +$0.1819 | 12 | 62.8 |
| total | $1.1833 | $1.3593 | +$0.1760 | 35 | 38.3 |

C2 remained materially more expensive than C0/C1 because it includes the harness-mediated acceptance gate and repair loop. The C2 visible acceptance suite itself was fast in aggregate: 12 checkpoint rows took 3.22 seconds total acceptance runtime, about 268 ms per C2 checkpoint row. Most of the extra cost is agent-side work, not test execution time.

## Interpretation

This rerun validates the improved protocol, not the research thesis.

What is now stronger:

- C2 acceptance is definitely executed by the harness for every C2 checkpoint row.
- C2 visible gate execution is recorded for every C2 checkpoint row.
- No C2 repair feedback was generated because every visible gate passed on the first attempt.
- Locked files stayed unchanged in C1/C2 runs.
- The result schema captures visible pass, hidden pass, hidden-after-visible, cost, and acceptance runtime fields.

What is not promising yet:

- C2 did not outperform C0 on strict survival for either problem.
- C2 did not reduce hidden-failure-after-visible-pass cases after the first strengthening pass.
- `file_backup` remains a checkpoint-1 failure for all conditions, so it is not yet useful for measuring long-horizon drift.
- The C1 `code_search` rerun worsened in one replicate, which reinforces that the current sample is noisy and underpowered.

The right conclusion is that EXP-100R produced a valid executed-spec mini-screen with no observed reduced-drift advantage. It should not be presented as positive evidence that executable specs reduce drift.

## Recommended Next Step

Do not scale to the full 5-6 problem screening matrix yet. First inspect the remaining rerun C2 visible-pass hidden-fail cases and classify whether the gaps are:

- original-spec behavior that the visible acceptance harness still missed,
- hidden-only behavior that should not be mirrored visibly,
- agent implementation failures unrelated to the spec workflow,
- problem unsuitability for this pilot.

If the same failure clusters are original-spec-parity gaps, add another targeted acceptance-strengthening task before running a broader screen. If the failures are hidden-only or the problem is unsuitable, replace or down-rank the problem in the representative subset.
