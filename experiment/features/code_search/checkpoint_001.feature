@problem_code_search @checkpoint_001
Feature: Python exact and regex code search

  Background:
    Given the command line tool is available

  @core @positive @cli @jsonl
  Scenario: Search Python files with exact and regex rules
    Given a file named "rules.json" contains:
      """
      [
        {"id":"plaintext","kind":"exact","pattern":"plaintext:"},
        {"id":"regex_rule","kind":"regex","pattern":"^hello.*$","regex_flags":["i","m"]}
      ]
      """
    And a file named "repo/A.py" contains:
      """
      print("hello world")
      print("plaintext")
      print("plaintext:")
      print("""
      hello
      hello world
      """)
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stderr is empty
    And stdout is JSON Lines containing exactly:
      """
      {"rule_id":"plaintext","file":"A.py","language":"python","start":{"line":3,"col":8},"end":{"line":3,"col":18},"match":"plaintext:"}
      {"rule_id":"regex_rule","file":"A.py","language":"python","start":{"line":5,"col":1},"end":{"line":5,"col":6},"match":"hello"}
      {"rule_id":"regex_rule","file":"A.py","language":"python","start":{"line":6,"col":1},"end":{"line":6,"col":12},"match":"hello world"}
      """

  @core @positive @cli
  Scenario: Ignore non-Python files and skip files that cannot be decoded
    Given a file named "rules.json" contains:
      """
      [{"id":"todo","kind":"exact","pattern":"TODO:"}]
      """
    And a file named "repo/main.py" contains:
      """
      # TODO: keep this visible
      """
    And a file named "repo/readme.md" contains:
      """
      TODO: ignore markdown
      """
    And a binary file named "repo/broken.py" cannot be decoded as "utf-8"
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stdout is JSON Lines containing exactly:
      """
      {"rule_id":"todo","file":"main.py","language":"python","start":{"line":1,"col":3},"end":{"line":1,"col":8},"match":"TODO:"}
      """

  @edge @negative @cli
  Scenario Outline: Reject invalid rule definitions
    Given a file named "rules.json" contains:
      """
      <rules_json>
      """
    And a file named "repo/main.py" contains:
      """
      print("hello")
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is non-zero
    And stderr contains structured error JSON

    Examples:
      | rules_json |
      | [{"id":"","kind":"exact","pattern":"x"}] |
      | [{"id":"bad","kind":"regex","pattern":"[","regex_flags":["i"]}] |
      | [{"id":"bad_lang","kind":"exact","pattern":"x","languages":["javascript"]}] |

