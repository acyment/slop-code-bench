@problem_file_merger @checkpoint_003
Feature: Partitioned and sharded output

  Background:
    Given the command line tool is available

  @core @positive @cli @file_io
  Scenario: Partition rows into Hive-style directories
    Given input rows contain country and dt fields
    When I run the merger with "--partition-by country,dt" and "--output out"
    Then "out" is a directory
    And rows are written under directories like "country=US/dt=2025-01-01"
    And null partition values use "_null"
    And unsafe path characters are percent-encoded
    And each partition file has the resolved schema header

  @core @positive @cli @file_io
  Scenario: Shard output by row count and byte count
    Given sorted input rows exceed the configured part limits
    When I run the merger with "--max-rows-per-file 2" and "--max-bytes-per-file 128"
    Then files are named "part-00000.csv", "part-00001.csv", and so on
    And each file contains at most two data rows unless a single row exceeds the byte limit
    And cutting occurs at the earliest row or byte boundary that would violate a limit

  @edge @negative @cli
  Scenario: Partitioning cannot write to stdout
    Given any partitioning flag is provided
    When I run the merger with "--output -"
    Then the exit status is non-zero
    And stderr reports that partitioned output requires a directory path

  @core @positive @cli
  Scenario: Field-partitioned outputs are sorted within each partition
    Given rows from different partitions are interleaved in the input
    When I run the merger with "--partition-by account_id" and "--key created_at,id"
    Then each partition directory contains rows sorted by the key within that partition
    And global order across partitions is not required

