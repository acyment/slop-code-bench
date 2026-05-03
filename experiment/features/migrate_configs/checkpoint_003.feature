@problem_migrate_configs @checkpoint_003
Feature: Array-aware patterns and inheritance

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io
  Scenario: Array filter pattern updates matching elements only
    Given a JSON file named "rules.json" contains a pattern_replace rule for "services[?enabled=true].host"
    And a JSON file named "configs/app.json" extends "base.json"
    And "base.json" defines enabled and disabled services
    When I run the migration tool with inheritance enabled
    Then enabled service hosts are replaced
    And disabled service hosts are unchanged
    And stdout reports a file_updated event for "app.json"

  @core @positive @cli @file_io
  Scenario: Inheritance merges parent configs before applying rules
    Given an inheritance map declares "extends" for JSON and YAML files
    And a child config extends a base config that extends a root config
    When I run the migration tool with the inheritance map
    Then the child config includes inherited root and base fields
    And child values override parent values
    And the inheritance directive is removed from the final file

  @edge @negative @cli
  Scenario: Circular inheritance fails before modifying files
    Given an inheritance map declares "extends"
    And config "a.yaml" extends "b.yaml"
    And config "b.yaml" extends "a.yaml"
    When I run the migration tool with inheritance enabled
    Then the exit status is non-zero
    And stderr describes a circular inheritance error
    And no config file is modified

  @regression @positive @cli
  Scenario: Missing array filter matches and missing template variables skip without output
    Given a pattern_replace rule whose array filter matches zero elements
    And a template_string rule whose variable path does not exist
    When I run the migration tool
    Then the target files are unchanged
    And stdout contains no file_updated event for those skipped rules

