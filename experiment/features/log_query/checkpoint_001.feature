@problem_log_query @checkpoint_001
Feature: Query NDJSON logs with projection and filtering

  Background:
    Given the command line tool is available

  @core @positive @cli @json
  Scenario: Project selected fields without a WHERE clause
    Given an NDJSON file named "logs.ndjson" contains:
      """
      {"level":"INFO","message":"ok","status":200,"http":{"status":200}}
      {"level":"ERROR","message":"boom","status":"500","service":"api","http":{"status":500}}
      {"level":"WARN","status":503,"service":"worker","http":{"status":503}}
      """
    When I run the log query:
      | query |
      | SELECT level, message FROM logs |
    Then the exit status is 0
    And stdout is a JSON array
    And each output object contains only "level" and "message"
    And missing selected fields appear as null

  @core @positive @cli
  Scenario: Filter with dotted fields and numeric comparisons
    Given the standard LogQL checkpoint 1 NDJSON fixture
    When I run the log query:
      | query |
      | SELECT * FROM logs WHERE http.status >= 500 |
    Then stdout contains only records whose numeric "http.status" is at least 500
    And records with string "http.status" values do not match the numeric comparison

  @core @positive @cli
  Scenario: AND binds tighter than OR
    Given the standard LogQL checkpoint 1 NDJSON fixture
    When I run the log query:
      | query |
      | SELECT level FROM logs WHERE level = "ERROR" OR level = "WARN" AND service = "worker" |
    Then stdout is JSON:
      """
      [{"level":"ERROR"},{"level":"WARN"}]
      """

  @edge @negative @cli
  Scenario: Duplicate selected fields are semantic errors
    Given an NDJSON file named "logs.ndjson" contains:
      """
      {"level":"INFO"}
      """
    When I run the log query:
      | query |
      | SELECT level, level FROM logs |
    Then the exit status is non-zero
    And stderr contains structured error JSON

