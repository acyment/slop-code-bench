@problem_migrate_configs @checkpoint_004
Feature: File relocation rules

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io
  Scenario: Rename service config files by captured path component
    Given a JSON file named "rules.json" contains a path_rename file rule from "services/$name/config.yaml" to "configs/$name.yaml"
    And files exist:
      | path |
      | configs/services/api/config.yaml |
      | configs/services/worker/config.yaml |
    When I run the migration tool
    Then the directory "configs" contains files:
      | path |
      | configs/api.yaml |
      | configs/worker.yaml |
    And stdout contains file_relocated events for both moved files

  @core @positive @cli @file_io
  Scenario: Rename files from content variables
    Given a content_rename file rule reads "service.name"
    And "services/api/config.yaml" contains service.name "api-gateway"
    When I run the migration tool
    Then the file moves to "services/api/api-gateway.yaml"
    And stdout contains a file_relocated event

  @core @positive @cli @file_io
  Scenario: Relocation updates inheritance references after moves
    Given inheritance is enabled
    And "app.yaml" extends "base.yaml"
    And a relocation rule moves "base.yaml" to "common/base.yaml"
    When I run the migration tool
    Then "app.yaml" updates its inheritance path to "common/base.yaml"
    And stdout orders events as content updates, relocations, then inheritance reference updates

  @edge @negative @cli
  Scenario: Destination collision aborts file relocation
    Given a file relocation rule would move "services/api/config.yaml" to "configs/api.yaml"
    And "configs/api.yaml" already exists
    When I run the migration tool
    Then the exit status is non-zero
    And stderr says the destination already exists
    And no relocation is committed

