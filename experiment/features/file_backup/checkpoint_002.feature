@problem_file_backup @checkpoint_002
Feature: Strategy-driven backup events

  Background:
    Given the command line tool is available

  @core @positive @cli @jsonl @file_io
  Scenario Outline: Full and verify strategies process selected files individually
    Given a mounted file tree rooted at "files" contains selected files
    And a schedule file named "schedule.yaml" contains one due job with strategy "<strategy>"
    When I run the scheduler at "2025-09-10T03:30:00Z"
    Then stdout includes STRATEGY_SELECTED with kind "<strategy>"
    And each selected file emits "<file_event>" with path, size, and checksum
    And JOB_COMPLETED includes total_size

    Examples:
      | strategy | file_event |
      | full | FILE_BACKED_UP |
      | verify | FILE_VERIFIED |

  @core @positive @cli @file_io
  Scenario: Pack strategy creates deterministic packs under the size limit
    Given a mounted file tree rooted at "files" contains files with byte sizes:
      | path | size |
      | file1 | 28 |
      | file2 | 4 |
      | file3 | 31 |
      | file4 | 33 |
      | file5 | 10 |
    And a schedule file named "schedule.yaml" contains a due pack job with max_pack_bytes 32
    When I run the scheduler at "2025-09-10T03:30:00Z"
    Then stdout includes FILE_PACKED events assigning file1 and file2 to pack 1
    And stdout finalizes pack 1 before packing file3
    And stdout packs oversized file4 alone instead of failing
    And stdout emits PACK_CREATED for every finalized pack
    And JOB_COMPLETED includes packs and total_size

  @regression @positive @cli
  Scenario: Jobs without a strategy keep checkpoint 1 simulated behavior
    Given a due job without a strategy field
    When I run the scheduler
    Then stdout contains selected and excluded file events
    And stdout does not contain STRATEGY_SELECTED, FILE_BACKED_UP, FILE_VERIFIED, FILE_PACKED, or PACK_CREATED

