# Gherkin Conversion Ledger

Source basis: visible checkpoint prose from
`gabeorlanski/scb-problems@8be2bd10bad43a3c0068bdafd05f8eb065a7dc80`.
Hidden tests, fixture assertions, and evaluator outputs were not used as
conversion sources.

Information level for this milestone: example-enriched Gherkin. Each feature
uses concrete examples that either appear in the checkpoint prose or directly
instantiate visible rules from that prose.

| Problem | Checkpoint | Feature File | Source Prose | Added Information Notes |
| --- | --- | --- | --- | --- |
| `code_search` | 1 | `code_search/checkpoint_001.feature` | `checkpoint_1.md` | Concrete Python exact/regex examples restate visible examples and schema rules. |
| `code_search` | 2 | `code_search/checkpoint_002.feature` | `checkpoint_2.md` | Concrete language-filter examples restate visible JS/C++ extension rules. |
| `code_search` | 3 | `code_search/checkpoint_003.feature` | `checkpoint_3.md` | Pattern/metavariable examples restate visible examples and optional/same-name rules. |
| `code_search` | 4 | `code_search/checkpoint_004.feature` | `checkpoint_4.md` | Fix and selector examples restate visible rule schema and dry-run/apply behavior. |
| `code_search` | 5 | `code_search/checkpoint_005.feature` | `checkpoint_5.md` | Language expansion examples restate visible Rust/Java/Go/Haskell extension behavior. |
| `file_backup` | 1 | `file_backup/checkpoint_001.feature` | `checkpoint_1.md` | Schedule, glob, and JSONL event examples restate visible prose examples. |
| `file_backup` | 2 | `file_backup/checkpoint_002.feature` | `checkpoint_2.md` | Strategy examples instantiate visible full/verify/pack rules. |
| `file_backup` | 3 | `file_backup/checkpoint_003.feature` | `checkpoint_3.md` | Incremental destination examples restate visible first/subsequent-run behavior. |
| `file_backup` | 4 | `file_backup/checkpoint_004.feature` | `checkpoint_4.md` | Pack incremental examples restate visible pack loaded/updated/unchanged behavior. |
| `migrate_configs` | 1 | `migrate_configs/checkpoint_001.feature` | `checkpoint_1.md` | Basic transformation examples restate visible replace/rename/merge rules. |
| `migrate_configs` | 2 | `migrate_configs/checkpoint_002.feature` | `checkpoint_2.md` | Pattern/template/conditional examples restate visible rule semantics. |
| `migrate_configs` | 3 | `migrate_configs/checkpoint_003.feature` | `checkpoint_3.md` | Array and inheritance examples restate visible requirements. |
| `migrate_configs` | 4 | `migrate_configs/checkpoint_004.feature` | `checkpoint_4.md` | File relocation examples restate visible path/content relocation behavior. |
| `migrate_configs` | 5 | `migrate_configs/checkpoint_005.feature` | `checkpoint_5.md` | Validation examples restate visible validation phase and failure event rules. |
| `log_query` | 1 | `log_query/checkpoint_001.feature` | `checkpoint_1.md` | SQL-like projection/filter examples restate visible examples and null rules. |
| `log_query` | 2 | `log_query/checkpoint_002.feature` | `checkpoint_2.md` | Aggregation examples restate visible COUNT/SUM/AVG/GROUP BY behavior. |
| `log_query` | 3 | `log_query/checkpoint_003.feature` | `checkpoint_3.md` | Conflation examples restate visible join and alias rules. |
| `log_query` | 4 | `log_query/checkpoint_004.feature` | `checkpoint_4.md` | GLOSS examples restate visible canonical-label behavior. |
| `log_query` | 5 | `log_query/checkpoint_005.feature` | `checkpoint_5.md` | POCKET/subquery examples restate visible correlated subquery behavior. |
| `file_merger` | 1 | `file_merger/checkpoint_001.feature` | `checkpoint_1.md` | CSV sorting/schema examples directly instantiate visible CLI rules. |
| `file_merger` | 2 | `file_merger/checkpoint_002.feature` | `checkpoint_2.md` | Heterogeneous input examples restate visible format and schema reconciliation rules. |
| `file_merger` | 3 | `file_merger/checkpoint_003.feature` | `checkpoint_3.md` | Partition examples restate visible Hive-style and sharding rules. |
| `file_merger` | 4 | `file_merger/checkpoint_004.feature` | `checkpoint_4.md` | Nested schema examples restate visible nested typing and path rules. |
| `textdrop` | 1 | `textdrop/checkpoint_001.feature` | `checkpoint_1.md` | HTTP form/note/raw/health examples restate visible endpoint contract. |
| `textdrop` | 2 | `textdrop/checkpoint_002.feature` | `checkpoint_2.md` | Markdown/JSON examples restate visible rendering and validation behavior. |
| `textdrop` | 3 | `textdrop/checkpoint_003.feature` | `checkpoint_3.md` | Metadata/TOC/render examples restate visible rendering pipeline behavior. |
| `textdrop` | 4 | `textdrop/checkpoint_004.feature` | `checkpoint_4.md` | Static docs/assets/robots/debug examples restate visible route behavior. |
| `textdrop` | 5 | `textdrop/checkpoint_005.feature` | `checkpoint_5.md` | Ops and identity examples restate visible secret/cookie behavior. |
| `textdrop` | 6 | `textdrop/checkpoint_006.feature` | `checkpoint_6.md` | Storage backend examples restate visible local/object startup/runtime behavior. |

## Later Review Items

- During EXP-050, parse these files with the selected runner parser and record
  any syntax or dialect changes required by that runner.
- During acceptance-harness implementation, decide whether examples using
  shortened hashes or excerpts need deterministic fixture expansion.
- Before full pilot execution, review each example for information-parity risk
  and flag examples that should move to the later enriched-only ablation.

