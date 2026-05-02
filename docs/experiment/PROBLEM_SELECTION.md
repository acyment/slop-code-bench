# Problem Selection

## Selection Criteria

Prefer problems that:

- use CLI, file-processing, or small HTTP/API boundaries,
- have observable behavior that maps cleanly to Gherkin examples,
- have full multi-checkpoint trajectories,
- exercise prior behavior preservation,
- avoid UI automation,
- avoid unsafe network/process behavior unless containerized,
- have manageable runtime and dependency footprint,
- do not require adding new semantic information to make Gherkin useful.

Avoid or defer problems that:

- depend on expensive services or heavyweight runtimes,
- require broad domain knowledge that would make Gherkin conversion ambiguous,
- have checkpoint configs that disable prior tests in ways that complicate regression analysis,
- have security-sensitive behavior that needs extra sandbox design before exposing runnable acceptance checks.

## Inspected Candidate Configs

| Problem | Type | Difficulty | Checkpoints | Dependencies | Initial Assessment |
| --- | --- | --- | --- | --- | --- |
| `xjq` | CLI XML/HTML/JSON query tool | Easy | 5 | `lxml` | Strong MVP candidate: compact observable CLI behavior. |
| `code_search` | CLI code search/refactoring | Easy | 5 | none observed in config | Strong MVP candidate: JSONL outputs and clear examples. |
| `file_backup` | CLI YAML backup scheduler/file walk | Easy | 4 | `pyyaml`, static assets | Strong pilot candidate: rich domain language and regression pressure. |
| `log_query` | CLI NDJSON query language | Medium | 5 | none observed in config | Good pilot candidate: examples can be concrete and user-facing. |
| `file_merger` | CLI data merge pipeline | Medium | 4 | `pyyaml`, `pyarrow` | Good pilot candidate; check runtime and Parquet dependencies. |
| `file_query_tool` | SQL over files | Medium | 5 | `pyyaml`, `pyarrow` | Valuable but may overlap with `log_query` and increase SQL parser complexity. |
| `textdrop` | HTTP text-sharing service | Easy | 6 | `httpx` | Good API candidate; more service lifecycle complexity. |
| `execution_server` | HTTP command execution server | Easy | 6 | `httpx`, checkpoint 6 disables prior tests | Useful API candidate but security-sensitive and timeout-heavy. Defer unless sandbox is validated. |
| `dynamic_config_service_api` | REST config service | Medium | 4 | `httpx`, `jsonschema`; later checkpoints disable prior tests | Good API candidate, but disabled prior tests may confound regression metrics. |
| `recli` | CLI framework | Hard | 8 | `pyyaml` | Better for later stress testing, not first pilot. |

## Provisional First Pilot Set

Recommended first 6:

1. `xjq`
2. `code_search`
3. `file_backup`
4. `log_query`
5. `file_merger`
6. `textdrop`

Rationale:

- covers CLI, file processing, query languages, static assets, and a small HTTP service,
- avoids the most security-sensitive API task in the first pass,
- keeps Gherkin conversion feasible,
- gives 4-6 checkpoint trajectories without the 8-checkpoint hard task cost.

Alternates:

- Replace `textdrop` with `dynamic_config_service_api` if API semantics are preferred over markdown/storage behavior.
- Replace `file_merger` with `file_query_tool` if SQL-like query behavior is more relevant to SpecCommons.
- Add `execution_server` only after sandbox and timeout controls are explicitly verified.

## MVP Problem Set

Use:

1. `xjq`
2. `code_search`

Rationale:

- both are CLI-based,
- both have concrete stdout/stderr behavior,
- both can be tested without service lifecycle logic,
- both should support a lightweight Gherkin acceptance harness.

## Required Follow-Up Inspection Task

Before implementing the full pilot, run an automated inventory over the pinned problem repo:

- parse every `config.yaml`,
- count checkpoints,
- record `include_prior_tests`,
- record dependencies and static assets,
- classify CLI/API/service/file-processing,
- measure reference-solution test runtime,
- inspect checkpoint prose length and example density,
- flag problems where original hidden tests conflict with prose examples.

Output:

- `experiment/results/problem_inventory.jsonl`
- `experiment/results/problem_selection_report.md`

