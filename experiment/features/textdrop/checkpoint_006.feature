@problem_textdrop @checkpoint_006
Feature: Pluggable storage backends and creation timestamps

  Background:
    Given the HTTP service is running

  @core @positive @api @storage
  Scenario: Local store persists notes and displays creation timestamp
    Given the service is started with "--store local:./data"
    When I create a note with plain text content "hello"
    And I request the stored note view
    Then the HTML page includes a visible UTC creation timestamp with no fractional seconds
    When I request the raw text endpoint for the note
    Then the response body is exactly "hello"
    And the raw text response does not include the timestamp

  @core @positive @api @storage
  Scenario: Object store validates container and uses normalized object paths
    Given the service is started with an "object" store JSON config
    And the object container HEAD request returns 200
    When I create a note
    Then the backend receives a PUT to "{url}/{container}/{noteID}.json"
    And the object payload includes content, mode, and created_at
    When I request the note
    Then the backend receives a GET to "{url}/{container}/{noteID}.json"
    And the HTTP behavior matches the local storage backend

  @edge @negative @storage
  Scenario Outline: Invalid storage configuration fails before the server accepts requests
    Given the service is started with store spec "<store_spec>"
    When startup validation runs
    Then the process exits non-zero
    And stderr contains a storage configuration error
    And no HTTP server is started

    Examples:
      | store_spec |
      | missing_separator |
      | unknown:/tmp |
      | object:{not-json} |
      | object:{"url":"http://store","key_id":"k","key_secret":"s"} |

  @edge @negative @api @storage
  Scenario Outline: Runtime backend failures map to deterministic HTTP errors
    Given storage startup validation has succeeded
    And the backend operation "<operation>" fails at runtime
    When the client performs "<request>"
    Then the response status is 500
    And the response body is the standard user-facing HTML status page

    Examples:
      | operation | request |
      | write | POST /submit |
      | read | GET /n/{noteID} |
      | read | GET /n/{noteID}/text |

