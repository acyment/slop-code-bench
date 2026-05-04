# Screening Run Status

Generated: 2026-05-04

## Current Status

The native execution path is now implemented far enough to run SCBench through condition-specific fixtures without replacing hidden benchmark evaluation. A one-checkpoint paid smoke run succeeded for C2 on `code_search` checkpoint 1, a first reduced-drift probe ran for C0 vs C2, and the later meaningful mini-screen has now run and rerun across C0/C1/C2 for `code_search` and `file_backup`.

This is still directional evidence. The latest EXP-100R rerun validates that C2 executable acceptance is being executed as a harness-mediated intervention, but it did not show a C2 survival advantage or reduce hidden-failure-after-visible-pass cases. EXP-100W now adds near-miss diagnostics, EXP-100X down-ranks `file_backup` to harness-validation-only, and EXP-100Y promotes `migrate_configs` into the next evidence-producing mini-screen. The mini-screen preflight is ready; the broader representative screening matrix remains blocked because it still includes `file_backup` and lacks complete locked C2 visible acceptance coverage.

## Seven-Step Run Checklist

| step | status | result |
| --- | --- | --- |
| 1. Implement execution bridge | done | `run_trajectory.py` supports `native-dry-run` and `native-run` by rendering condition prompts into a temporary SCBench problem root and invoking native `slop-code run`. |
| 2. Wire C2 acceptance to snapshots | done for measurement and intervention gate | C2 prompts expose `.scbench_acceptance/runner.py`; future C2 native runs enable a harness-mediated visible acceptance gate before hidden scoring, and post-run snapshot acceptance is still merged as measurement. |
| 3. Add screening preflight | done | `validate_full_pilot_preflight.py --profile screening` checks model/agent selection, execution bridge, freeze state, C2 coverage, and C2 executed-feedback enforcement. |
| 4. Choose fixed runtime settings | done | Screening configs use `codex_auth/gpt-5.3-codex-spark`, Codex CLI `0.128.0`, `thinking: low`, `num_workers: 1`. |
| 5. Run one paid smoke checkpoint | done | `smoke-c2-code-search-cp1-v2` completed and passed. |
| 6. Run replacement mini-screen | ready | `mini_screen_*` configs now use `code_search` and `migrate_configs`, checkpoints 1-3, C0/C1/C2, 3 replicates. `experiment/results/mini_screen_preflight/preflight.json` is ready. |
| 7. Export/analyze/report | done for smoke, reduced-drift probe, meaningful mini-screen, and EXP-100R rerun | Normalized smoke result and analysis are under `experiment/results/paid_smoke_c2_code_search_cp1_v2/`; the EXP-100R rerun is under `experiment/results/meaningful_mini_screen_rerun/`. |

## Paid Smoke Result

Run: `smoke-c2-code-search-cp1-v2`

Condition/problem/checkpoint: `C2 / code_search / checkpoint_1`

Key result:

- Native SCBench run status: `completed`
- Visible acceptance: passed (`code_search.cp001.workspace-cli-search`)
- Hidden SCBench tests: passed
- Core tests: 7/7
- Total hidden tests collected: 13
- Regression failures: 0
- Hidden failure after visible pass: 0
- Agent reported cost: `$0.0325127`
- Agent duration: `41.37s`
- Hidden eval duration: `4.64s`
- Agent steps: 34
- Net input tokens: 412,262
- Net output tokens: 8,298
- Net reasoning tokens: 2,999

Primary artifacts:

- Native run: `experiment/runs/paid_smoke/code_search/replicate_01/smoke-c2-code-search-cp1-v2/native/run`
- Normalized export: `experiment/results/paid_smoke_c2_code_search_cp1_v2/`
- Analysis summary: `experiment/results/paid_smoke_c2_code_search_cp1_v2/analysis/summary.json`
- Screening preflight: `experiment/results/screening_preflight/preflight.json`

## Important Interpretation

The smoke result validates that the pipeline can:

