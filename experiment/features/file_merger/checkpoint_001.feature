@problem_file_merger @checkpoint_001
Feature: Merge and sort CSV files

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io @sorting
  Scenario: Infer schema from CSV inputs and sort by key
    Given a CSV file named "input/a.csv" contains:
      """
      id,name
      2,beta
      1,alpha
      """
    And a CSV file named "input/b.csv" contains:
      """
      id,name
      3,gamma
      """
    When I run the merger with arguments:
      | argument |
      | --output |
      | merged.csv |
      | --key |
      | id |
      | input/a.csv |
      | input/b.csv |
    Then the exit status is 0
    And the file "merged.csv" is a CSV with header "id,name"
    And rows are sorted by "id" ascending
    And equal keys preserve input appearance order

  @core @positive @cli @file_io
  Scenario: Provided schema controls output order and casting
    Given a schema file defines columns id int, ts timestamp, amount float, note string, and is_active bool
    And input CSV files contain extra columns and missing schema columns
    When I run the merger with "--schema schema.json" and "--on-type-error coerce-null"
    Then output columns follow the schema order
    And extra input columns are ignored
    And missing values are emitted as the configured null literal
    And timestamps are normalized to UTC with "Z"

  @edge @negative @cli
  Scenario: Missing key column is an error
    Given input CSV files do not contain column "missing_key"
    When I run the merger with "--key missing_key"
    Then the exit status is non-zero
    And stderr reports a key-column error

  @core @positive @cli
  Scenario: Null keys sort before non-null in ascending and after non-null in descending
    Given input rows include null and non-null key values
    When I run the merger in ascending and descending modes
    Then null key values are first in ascending output
    And null key values are last in descending output

