@problem_code_search @checkpoint_003
Feature: Structure-aware pattern rules with metavariables

  Background:
    Given the command line tool is available

  @core @positive @cli @jsonl
  Scenario: Pattern rules capture source text and ranges
    Given a file named "rules.json" contains:
      """
      [
        {"id":"py-print","kind":"pattern","pattern":"print($GREETING)","languages":["python"]},
        {"id":"same-tag","kind":"pattern","pattern":"console.log($TAG, $TAG)","languages":["javascript"]}
      ]
      """
    And a file named "repo/main.py" contains:
      """
      def run():
          print("hello")
          print(greeting())
      """
    And a file named "repo/web.js" contains:
      """
      console.log("user", "user");
      console.log("user", id);
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stdout includes JSON Lines for two "py-print" matches with "$GREETING" captures
    And stdout includes one "same-tag" match where both "$TAG" ranges bind to the same text
    And stdout does not include a "same-tag" match for "console.log(\"user\", id)"

  @core @positive @cli
  Scenario: Nested expressions bind as a single metavariable value
    Given a file named "rules.json" contains:
      """
      [{"id":"func-call","kind":"pattern","pattern":"$X($Y)","languages":["python"]}]
      """
    And a file named "repo/nested.py" contains:
      """
      f(g(h(z)))
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stdout includes a match whose "match" value is "f(g(h(z)))"
    And stdout includes captures for "$X" with text "f" and "$Y" with text "g(h(z))"

  @regression @positive @cli
  Scenario: Exact and regex rules from previous checkpoints still produce match lines
    Given a file named "rules.json" contains:
      """
      [
        {"id":"exact-todo","kind":"exact","pattern":"TODO:"},
        {"id":"printf","kind":"regex","pattern":"\\bprintf\\s*\\(","languages":["cpp"]}
      ]
      """
    And a file named "repo/main.py" contains:
      """
      # TODO: keep
      """
    And a file named "repo/main.cpp" contains:
      """
      int main() { printf("x"); }
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stdout includes a match with rule_id "exact-todo"
    And stdout includes a match with rule_id "printf"

