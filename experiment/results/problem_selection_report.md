# Problem Selection Inventory Report

Generated at: 2026-05-02T15:41:37.509075+00:00

## MVP Recommendation

Use `code_search` and `file_backup` for the minimum viable pilot.

| Problem | Boundary | Difficulty | Checkpoints | Ref runtime | Score | Risks |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `code_search` | cli | Easy | 5 | 42.6s | 8 | - |
| `file_backup` | cli, file_processing | Easy | 4 | 42.8s | 10 | - |

## First Full Pilot Recommendation

Use `code_search`, `file_backup`, `log_query`, `file_merger`, `textdrop`, and `migrate_configs` for the first 5-6 problem pilot.

| Problem | Boundary | Difficulty | Checkpoints | Ref runtime | Score | Risks |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `code_search` | cli | Easy | 5 | 42.6s | 8 | - |
| `file_backup` | cli, file_processing | Easy | 4 | 42.8s | 10 | - |
| `file_merger` | cli, file_processing | Medium | 4 | 112.5s | 8 | heavy_dependency |
| `log_query` | cli, query_language | Medium | 5 | 99.6s | 9 | - |
| `migrate_configs` | cli, file_processing | Easy | 5 | 54.6s | 10 | - |
| `textdrop` | api_service | Easy | 6 | 120.5s | 5 | service_lifecycle |

## Top Ranked Problems By Metadata Heuristic

| Problem | Boundary | Difficulty | Checkpoints | Ref runtime | Score | Risks |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `xjq` | cli, file_processing, query_language | Easy | 5 | 59.3s | 12 | - |
| `env_manager` | cli, file_processing | Easy | 5 | - | 10 | - |
| `etl_pipeline` | cli, file_processing | Easy | 5 | - | 10 | - |
| `file_backup` | cli, file_processing | Easy | 4 | 42.8s | 10 | - |
| `file_query_tool` | cli, file_processing, query_language | Medium | 5 | - | 10 | heavy_dependency |
| `migrate_configs` | cli, file_processing | Easy | 5 | 54.6s | 10 | - |
| `database_migration` | cli, file_processing, database | Medium | 5 | - | 9 | - |
| `layered_config_synthesizer` | cli, file_processing | Medium | 4 | - | 9 | - |
| `log_query` | cli, query_language | Medium | 5 | 99.6s | 9 | - |
| `pwd_manager` | cli, file_processing | Medium | 5 | - | 9 | - |
| `cfgpipe` | cli | Easy | 6 | - | 8 | - |
| `code_search` | cli | Easy | 5 | 42.6s | 8 | - |

## Notes

- Runtime fields are populated only for requested runtime-probe problems.
- `xjq` remains a strong alternate, but the local reference-runtime probe showed core-pass mismatches that should be resolved before using it in the MVP.
- The inventory intentionally excludes checkpoint prose, test names, fixture source, and assertion details.
- Reference-runtime pass rates are diagnostic only; hidden SCBench evaluation remains the final judge during actual experiment runs.
