@problem_code_search @checkpoint_004
Feature: Selectors and auto-fixes

  Background:
    Given the command line tool is available

  @core @positive @cli @jsonl
  Scenario: Dry run emits match and unapplied fix preview lines without writing files
    Given a file named "rules.json" contains:
      """
      [
        {"id":"remove-returns","kind":"selector","languages":["python"],"selector":"return_statement","fix":{"kind":"replace","template":"pass"}},
        {"id":"py-print-to-logger","kind":"pattern","languages":["python"],"pattern":"print($ARG)","fix":{"kind":"replace","template":"logger.info($ARG)"}}
      ]
      """
    And a file named "repo/main.py" contains:
      """
      def run():
          print("hello")
          return 42
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
      | --dry-run |
    Then the exit status is 0
    And stdout includes a match line before each fix line for the same range
    And stdout includes fix lines with "applied" set to false
    And the file "repo/main.py" still contains "print(\"hello\")"
    And the file "repo/main.py" still contains "return 42"

  @core @positive @cli @file_io
  Scenario: Apply fixes writes replacements and reports applied fix lines
    Given a file named "rules.json" contains:
      """
      [{"id":"py-print-to-logger","kind":"pattern","languages":["python"],"pattern":"print($ARG)","fix":{"kind":"replace","template":"logger.info($ARG)"}}]
      """
    And a file named "repo/main.py" contains:
      """
      def run():
          print("hello")
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
      | --apply-fixes |
    Then the exit status is 0
    And stdout includes a fix line with "replacement" equal to "logger.info(\"hello\")"
    And stdout includes a fix line with "applied" set to true
    And the file "repo/main.py" contains "logger.info(\"hello\")"

  @edge @positive @cli
  Scenario: Overlapping fixes skip later candidates deterministically
    Given overlapping rules that match the same file range
    When I run the tool with "--apply-fixes"
    Then the earliest fix by file, line, column, and rule_id is applied
    And the overlapping later fix is reported with skipped_reason "overlap"

  @edge @negative @cli
  Scenario: Apply and dry-run flags are mutually exclusive
    Given a file named "rules.json" contains:
      """
      []
      """
    When I run the tool with "--dry-run" and "--apply-fixes"
    Then the exit status is non-zero
    And stderr contains structured error JSON

