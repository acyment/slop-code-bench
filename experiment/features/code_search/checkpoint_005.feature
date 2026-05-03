@problem_code_search @checkpoint_005
Feature: Rust Java Go and Haskell support

  Background:
    Given the command line tool is available

  @core @positive @cli @jsonl
  Scenario: Search and preview fixes across the expanded language set
    Given a file named "rules.json" contains:
      """
      [
        {"id":"go-no-log-println","kind":"pattern","languages":["go"],"pattern":"log.Println($ARGS)","fix":{"kind":"replace","template":"logger.Println($ARGS)"}},
        {"id":"rust-no-println-macro","kind":"pattern","languages":["rust"],"pattern":"println!($MSG)","fix":{"kind":"replace","template":"log::info!($MSG)"}},
        {"id":"java-no-system-out","kind":"pattern","languages":["java"],"pattern":"System.out.println($X)","fix":{"kind":"replace","template":"logger.info($X)"}},
        {"id":"hs-avoid-putStrLn","kind":"pattern","languages":["haskell"],"pattern":"putStrLn $MSG","fix":{"kind":"replace","template":"logInfo $MSG"}}
      ]
      """
    And a file named "repo/main.go" contains "func main() { log.Println(\"hi\", 42) }"
    And a file named "repo/main.rs" contains "fn main() { println!(\"hi {}\", 42); }"
    And a file named "repo/Main.java" contains "class Main { static void main(String[] a){ System.out.println(\"hi\"); } }"
    And a file named "repo/Main.hs" contains "main = putStrLn \"hi\""
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
      | --dry-run |
    Then the exit status is 0
    And stdout includes matches whose language values are "go", "rust", "java", and "haskell"
    And stdout includes unapplied fix preview lines for all four rules

  @core @positive @cli
  Scenario Outline: Discover files by extension for every supported language
    Given a file named "rules.json" contains:
      """
      [{"id":"marker","kind":"exact","pattern":"MARKER","languages":["<language>"]}]
      """
    And a file named "repo/source<extension>" contains "MARKER"
    When I run the tool with arguments:
      | argument |
      | repo |
      | --rules |
      | rules.json |
    Then the exit status is 0
    And stdout includes a match with language "<language>"

    Examples:
      | language | extension |
      | rust | .rs |
      | java | .java |
      | go | .go |
      | haskell | .hs |
      | haskell | .lhs |

  @regression @positive @cli
  Scenario: Existing Python JavaScript and C++ behavior remains supported
    Given rules for exact, regex, pattern, selector, dry-run, and apply-fixes
    And source files with extensions ".py", ".js", and ".cpp"
    When I run the tool for each existing language
    Then each prior language still produces sorted JSON Lines with the original output schema

