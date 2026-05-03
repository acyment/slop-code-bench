@problem_file_merger @checkpoint_004
Feature: Nested schema support

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io
  Scenario: Cast nested JSON values and emit canonical JSON cells
    Given a schema file defines a struct column "user" and an array column "items"
    And a JSONL input file contains nested objects and arrays matching the schema
    When I run the merger with "--schema schema_nested.json"
    Then nested columns are emitted as minified canonical JSON
    And struct fields appear in schema-declared order
    And map keys are sorted lexicographically
    And timestamps inside nested values are normalized to UTC with "Z"

  @core @positive @cli @sorting
  Scenario: Sort and partition by primitive nested field paths
    Given a schema file declares "user.id" and "attrs" map values as primitive leaves
    And input rows contain nested user ids and country attributes
    When I run the merger with "--key user.id,event_time" and "--partition-by attrs[\"country\"]"
    Then rows are sorted by the nested primitive key values
    And partition directories are derived from the resolved nested country value

  @edge @negative @cli
  Scenario Outline: Invalid nested usage fails deterministically
    Given input data or flags use nested structures incorrectly
    When I run the merger
    Then the exit status is non-zero
    And stderr reports error "<error_code>"

    Examples:
      | error_code |
      | 3 |
      | 6 |

  @regression @positive @cli
  Scenario: Flat schema inference remains flat-only
    Given no "--schema" file is provided
    And input files contain only primitive flat values
    When I run the merger
    Then schema inference and CSV output follow checkpoint 2 behavior