- run Codex through SCBench using condition-specific checkpoint prompts,
- expose a workspace-local C2 visible acceptance command,
- preserve native hidden SCBench scoring,
- export hidden correctness and technical metrics,
- merge visible acceptance results into normalized result rows.

It does not show a tendency between C0, C1, and C2. There is only one C2 checkpoint and no paired baseline run in this smoke. It also does not prove the agent executed the visible acceptance suite as feedback before checkpoint completion.

## Reduced-Drift Mini-Screen Result

Run prefix: `reduced-drift-probe`

Shape:

- Conditions: C0 vs C2
- Problems: `code_search`, `file_backup`
- Checkpoint prefix: 1-3
- Replicates: 1
- Evaluable checkpoint rows: 8
- Agent-reported cost: `$0.2900795`

Directional/pipeline outcome:

- `code_search`: C0 and C2 both survived through checkpoint 2 and failed hidden tests at checkpoint 3. C2 visible acceptance passed at checkpoints 1-3, producing one hidden-failure-after-visible-pass case at checkpoint 3.
- `file_backup`: C0 and C2 both failed hidden tests at checkpoint 1 and did not progress to checkpoints 2-3. C2 visible acceptance passed checkpoint 1, producing one hidden-failure-after-visible-pass case.
- There is no observed survival or regression-rate advantage for C2 in this one-replicate mini-screen.
- Because C2 agent-side acceptance execution was not audited as mandatory feedback, this result should not be treated as primary evidence for the executed-spec thesis.

Primary artifacts:

- Runs: `experiment/runs/reduced_drift_probe/`
- Normalized export: `experiment/results/reduced_drift_probe/`
- Analysis summary: `experiment/results/reduced_drift_probe/analysis/summary.json`
- Directional report: `experiment/results/reduced_drift_probe/report/reduced_drift_report.md`

## Meaningful Mini-Screen And EXP-100R Rerun

Latest run prefix: `meaningful-rerun`

Shape:

- Conditions: C0, C1, C2
- Problems: `code_search`, `file_backup`
- Checkpoint prefix: 1-3
- Replicates: 3
- Trajectories: 18
- Evaluable checkpoint rows: 35
- C2 visible-acceptance checkpoint rows: 12
- C2 rows with visible gate execution recorded: 12
- Protocol violations: 0
- Agent-reported cost: `$1.3592863`

Directional outcome:

- `code_search`: C0 and C2 both survived through checkpoint 2 and failed hidden tests at checkpoint 3 in all three replicates. C1 worsened in one replicate, failing checkpoint 2 once.
- `file_backup`: C0, C1, and C2 all failed hidden tests at checkpoint 1 in all three replicates.
- C2 visible acceptance passed all 12 C2 checkpoint rows, but six of those rows failed hidden tests afterward.
- Hidden-failure-after-visible-pass count stayed unchanged from the prior meaningful mini-screen: 6 before, 6 after acceptance strengthening.
- The EXP-100R result validates that the visible gate executes, but every C2 gate passed on the first attempt, so no repair feedback was generated. It does not provide positive evidence that C2 reduced functional/spec drift in this mini-screen.

Primary artifacts:

- Runs: `experiment/runs/meaningful_mini_screen_rerun/`
- Normalized export: `experiment/results/meaningful_mini_screen_rerun/exported/`
- Analysis summary: `experiment/results/meaningful_mini_screen_rerun/analysis/summary.json`
- Comparison report: `experiment/results/meaningful_mini_screen_rerun/analysis/exp100r_comparison.md`
- Near-miss report: `experiment/results/meaningful_mini_screen_rerun/analysis/near_miss_summary.md`
- `file_backup` decision: `experiment/results/meaningful_mini_screen_rerun/analysis/file_backup_keep_replace_decision.md`

## Current Mini-Screen Gate

The evidence-producing replacement mini-screen is ready:

- conditions: C0, C1, C2
- problems: `code_search`, `migrate_configs`
- checkpoint prefix: 1-3
- replicates: 3
- trajectories: 18
- checkpoint executions: 54
- covered C2 feature scenarios: 22 executable and 3 documented spec-only
- preflight: `experiment/results/mini_screen_preflight/preflight.json`

