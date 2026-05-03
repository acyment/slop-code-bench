@problem_file_backup @checkpoint_003
Feature: Destination directories and incremental backups

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io
  Scenario: First run writes full backups into destination job directories
    Given a mounted file tree rooted at "files" contains selected files "A/K.html", "A/L.md", and "O.md"
    And an empty backup directory named "backup"
    And a schedule file named "schedule.yaml" contains a due full job with destination "backup://"
    When I run the tool with "--backup backup"
    Then stdout includes FILE_BACKED_UP events for all selected files
    And the backup directory contains files:
      | path |
      | daily-docs/A/K.html |
      | daily-docs/A/L.md |
      | daily-docs/O.md |
    And JOB_COMPLETED includes files_skipped_unchanged 0 and dest_state_files 0

  @core @positive @cli @file_io
  Scenario: Subsequent run skips unchanged files and backs up changed files
    Given a backup directory already contains prior files for job "daily-docs"
    And the mounted source changes only "A/L.md"
    And a schedule file named "schedule.yaml" contains a due full job with destination "backup://"
    When I run the tool with "--backup backup"
    Then stdout includes DEST_STATE_LOADED with files_total 3
    And stdout includes FILE_SKIPPED_UNCHANGED for "A/K.html" and "O.md"
    And stdout includes FILE_BACKED_UP for "A/L.md"
    And JOB_COMPLETED includes files_skipped_unchanged 2 and dest_state_files 3

  @regression @positive @cli
  Scenario: Pack strategy does not use file-level incremental state
    Given a due job with strategy "pack" and a destination
    When I run the scheduler with existing individual backup files
    Then stdout does not emit FILE_SKIPPED_UNCHANGED for individual source files
    And pack behavior follows checkpoint 2 unless existing pack files are present in a later checkpoint

