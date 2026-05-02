# Hidden-Test Separation Notes

Status: EXP-011 implementation note.

SCBench tests are source-available to benchmark maintainers in the problem repo, but they are intended to be hidden from the implementation agent. The pilot must preserve that separation and treat visible Gherkin acceptance checks as an intervention, not as a replacement for native scoring.

## Verified Native Separation

Prompt construction:

- `ProblemConfig.get_checkpoint_spec()` reads only `checkpoint_N.md`.
- `get_task_for_checkpoint()` renders that prose through the configured prompt template.
- The saved implementation prompt is `prompt.txt`.
- The native prompt context includes the formatted entry file and command, not pytest files.

Agent inference workspace:

- Agent sessions are created with `is_agent_infer=True`.
- The checkpoint snapshot is produced after the agent finishes the task.
- Hidden pytest files are not copied by the prompt construction path.

Evaluation workspace:

- Evaluation creates a separate session with `is_agent_infer=False`.
- Collection and pytest execution copy checkpoint-relevant tests from `<problem>/tests` into `.evaluation_tests`.
- Pytest is then run against `.evaluation_tests`, passing `--entrypoint` and `--checkpoint`.
- `.evaluation_tests` is an evaluation-time implementation detail, not an input to the implementation prompt.

Primary source files:

- `src/slop_code/agent_runner/runner.py`
- `src/slop_code/evaluation/config.py`
- `src/slop_code/evaluation/collection.py`
- `src/slop_code/evaluation/pytest_runner.py`

## Test Selection Behavior

For checkpoint `N`:

- If `include_prior_tests: true`, SCBench copies `test_checkpoint_1.py` through `test_checkpoint_N.py`.
- If `include_prior_tests: false`, SCBench copies only `test_checkpoint_N.py`.
- `conftest.py`, helpers, fixture directories, and non-checkpoint helper files are copied when present.
- Prior checkpoint tests are classified as `Regression`.
- Current checkpoint tests are classified by marker:
  - unmarked current tests become `Core`;
  - `@pytest.mark.functionality` becomes `Functionality`;
  - `@pytest.mark.error` becomes `Error`;
  - custom problem markers can map to a configured group type.

`evaluation.json` records the grouped results, pytest collection count, and `test_collection_hash`.

## Pilot Visibility Model

The pilot should use three distinct visibility levels:

- Hidden native tests: original SCBench pytest tests. Only the runner/evaluator sees these.
- Visible C1/C2 specs: experiment-owned `.feature` files intentionally shown to the agent in C1 and C2.
- Locked C2 harness: experiment-owned step definitions and scoring wrappers runnable by the agent but forbidden to modify.

For C2, the implementation agent may run the visible acceptance harness, but must not modify:

- `experiment/features/**`
- `experiment/steps/**`
- `experiment/scripts/**` that run or score the harness
- `experiment/schemas/**`
- native problem tests
- native evaluator/scoring files

## Required Lock Enforcement Tasks

Milestone 8 should implement lock enforcement before any pilot run:

1. Generate a lock manifest with hashes for feature files, step definitions, prompt templates, runner scripts, schemas, and native hidden-test metadata.
2. Verify the manifest before each checkpoint prompt is issued.
3. Verify the manifest after each agent turn/checkpoint.
4. If a locked file changes, mark the checkpoint/run invalid or failed according to the condition policy.
5. Preserve the changed artifact for audit instead of silently restoring it.

## Leakage Risks To Control

- Do not mount or copy the full problem repo into an agent-visible workspace.
- Do not include native pytest file contents, failure traces, or fixture source in prompts.
- Do not paste raw problem config comments into experiment docs or prompts.
- Do not allow C2 visible acceptance files to contain hidden-test implementation details.
- Do not let prompt-generation scripts read pytest files while deriving Gherkin.
- Do not expose native evaluator stdout/stderr to the agent between checkpoints unless the condition explicitly permits that feedback.

## Recommended Policy For Failed Lock Checks

Initial pilot policy:

- If the agent modifies locked C2 files, record `locked_file_violation: true`.
- Treat the checkpoint as failed for visible acceptance.
- Still run native evaluation on the saved product snapshot when feasible, so the analysis can distinguish product correctness from protocol violation.
- Mark the trajectory as invalid for the main C2 causal comparison unless a pre-registered robustness analysis includes protocol-violation runs.

## Unresolved Questions

- Should C2 agents see visible acceptance failure details after each checkpoint, or only a pass/fail command result?
- Should native hidden-test failures ever be shown to the implementation agent during a trajectory? The default answer for comparability should be no.
- Should a harness modification be scored as an immediate trajectory termination or a checkpoint-level failure with continuation?
