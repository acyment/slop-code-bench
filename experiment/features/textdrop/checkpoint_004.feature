@problem_textdrop @checkpoint_004
Feature: Documentation static assets robots policy and debug mode

  Background:
    Given the HTTP service is running

  @core @positive @api @markdown
  Scenario Outline: Bundled documentation pages render through the markdown pipeline
    When I request "GET <route>"
    Then the response status is 200
    And the response body is a complete HTML document
    And the HTML head contains OpenGraph title and description tags

    Examples:
      | route |
      | /about |
      | /help/formatting |

  @core @positive @api
  Scenario: Static assets and favicon have MIME-specific content types
    When I request "GET /static/style.css"
    Then the response status is 200
    And the Content-Type starts with "text/css"
    When I request "GET /favicon.ico"
    Then the response status is 200
    And the Content-Type is "image/x-icon"

  @core @positive @api
  Scenario: Robots policy is fixed plain text
    When I request "GET /robots.txt"
    Then the response status is 200
    And the Content-Type starts with "text/plain"
    And the response body exactly matches the configured crawler policy

  @edge @negative @api
  Scenario: Missing debug files do not fall back to bundled resources
    Given the service is running with "--debug"
    And a required debug documentation or static file is missing
    When I request the corresponding route
    Then the response status is 404
    And the response body is the standard complete HTML 404 page

