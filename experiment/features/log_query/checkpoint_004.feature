@problem_log_query @checkpoint_004
Feature: GLOSS canonical labels

  Background:
    Given the command line tool is available

  @core @positive @cli @json
  Scenario: CANON labels resolve by ordered fallback
    Given source "a" has rows with client.ip, http.client_ip, ip, route, and path fields
    When I run the log query:
      | query |
      | SELECT CANON.ip, CANON.route FROM a GLOSS { ip := a.client.ip | a.http.client_ip | a.ip, route := a.route | a.path } |
    Then stdout includes "CANON.ip" and "CANON.route" keys
    And each CANON value is the first non-null candidate for that row

  @core @positive @cli
  Scenario: DEFAULT supplies a value when all candidates are null
    Given source "a" has no "foo" or "bar" fields
    When I run the log query:
      | query |
      | SELECT CANON.route AS r FROM a GLOSS { route := a.foo | a.bar DEFAULT "/unknown" } |
    Then every output row has "r" equal to "/unknown"

  @core @positive @cli
  Scenario: CANON labels participate in GROUP BY aggregates and conflation predicates
    Given sources "a" and "b" are bound
    When I run queries using CANON labels in SELECT, GROUP BY, and UPON
    Then CANON values use the same resolution rules in each location
    And aggregate outputs remain deterministic

  @edge @negative @cli
  Scenario: STRICT GLOSS reports unequal non-null candidates
    Given source "a" has one row where route is "/a" and path is "/b"
    When I run the log query:
      | query |
      | SELECT a.id, CANON.route FROM a GLOSS STRICT { route := a.route | a.path } |
    Then the exit status is non-zero
    And stderr contains an E_RUNTIME error for conflict in CANON.route

