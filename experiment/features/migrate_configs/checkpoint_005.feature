@problem_migrate_configs @checkpoint_005
Feature: Pre-transformation validation rules

  Background:
    Given the command line tool is available

  @core @negative @cli @validation
  Scenario: Required key validation reports all missing keys and prevents writes
    Given a validation rule "require_database" requires "database.host" and "database.port"
    And a YAML file named "configs/app.yaml" contains only "database.host"
    When I run the migration tool
    Then the exit status is 1
    And stdout is JSON Lines containing a validation_failed event for "database.port"
    And stdout contains no file_updated or file_relocated events
    And no config file is modified

  @core @negative @cli @validation
  Scenario Outline: Validation failures use deterministic messages
    Given a validation rule of type "<rule_type>"
    And a config file that violates the rule
    When I run the migration tool
    Then the exit status is 1
    And stdout contains a validation_failed event whose error mentions "<message_fragment>"

    Examples:
      | rule_type | message_fragment |
      | validate_type | expected type |
      | validate_value | not in allowed values |
      | validate_value | exceeds max |
      | validate_value | does not match pattern |
      | unique_array_values | duplicate values |

  @core @positive @cli @validation
  Scenario: Validation runs after inheritance and before content transformations
    Given a child config inherits a required key from a parent config
    And validation, content transformation, and relocation rules are present
    When I run the migration tool with inheritance enabled
    Then validation sees the inherited key
    And content transformations run only after validation succeeds
    And relocation runs after content transformations

  @regression @positive @cli
  Scenario: Successful validation preserves previous migration behavior
    Given validation rules all pass
    And rules from checkpoints 1 through 4 are present
    When I run the migration tool
    Then content updates and file relocations are applied
    And stdout contains only file_updated and file_relocated events