This mini-screen is the next meaningful run candidate. It is not a full screening matrix and should be labeled as a replacement mini-screen because the second problem changed after EXP-100X.

## Broader Screening Blocker

The screening preflight blocks the full screening matrix because C2 visible acceptance coverage is partial:

- selected C2 checkpoint slots: 19
- covered checkpoint slots: 9
- missing checkpoint slots: 10

The covered slots are:

- `code_search` checkpoints 1-3
- `file_backup` checkpoints 1-3
- `migrate_configs` checkpoints 1-3

The missing C2 slots include later checkpoints for `code_search`, `file_backup`, and `migrate_configs`, plus all selected checkpoints for `log_query`. The broader screening profile also remains blocked because `file_backup` is evidence-disabled by EXP-100X.

The C2 feedback blocker has been addressed for current and future C2 native runs:

- current enforcement mode: `harness_mediated`
- native C2 runs set `SPECCOMMONS_ACCEPTANCE_GATE=1`
- the runner executes visible acceptance after each checkpoint draft and feeds failures back for one repair attempt before hidden scoring

## Recommended Next Step

EXP-100S is complete. The root-cause report is `experiment/results/meaningful_mini_screen_rerun/analysis/c2_root_cause_analysis.md`.

Key finding:

- `code_search`: C2 improved checkpoint 3 hidden subtest pass rate versus C0 but still missed strict pass due remaining pattern-semantics gaps.
- `file_backup`: currently unsuitable for drift measurement because all conditions fail checkpoint 1; C2 visible examples allowed a brittle YAML parser that handled hand-written Gherkin examples but failed benchmark-style valid YAML fixture shapes.
- All C2 acceptance gates passed on first attempt, so C2 execution produced no repair feedback in EXP-100R.

EXP-100T, EXP-100U, EXP-100V, EXP-100W, EXP-100X, and EXP-100Y are complete:

- visible C2 acceptance now uses benchmark-equivalent `uv run <script>` entrypoints for `code_search` and `file_backup` and records command provenance artifacts.
- `file_backup` checkpoint 1 acceptance now includes a `yaml.safe_dump`-style schedule shape; the reference checkpoint 1 solution passes it, while all three EXP-100R C2 checkpoint 1 snapshots fail it as `product_error`.
- `code_search` checkpoint 3 acceptance now catches the remaining EXP-100R C2 near-miss snapshots while the reference checkpoint 3 solution still passes.
- near-miss analysis now reports hidden subtest pass-rate deltas and failed hidden cluster labels without exposing hidden test bodies.
- `file_backup` is down-ranked to harness-validation-only because all C0/C1/C2 EXP-100R replicates failed checkpoint 1; `migrate_configs` was selected as the replacement and now has locked C2 coverage.
- `migrate_configs` now has six locked executable scenarios for checkpoints 1-3, reference acceptance passes through checkpoint 3, and the active `mini_screen_*` configs replace `file_backup` with `migrate_configs`.
- preflight now blocks evidence-producing profiles that still include `file_backup` with an `EXP-100X` evidence-disabled-problem reason; the current mini-screen profile no longer includes it and is ready.

Next run the replacement mini-screen if budget allows, then export/analyze it as a separate replacement screen:

```bash
uv run python experiment/scripts/validate_full_pilot_preflight.py --profile mini_screen --problems-root ../scb-problems --output-dir experiment/results/mini_screen_preflight
uv run python experiment/scripts/run_pilot_subset.py --subset mini_screen --mode native-run --problems-root ../scb-problems --run-id-prefix replacement-mini-screen
```

Before running the broader screening matrix, complete the remaining locked visible acceptance scenarios for the selected screening checkpoints and rerun:

```bash
uv run python experiment/scripts/freeze_pilot_artifacts.py snapshot --problems-root ../scb-problems
uv run python experiment/scripts/validate_full_pilot_preflight.py --profile screening --problems-root ../scb-problems --output-dir experiment/results/screening_preflight
```

Only run the full screening matrix after that preflight returns `ready`.
