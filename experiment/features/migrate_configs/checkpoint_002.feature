@problem_migrate_configs @checkpoint_002
Feature: Pattern matching templates and conditional replacements

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io
  Scenario: Pattern replacement captures path components and uses them in values
    Given a JSON file named "rules.json" contains:
      """
      {"normalize_service_hosts":{"type":"pattern_replace","key_pattern":"services.$name.host","value":"${name}.internal.example.com"}}
      """
    And a JSON file named "configs/config.json" contains:
      """
      {"services":{"api":{"host":"localhost","port":8080},"database":{"host":"localhost","port":5432}}}
      """
    When I run the migration tool
    Then "configs/config.json" has "services.api.host" equal to "api.internal.example.com"
    And "configs/config.json" has "services.database.host" equal to "database.internal.example.com"
    And stdout reports "normalize_service_hosts" in rules_applied

  @core @positive @cli @file_io
  Scenario: Template string builds a target value from other keys
    Given a JSON file named "rules.json" contains a template_string rule for key "s3.bucket"
    And a YAML file named "configs/config.yaml" contains environment "staging" and aws.region "us-west-2"
    When I run the migration tool
    Then "configs/config.yaml" has "s3.bucket" equal to "data-staging-us-west-2"

  @core @positive @cli
  Scenario Outline: Conditional replacement only applies when the condition matches
    Given a rule that conditionally replaces "server.host" with "prod.example.com"
    And "server.host" currently equals "<current>"
    When I run the migration tool
    Then "server.host" is "<result>"

    Examples:
      | current | result |
      | localhost | prod.example.com |
      | staging.example.com | staging.example.com |

  @regression @positive @cli
  Scenario: Checkpoint 1 replace_value rename_key and merge_data rules still work
    Given rules using replace_value, rename_key, merge_data, pattern_replace, template_string, and conditional_replace
    When I run the migration tool
    Then content rules are applied in lexicographic order by rule name
    And stdout reports every file_updated event as JSON Lines

