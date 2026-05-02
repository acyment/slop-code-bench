# Native Metric Field Map

Status: EXP-012 implementation note.

This map identifies SCBench fields that the first pilot should reuse before adding experiment-specific metrics. Field names are native unless a normalized field is explicitly listed.

## Source Artifacts

| Artifact | Native location | Primary producer | Notes |
| --- | --- | --- | --- |
| Inference result | `<checkpoint>/inference_result.json` | `save_agent_checkpoint_info()` | Agent timing, cost, usage, error state, artifact paths. |
| Correctness result | `<checkpoint>/evaluation.json` | `CorrectnessResults.save()` | Grouped pytest outcomes and collection metadata. |
| Pytest stdout/stderr | `<checkpoint>/evaluation/stdout.txt`, `<checkpoint>/evaluation/stderr.txt` | `CorrectnessResults.save()` | Debug artifact, not the primary metric source. |
| Pytest report | `<checkpoint>/evaluation/report.json` | `CorrectnessResults.save()` | Slimmed pytest-json-report when available. |
| Diff result | `<checkpoint>/diff.json` | `save_agent_checkpoint_info()` | Snapshot diff used for line-change distributions. |
| Aggregate quality | `<checkpoint>/quality_analysis/overall_quality.json` | `save_quality_metrics()` | Snapshot-level quality metrics. |
| File quality rows | `<checkpoint>/quality_analysis/files.jsonl` | `save_quality_metrics()` | Per-file metrics. |
| Symbol quality rows | `<checkpoint>/quality_analysis/symbols.jsonl` | `save_quality_metrics()` | Per-function/method/class metrics. |
| AST-grep rows | `<checkpoint>/quality_analysis/ast_grep.jsonl` | `save_quality_metrics()` | Per-violation rows. |
| Checkpoint export | `<run>/checkpoint_results.jsonl` | `create_problem_reports()` | Flattened per-checkpoint rows for analysis. |
| Run summary | `<run>/result.json` | `display_and_save_summary()` | Aggregated run-level statistics. |

Primary extraction code:

- `src/slop_code/metrics/checkpoint/extractors.py`
- `src/slop_code/metrics/checkpoint/composites.py`
- `src/slop_code/metrics/checkpoint/mass.py`
- `src/slop_code/entrypoints/evaluation/metrics.py`

## Identity And State

| Native field | Source | Normalized pilot field | Notes |
| --- | --- | --- | --- |
| `problem` | `checkpoint_results.jsonl` | `problem_id` | Problem directory/name. |
| `checkpoint` | `checkpoint_results.jsonl` | `checkpoint_id` | Native checkpoint name, e.g. `checkpoint_1`. |
| `idx` | `checkpoint_results.jsonl` | `checkpoint_index` | Native order value. |
| `version` | `checkpoint_results.jsonl` | `problem_version` | Loaded from `problem.yaml`. |
| `state` | `checkpoint_results.jsonl` | `native_checkpoint_state` | `ran`, `skipped`, `error`, or unknown. |
| `path` | `checkpoint_results.jsonl` | `native_problem_output_path` | Path to problem output dir. |
| `is_first`, `is_last` | checkpoint metrics | same | Useful for trajectory analysis. |

Pilot-only fields such as `run_id`, `condition_id`, `replicate_id`, `prompt_template_id`, and harness hashes should be added by experiment wrappers, not inferred from SCBench.

## Correctness Metrics

| Native field | Source function | Normalized pilot field | Calculation |
| --- | --- | --- | --- |
| `strict_pass_rate` | `get_evaluation_metrics()` | `hidden_strict_pass_rate` | `passed_tests / total_tests`. |
| `core_pass_rate` | `get_evaluation_metrics()` | `hidden_core_pass_rate` | `core_passed / core_total`. |
| `isolated_pass_rate` | `get_evaluation_metrics()` | `hidden_current_checkpoint_pass_rate` | Current checkpoint groups excluding regression. |
| `total_tests` | `get_evaluation_metrics()` | `hidden_total_tests` | Sum of `total_counts`; falls back to collected count. |
| `passed_tests` | `get_evaluation_metrics()` | `hidden_passed_tests` | Sum of `pass_counts`. |
| `core_total`, `core_passed` | `get_evaluation_metrics()` | same with `hidden_` prefix | Current unmarked core behavior. |
| `functionality_total`, `functionality_passed` | `get_evaluation_metrics()` | same with `hidden_` prefix | Optional/non-core behavior. |
| `error_total`, `error_passed` | `get_evaluation_metrics()` | same with `hidden_` prefix | Error-handling tests. |
| `regression_total`, `regression_passed` | `get_evaluation_metrics()` | same with `hidden_` prefix | Prior checkpoint tests when included. |
| `duration` | `evaluation.json` | `hidden_eval_duration_seconds` | Pytest execution duration. |
| `pytest_exit_code` | `evaluation.json` | same | Exit code from pytest. |
| `pytest_collected` | `evaluation.json` | same | Number of collected tests. |
| `test_collection_hash` | `evaluation.json` | same | Deterministic hash of collected grouped test IDs. |
| `infrastructure_failure` | `evaluation.json` | `hidden_eval_infrastructure_failure` | True when pytest or collection failed. |

