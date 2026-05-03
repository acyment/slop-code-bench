@problem_file_backup @checkpoint_004
Feature: Incremental pack backups

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io
  Scenario: Load existing packs and report unchanged pack contents
    Given the backup destination contains pack files:
      | name | files |
      | pack-1.tar | A,B |
      | pack-2.tar | C |
      | pack-3.tar | D,E |
    And the mounted source files A, B, C, D, and E are unchanged
    And a schedule file named "schedule.yaml" contains a due pack job with max_pack_bytes 4
    When I run the tool with "--backup backup"
    Then stdout emits PACK_LOADED once for each existing pack
    And stdout emits PACK_SKIP_UNCHANGED for each unchanged packed file
    And stdout emits PACK_UNCHANGED instead of PACK_CREATED for unchanged packs
    And JOB_COMPLETED includes files_skipped_unchanged 5

  @core @positive @cli @file_io
  Scenario: Repack changed files and preserve unchanged packs
    Given existing packs contain A, B, C, D, and E
    And source files A and C have changed
    And source files B, D, and E are unchanged
    When I run the due pack job with "--backup backup"
    Then stdout emits PACK_LOADED for the existing packs
    And stdout emits FILE_PACKED for changed files and any files repacked with them
    And stdout emits PACK_UPDATED with old_size and old_checksum for rewritten packs
    And stdout emits PACK_UNCHANGED for packs whose files all remain unchanged
    And JOB_COMPLETED reports unchanged file count separately from total selected files

  @regression @positive @cli
  Scenario: Empty pack destination still follows checkpoint 2 pack creation
    Given a due pack job with an empty destination directory
    When I run the scheduler
    Then stdout emits FILE_PACKED and PACK_CREATED events
    And stdout does not emit PACK_LOADED, PACK_UNCHANGED, or PACK_UPDATED

