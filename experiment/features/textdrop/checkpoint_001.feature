@problem_textdrop @checkpoint_001
Feature: Plain text note sharing service

  Background:
    Given the HTTP service is running

  @core @positive @api
  Scenario: Submit form text and retrieve rendered and raw note views
    When I submit a form request to "POST /submit":
      | field | value |
      | content | Hello, world! |
      | mode | |
    Then the response status is 302
    And the Location header matches "/n/{noteID}"
    When I request "GET /n/{noteID}"
    Then the response status is 200
    And the Content-Type starts with "text/html"
    And the HTML body contains the escaped note inside "pre code"
    When I request "GET /n/{noteID}/text"
    Then the response status is 200
    And the Content-Type is "text/plain; charset=utf-8"
    And the response body is exactly "Hello, world!"

  @core @positive @api
  Scenario: Health endpoint returns active JSON
    When I request "GET /health"
    Then the response status is 200
    And the Content-Type starts with "application/json"
    And the response body is JSON:
      """
      {"status":"active"}
      """

  @edge @negative @api
  Scenario Outline: Invalid submissions return user-facing HTML errors
    When I submit a form request to "POST /submit":
      | field | value |
      | content | <content> |
      | mode | <mode> |
    Then the response status is 400
    And the response body is a complete HTML document

    Examples:
      | content | mode |
      |         |      |
      | hello | unsupported |

  @edge @negative @api
  Scenario: Unregistered route returns complete HTML 404 page
    When I request "GET /missing"
    Then the response status is 404
    And the response body is a complete HTML document

