@problem_file_backup @checkpoint_001
Feature: Schedule-driven backup event simulation

  Background:
    Given the command line tool is available

  @core @positive @cli @jsonl @file_io
  Scenario: Run due daily jobs and report selected and excluded files
    Given a mounted file tree rooted at "files" contains:
      | path | content |
      | A/B/C/D.py | |
      | A/B/E.bin | |
      | A/I.py | |
      | M.py | |
      | O.md | |
    And a schedule file named "schedule.yaml" contains:
      """
      version: 1
      timezone: UTC
      jobs:
        - id: job-root
          source: mount://
          exclude: ["A/*", "*.py", "**/*.bin"]
          when:
            kind: daily
            at: "03:30"
        - id: job-subdir
          source: mount://A/B
          exclude: ["*.py", "**/*.bin"]
          when:
            kind: daily
            at: "03:30"
      """
    When I run the tool with arguments:
      | argument |
      | --now |
      | 2025-09-10T03:30:00Z |
      | --schedule |
      | schedule.yaml |
      | --duration |
      | 1 |
      | --mount |
      | files |
    Then the exit status is 0
    And stdout starts with a SCHEDULE_PARSED event
    And stdout reports due jobs in ascending job_id order
    And stdout reports selected paths relative to each job source
    And stdout reports the first matching exclusion pattern for excluded files
    And stdout ends each job with a JOB_COMPLETED event containing selected and excluded counts

  @core @positive @cli
  Scenario Outline: Determine whether jobs are due inside the inclusive simulation window
    Given a schedule with one enabled job:
      | kind | at | days |
      | <kind> | <at> | <days> |
    When I run the scheduler at "<now>" for "<duration>" hours
    Then the job is "<eligibility>"

    Examples:
      | kind | at | days | now | duration | eligibility |
      | daily | 03:30 | | 2025-09-10T03:30:00Z | 0 | due |
      | daily | 03:30 | | 2025-09-10T03:31:00Z | 24 | due |
      | weekly | 03:30 | Wed | 2025-09-10T03:30:00Z | 0 | due |
      | once | 2025-09-10T03:30:00 | | 2025-09-10T03:30:00Z | 0 | due |

  @core @positive @cli @jsonl @file_io
  Scenario: Recurring jobs run once for each trigger inside the simulation window
    Given a mounted file tree rooted at "files" contains:
      | path | content |
      | data.txt | data |
    And a schedule file named "schedule.yaml" contains:
      """
      version: 1
      timezone: UTC
      jobs:
        - id: daily-repeat
          source: mount://
          destination: backup://
          when:
            kind: daily
            at: "03:30"
      """
    When I run the scheduler at "2025-09-08T03:30:00Z" for "48" hours
    Then stdout reports the job as due at "2025-09-08T03:30:00Z"
    And stdout reports the job as due at "2025-09-09T03:30:00Z"
    And stdout reports the job as due at "2025-09-10T03:30:00Z"
    And stdout contains three JOB_COMPLETED events for "daily-repeat"

  @edge @negative @cli
  Scenario: Disabled jobs emit no job events
    Given a schedule file named "schedule.yaml" contains:
      """
      version: 1
      timezone: UTC
      jobs:
        - id: disabled
          enabled: false
          source: mount://
          destination: backup://
          when: {kind: daily, at: "03:30"}
      """
    When I run the scheduler at "2025-09-10T03:30:00Z"
    Then stdout contains one SCHEDULE_PARSED event
    And stdout does not contain JOB_ELIGIBLE, JOB_STARTED, or JOB_COMPLETED events

  @edge @positive @cli @jsonl @file_io
  Scenario: Block-style lists, default fields, and representative glob operators are honored
    Given a mounted file tree rooted at "files" contains:
      | path | content |
      | data1.txt | one |
      | data10.txt | ten |
      | keep.md | keep |
      | report1.log | one |
      | report3.log | three |
      | tmp/cache.bin | cache |
    And a schedule file named "schedule.yaml" contains:
      """
      version: 1
      jobs:
        - id: defaults-and-globs
          source: mount://
          destination: backup://
          exclude:
            - tmp/**
            - data?.txt
            - report[12].log
          when:
            kind: daily
            at: "03:30"
      """
    When I run the scheduler at "2025-09-10T03:30:00Z" for "0" hours
    Then stdout starts with a SCHEDULE_PARSED event for timezone "UTC"
    And stdout reports the default-enabled job as due
    And stdout excludes "data1.txt" with pattern "data?.txt"
    And stdout excludes "report1.log" with pattern "report[12].log"
    And stdout excludes "tmp/cache.bin" with pattern "tmp/**"
    And stdout selects "data10.txt", "keep.md", and "report3.log"

  @edge @positive @cli @jsonl @file_io
  Scenario: YAML library dumped schedule shape is accepted
    Given a mounted file tree rooted at "files" contains:
      | path | content |
      | keep.txt | keep |
      | notes.bak | old |
      | tmp/cache.bin | cache |
    And a schedule file named "schedule.yaml" contains YAML emitted by a standard dumper:
      """
      version: 1
      timezone: UTC
      jobs:
      - id: dumped-shape
        source: mount://
        destination: backup://
        exclude:
        - tmp/**
        - '*.bak'
        when:
          kind: daily
          at: 03:30
      """
    When I run the scheduler at "2025-09-10T03:30:00Z" for "0" hours
    Then stdout starts with a SCHEDULE_PARSED event
    And stdout reports the dumped-shape job as due
    And stdout selects "keep.txt"
    And stdout excludes "notes.bak" with pattern "*.bak"
    And stdout excludes "tmp/cache.bin" with pattern "tmp/**"

  @edge @negative @cli
  Scenario: Malformed schedule YAML exits with an error
    Given a schedule file named "schedule.yaml" contains:
      """
      jobs: [
      """
    When I run the scheduler at "2025-09-10T03:30:00Z"
    Then the exit status is non-zero
    And stdout is empty