Derived pilot fields:

- `current_checkpoint_passed`: `hidden_core_pass_rate == 1.0` unless the pilot pre-registers a stricter pass policy.
- `strict_trajectory_survival`: first checkpoint index before strict hidden pass failure, computed over a full trajectory.
- `prior_regression_count`: `regression_total - regression_passed`.
- `hidden_failure_after_visible_pass`: visible C2 acceptance passed and hidden pass policy failed.

## Inference, Cost, And Runtime Metrics

| Native field | Source function | Normalized pilot field | Notes |
| --- | --- | --- | --- |
| `started` | `get_inference_metrics()` | `started_at` | ISO timestamp from `inference_result.json`. |
| `ended` | `get_inference_metrics()` | `ended_at` | Native `completed` renamed by extractor. |
| `duration` | `get_inference_metrics()` | `agent_duration_seconds` | `ended - started`. |
| `cost` | `get_inference_metrics()` | `api_cost_usd` | From usage tracker when available. |
| `steps` | `get_inference_metrics()` | `agent_steps` | Agent steps/tool calls according to adapter. |
| `input` | `get_inference_metrics()` | `input_tokens` | Net token usage. |
| `output` | `get_inference_metrics()` | `output_tokens` | Net token usage. |
| `cache_read` | `get_inference_metrics()` | `cache_read_tokens` | Provider-dependent. |
| `cache_write` | `get_inference_metrics()` | `cache_write_tokens` | Provider-dependent. |
| `reasoning` | `get_inference_metrics()` | `reasoning_tokens` | Provider-dependent. |

Experiment wrappers should additionally record visible acceptance runtime, number of test command invocations, failed/retried commands, wall-clock trajectory runtime, and harness process failures.

## Size And Change Metrics

| Native field | Source function | Normalized pilot field | Notes |
| --- | --- | --- | --- |
| `loc` | `get_quality_metrics()` | `total_lines_with_comments` | Native extractor maps this to `lines.total_lines`; preserve native meaning in exports. |
| `sloc` | `get_quality_metrics()` | `source_loc` | Native `lines.loc`. |
| `total_lines` | `get_quality_metrics()` | `total_lines` | Same as native aggregate total. |
| `single_comments` | `get_quality_metrics()` | `single_line_comments` | Comment count. |
| `files` | `get_quality_metrics()` | `file_count` | Measured files. |
| `lines_added`, `lines_removed` | `_compute_distributions()` | same | Uses `diff.json` and file rows. |
| `mean_func_loc` | `_compute_distributions()` | `mean_function_loc` | Computed from symbol rows. |

For pilot reporting, use `source_loc` for LOC-normalized technical drift unless explicitly comparing to native `loc`.

## Complexity And Structure Metrics

| Native field | Source function | Normalized pilot field | Notes |
| --- | --- | --- | --- |
| `functions`, `methods`, `classes` | `get_quality_metrics()` | same | Symbol counts. |
| `statements` | `get_quality_metrics()` | same | Statement count. |
| `symbols_total` | `get_quality_metrics()` | same | Aggregate symbol count. |
| `cc_max` | `get_quality_metrics()` | `cyclomatic_complexity_max` | Max across functions/methods. |
| `cc_mean` | `get_quality_metrics()` | `cyclomatic_complexity_mean` | Mean across functions/methods. |
| `cc_std` | `get_quality_metrics()` | `cyclomatic_complexity_std` | Standard deviation. |
| `cc_high_count` | `get_quality_metrics()` | `high_complexity_function_count` | Native high threshold. |
| `cc_extreme_count` | `get_quality_metrics()` | `extreme_complexity_function_count` | Native extreme threshold. |
| `high_cc_mean` | `get_quality_metrics()` | `high_complexity_mean` | Mean among high-CC functions. |
| `cc_normalized` | `get_quality_metrics()` | same | Native normalized score. |
| `cc_concentration` | `get_quality_metrics()` | `complexity_concentration` | Native concentration metric. |
| `cc_top20` | `get_quality_metrics()` | `complexity_top20_share` | Share of complexity in top 20 percent. |
| `max_nesting_depth` | `get_quality_metrics()` | same | Max nesting. |
| `lines_per_symbol` | `get_quality_metrics()` | same | Mean lines per symbol. |
| `mass.cc` | `compute_mass_metrics()` | `complexity_mass` | Sum of `complexity * sqrt(sloc)`. |
| `mass.high_cc_pct` | `compute_mass_metrics()` | `high_complexity_mass_share` | Share of mass where complexity > 10. |

