@problem_log_query @checkpoint_002
Feature: Grouping and aggregate functions

  Background:
    Given the command line tool is available

  @core @positive @cli @json
  Scenario: Compute global aggregates after filtering
    Given the LogQL checkpoint 2 NDJSON fixture
    When I run the log query:
      | query |
      | SELECT COUNT(*) AS total, SUM(bytes) AS sum_bytes, AVG(latency_ms) AS avg_latency FROM logs WHERE level = "INFO" |
    Then stdout is JSON:
      """
      [{"total":6,"sum_bytes":800,"avg_latency":8.7}]
      """

  @core @positive @cli
  Scenario: Group rows in first-encountered order
    Given the LogQL checkpoint 2 NDJSON fixture
    When I run the log query:
      | query |
      | SELECT service, COUNT(*) AS n FROM logs WHERE bytes >= 0 GROUP BY service |
    Then stdout groups by service in first-encountered order
    And null group keys remain distinct from strings numbers and booleans

  @core @positive @cli
  Scenario: Aggregates ignore invalid values according to function rules
    Given the LogQL checkpoint 2 NDJSON fixture
    When I run queries for COUNT(field), SUM, AVG, MIN, MAX, and UNIQUE
    Then COUNT(field) counts present non-null arrays and objects
    And SUM and AVG ignore non-numeric values
    And MIN and MAX prefer numbers before strings
    And UNIQUE preserves first-seen deep-equal values

  @edge @negative @cli
  Scenario: Non-grouped selected fields are invalid when aggregates are present
    Given the LogQL checkpoint 2 NDJSON fixture
    When I run the log query:
      | query |
      | SELECT service, COUNT(*) FROM logs |
    Then the exit status is non-zero
    And stderr contains an E_SEMANTIC error

