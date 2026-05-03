@problem_file_merger @checkpoint_002
Feature: Merge heterogeneous file formats

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io
  Scenario: Auto-detect CSV TSV JSONL Parquet and gzip inputs
    Given input files with extensions ".csv", ".tsv", ".jsonl.gz", and ".parquet"
    When I run the merger with "--input-format auto" and "--compression auto"
    Then each input row appears exactly once in the output CSV
    And schema inference uses the union of all encountered fields
    And output columns are sorted lexicographically when no schema is provided

  @core @positive @cli
  Scenario Outline: Schema disagreement strategy selects deterministic target types
    Given heterogeneous inputs disagree about the type of column "value"
    When I run the merger with "--schema-strategy <strategy>"
    Then the resolved type is chosen by the "<strategy>" rules
    And every cell is cast according to the final schema

    Examples:
      | strategy |
      | authoritative |
      | consensus |
      | union |

  @edge @negative @cli
  Scenario Outline: Invalid input shape returns the specified error class
    Given an input file with "<problem>"
    When I run the merger
    Then the exit status is non-zero
    And stderr reports error "<error_code>"

    Examples:
      | problem | error_code |
      | ambiguous extension without Parquet magic | 2 |
      | compression mismatch | 5 |
      | nested JSONL object without nested support | 6 |
      | nested Parquet schema without nested support | 6 |

  @regression @positive @cli
  Scenario: CSV-only checkpoint 1 behavior still works
    Given only CSV input files are provided
    When I run the merger using checkpoint 1 flags
    Then output remains a single sorted CSV with the same schema and casting rules

