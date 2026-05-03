@problem_code_search @checkpoint_002
Feature: JavaScript and C++ language-aware search

  Background:
    Given the command line tool is available

  @core @positive @cli @jsonl
  Scenario: Search Python, JavaScript, and C++ files with language filters
    Given a file named "rules.json" contains:
      """
      [
        {"id":"todo","kind":"exact","pattern":"TODO:"},
        {"id":"printf","kind":"regex","pattern":"\\bprintf\\s*\\(","languages":["cpp"]},
        {"id":"console-log","kind":"regex","pattern":"console\\.log\\s*\\(","languages":["javascript"]}
      ]
      """
    And a file named "repo/main.py" contains:
      """
      # TODO: python work
      """
    And a file named "repo/app.js" contains:
      """
      function run() {
        console.log("ready");
      }
      """
    And a file named "repo/src/engine.cpp" contains:
      """
      void run() {
        printf("ready");
      }
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stdout is JSON Lines sorted by file and position
    And stdout includes a match with rule_id "console-log" and language "javascript"
    And stdout includes a match with rule_id "printf" and language "cpp"
    And stdout includes a match with rule_id "todo" and language "python"

  @regression @positive @cli
  Scenario: Python-only behavior from checkpoint 1 still works
    Given a file named "rules.json" contains:
      """
      [{"id":"exact","kind":"exact","pattern":"plaintext:","languages":["python"]}]
      """
    And a file named "repo/A.py" contains:
      """
      print("plaintext:")
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stdout is JSON Lines containing exactly:
      """
      {"rule_id":"exact","file":"A.py","language":"python","start":{"line":1,"col":8},"end":{"line":1,"col":18},"match":"plaintext:"}
      """

  @edge @negative @cli
  Scenario: Reject a rule that names an unsupported language
    Given a file named "rules.json" contains:
      """
      [{"id":"bad","kind":"exact","pattern":"x","languages":["ruby"]}]
      """
    And a file named "repo/main.py" contains:
      """
      x
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is non-zero
    And stderr contains structured error JSON

