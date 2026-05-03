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

  @core @positive @cli @jsonl
  Scenario: Optional metavariables, literal dollars, and multiple captures follow pattern semantics
    Given a file named "rules.json" contains:
      """
      [
        {"id":"optional-item","kind":"pattern","pattern":"[$X?]","languages":["python"]},
        {"id":"dollar-var","kind":"pattern","pattern":"$$price = $VAL","languages":["python"]},
        {"id":"js-func","kind":"pattern","pattern":"function $NAME($ARG) {}","languages":["javascript"]},
        {"id":"var-decl","kind":"pattern","pattern":"let $VAR = $VAL;","languages":["javascript"]}
      ]
      """
    And a file named "repo/items.py" contains:
      """
      []
      [value]
      $price = 100
      """
    And a file named "repo/a.js" contains:
      """
      let a = 1;
      let b = 2;
      function greet(name) {}
      """
    And a file named "repo/z.js" contains:
      """
      let z = 3;
      """
    And a file named "repo/not_javascript.py" contains:
      """
      function wrong(arg) {}
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stdout includes one "optional-item" match without a "$X" capture
    And stdout includes one "optional-item" match with "$X" text "value"
    And stdout includes one "dollar-var" match with "$VAL" text "100"
    And stdout includes one "js-func" match with "$NAME" text "greet" and "$ARG" text "name"
    And stdout includes "var-decl" matches sorted by file and source position
    And stdout does not include a "js-func" match from "not_javascript.py"

  @core @positive @cli @jsonl
  Scenario: Multiline Python patterns preserve capture boundaries
    Given a file named "rules.json" contains:
      """
      [{"id":"if-return","kind":"pattern","pattern":"if $COND:\n        return $VALUE","languages":["python"]}]
      """
    And a file named "repo/app.py" contains:
      """
      def choose(flag):
          if flag:
              return result
          return None
      """
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stdout includes a match whose "match" value spans the if line and return line
    And stdout includes captures for "$COND" with text "flag" and "$VALUE" with text "result"

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
