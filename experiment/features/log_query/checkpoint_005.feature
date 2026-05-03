@problem_log_query @checkpoint_005
Feature: Nested and correlated POCKET queries

  Background:
    Given the command line tool is available

  @core @positive @cli @json
  Scenario: Scalar POCKET enriches each outer row with a correlated count
    Given sources "a" and "b" are bound
    When I run the log query:
      | query |
      | SELECT a.id, POCKET(SELECT COUNT(*) FROM b WHERE b.rid = UPTREE.a.req) AS b_count FROM a |
    Then stdout contains one row for each "a" record
    And "b_count" is computed from matching "b.rid" values for the current outer row

  @core @positive @cli
  Scenario: BEHOLDS filters rows where a correlated table subquery has results
    Given sources "a" and "b" are bound
    When I run the log query:
      | query |
      | SELECT a.id FROM a WHERE BEHOLDS POCKET[SELECT b.rid FROM b WHERE b.rid = UPTREE.a.req AND b.status >= 500] |
    Then stdout contains only rows with at least one matching error status in source "b"

  @core @positive @cli
  Scenario Outline: Table subquery predicates use deterministic empty-set behavior
    Given a row whose subquery result set is empty
    When I evaluate "<predicate_kind>" against that table subquery
    Then the predicate result is "<result>"

    Examples:
      | predicate_kind | result |
      | EITHERWISE | false |
      | EVERYWISE | true |

  @regression @positive @cli
  Scenario: Subqueries may use prior LogQL features locally
    Given sources "a", "b", and "c" are bound
    When a POCKET subquery uses GLOSS, aggregation, and UPTREE references
    Then its GLOSS labels are scoped to the subquery
    And outer query aliases remain accessible through UPTREE

