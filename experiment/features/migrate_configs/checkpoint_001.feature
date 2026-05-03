@problem_migrate_configs @checkpoint_001
Feature: Basic configuration transformations

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io
  Scenario: Replace values and rename keys in supported config files
    Given a JSON file named "rules.json" contains:
      """
      {
        "prod_env":{"type":"replace_value","key":"environment","value":"production"},
        "rename_db_key":{"type":"rename_key","old_key":"db.hostname","new_key":"db.host"}
      }
      """
    And a JSON file named "configs/app.json" contains:
      """
      {"environment":"development","db":{"hostname":"localhost","port":5432}}
      """
    When I run the tool with arguments:
      | argument |
      | rules.json |
      | configs |
    Then the exit status is 0
    And the file "configs/app.json" contains JSON with "environment" equal to "production"
    And the file "configs/app.json" contains JSON with "db.host" equal to "localhost"
    And stdout is JSON Lines containing a file_updated event for "app.json"

  @core @positive @cli @file_io
  Scenario: Deep merge data into matching files without replacing sibling fields
    Given a JSON file named "rules.json" contains a merge_data rule scoped to "**/*"
    And a YAML file named "configs/config.yaml" contains logging level "debug" and cache ttl 300
    When I run the migration tool
    Then the file "configs/config.yaml" keeps the existing logging format and cache ttl
    And the file "configs/config.yaml" has logging level "info"
    And the file "configs/config.yaml" has new logging handlers and cache enabled fields
    And stdout reports the merge rule in rules_applied

  @core @positive @cli
  Scenario Outline: Process only supported configuration file extensions
    Given a rule that replaces key "region" with "us-west-2"
    And a file named "configs/app<extension>" contains a region field
    When I run the migration tool
    Then the file "configs/app<extension>" is updated

    Examples:
      | extension |
      | .json |
      | .yaml |
      | .yml |
      | .toml |
      | .ini |

  @edge @positive @cli
  Scenario: Ignore files with unsupported extensions
    Given a rule that replaces key "region" with "us-west-2"
    And a file named "configs/readme.txt" contains "region=us-east-1"
    When I run the migration tool
    Then the file "configs/readme.txt" is unchanged
    And stdout does not report a file_updated event for "readme.txt"

