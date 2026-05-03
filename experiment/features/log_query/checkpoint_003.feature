@problem_log_query @checkpoint_003
Feature: Multi-source conflation

  Background:
    Given the command line tool is available

  @core @positive @cli @json
  Scenario: Intersecting conflation joins matching aliases and groups results
    Given source "a" is bound to "a.ndjson"
    And source "b" is bound to "b.ndjson"
    And both sources contain request identifiers
    When I run the log query:
      | query |
      | SELECT a.service, b.status, COUNT(*) AS n FROM a CONFLATE INTERSECTING b UPON a.req = b.req GROUP BY a.service, b.status |
    Then stdout contains only matched request pairs
    And stdout groups joined rows by selected qualified fields

  @core @positive @cli
  Scenario Outline: Preserving join flavors keep unmatched rows from the requested side
    Given source "a" has request ids "r1", "r2", and "r3"
    And source "b" has request ids "r1", "r2", and "r5"
    When I run a "<flavor>" conflation from "a" to "b"
    Then unmatched rows are preserved according to "<preserved_side>"

    Examples:
      | flavor | preserved_side |
      | PRESERVING LEFT | left |
      | PRESERVING RIGHT | right |
      | PRESERVING BOTH | both |

  @core @positive @cli
  Scenario: Alias star expands top-level fields as qualified output keys
    Given source "a" has top-level keys "id", "service", and "req"
    And source "b" has status values
    When I run the log query:
      | query |
      | SELECT a.*, b.status AS edge_status FROM a CONFLATE PRESERVING LEFT b UPON a.req = b.req |
    Then each output object has keys "a.id", "a.service", "a.req", and "edge_status"

  @edge @negative @cli
  Scenario: Bare SELECT star is invalid when conflation is present
    Given sources "a" and "b" are bound
    When I run the log query:
      | query |
      | SELECT * FROM a CONFLATE b UPON a.req = b.req |
    Then the exit status is non-zero
    And stderr contains an E_SEMANTIC error