Candidate technical-drift fields:

- `structural_erosion_slope`: slope of `high_complexity_mass_share` over checkpoints.
- `complexity_concentration_slope`: slope of `complexity_concentration` or `complexity_top20_share`.
- `max_complexity_delta`: checkpoint-to-checkpoint change in `cyclomatic_complexity_max`.

## Duplication, Waste, And Slop Metrics

| Native field | Source function | Normalized pilot field | Notes |
| --- | --- | --- | --- |
| `single_use_functions` | `get_quality_metrics()` | same | Waste signal. |
| `trivial_wrappers` | `get_quality_metrics()` | same | Waste signal. |
| `unused_variables` | `get_quality_metrics()` | same | Waste signal. |
| `clone_lines` | `get_quality_metrics()` | same | Redundancy signal. |
| `cloned_sloc_lines` | `get_quality_metrics()` | same | Redundancy signal. |
| `cloned_pct` | `get_quality_metrics()` | `duplicated_source_pct` | `cloned_sloc_lines / loc` in native extractor. |
| `ast_grep_violations` | `get_quality_metrics()` | same | Total AST-grep violations. |
| `sg_slop_violations` | `_extract_ast_grep_categories()` | same | Slop-category count. |
| `violation_pct` | `get_quality_metrics()` | `ast_grep_violation_line_pct` | Native violation lines over total. |
| `verbosity_flagged_sloc_lines` | `get_quality_metrics()` | same | Verbosity/slop line signal. |
| `verbosity_flagged_pct` | `get_quality_metrics()` | same | Flagged lines over native `loc`. |
| `verbosity` | `compute_checkpoint_verbosity()` | `native_verbosity_score` | Uses `verbosity_flagged_pct` if present, else clone ratio plus violation percentage. |
| `erosion` | `compute_checkpoint_erosion()` | `native_erosion_score` | Uses `mass.high_cc_pct`. |

Candidate pilot fields:

- `verbosity_bloat_slope`: slope of `native_verbosity_score`, `source_loc`, and `duplicated_source_pct`.
- `duplication_slope`: slope of `duplicated_source_pct` or `clone_lines`.

## Graph Metrics

| Native field | Source function | Normalized pilot field | Notes |
| --- | --- | --- | --- |
| `graph_cyclic_dependency_mass` | `get_quality_metrics()` | same | Present only when graph metrics are available. |
| `graph_propagation_cost` | `get_quality_metrics()` | same | Optional. |
| `graph_dependency_entropy` | `get_quality_metrics()` | same | Optional. |

Graph fields may be missing for non-Python or unsupported layouts. Analysis scripts must treat missing as missing, not zero.

## Rubric Metrics

| Native field | Source function | Normalized pilot field | Notes |
| --- | --- | --- | --- |
| `rubric_total_flags` | `get_rubric_metrics()` | same | Count of rubric violations when `rubric.jsonl` exists. |
| `rubric_carried_over` | `get_rubric_metrics()` | same | Count with `carried_over`. |
| `rubric_verbosity_flags` | `get_rubric_metrics()` | same | Verbosity-type flags. |
| `rubric_erosion_flags` | `get_rubric_metrics()` | same | Erosion-type flags. |

Rubric fields may not exist for first pilot runs. They are optional and should not block MVP pipeline validation.

## C2 Visible Acceptance Additions

Experiment-owned C2 fields to add to the result schema:

- `visible_acceptance_passed`
- `visible_acceptance_duration_seconds`
- `visible_acceptance_scenario_total`
- `visible_acceptance_scenario_passed`
- `visible_acceptance_step_errors`
- `visible_acceptance_harness_errors`
- `visible_acceptance_product_errors`
- `visible_acceptance_runtime_by_scenario`
- `feature_hash`
- `steps_hash`
- `lock_manifest_hash`
- `locked_file_violation`

These should be stored separately from native hidden-test fields so C2 acceptance can be analyzed as an intervention and diagnostic.

## Analysis Defaults

For the first pilot:

- Use native hidden `core_pass_rate == 1.0` as the default current-checkpoint correctness pass.
- Report stricter `strict_pass_rate == 1.0` as trajectory survival and regression preservation.
- Compute regression rate from native `regression_total` and `regression_passed`.
- Compute hidden failure after visible pass only for C2 and only after a visible acceptance run was actually attempted.
- Treat missing quality metrics as missing; do not impute zero.
- Treat each full problem trajectory as the major unit of analysis, with checkpoint rows as repeated measures.
