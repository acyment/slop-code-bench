@problem_textdrop @checkpoint_005
Feature: Operational drain and signed user identity

  Background:
    Given the HTTP service is running

  @core @positive @api
  Scenario: Authorized drain changes health endpoints only
    Given the service is configured with ops secret "s3cretvalue"
    When I request "GET /_ops/drain" with Authorization "Bearer s3cretvalue"
    Then the response status is 200
    And the response body is JSON:
      """
      {"status":"ok"}
      """
    When I request "GET /health"
    Then the response status is 404
    And the response body is JSON:
      """
      {"status":"drained"}
      """
    When I request "GET /_health"
    Then the response status is 404
    And the response body is JSON:
      """
      {"status":"drained"}
      """
    And other note routes continue to function normally

  @edge @negative @api
  Scenario Outline: Unauthorized drain returns JSON 401
    Given the service is configured with ops secret "s3cretvalue"
    When I request "GET /_ops/drain" with "<authorization>"
    Then the response status is 401
    And the response body is JSON:
      """
      {"error":"unauthorized"}
      """

    Examples:
      | authorization |
      | no Authorization header |
      | malformed Authorization header |
      | Bearer wrong-secret |

  @core @positive @api
  Scenario: User identity cookie is issued and preserved when id seed is configured
    Given the service is configured with id seed "my-seed-value"
    When I create a note without a user_id cookie
    Then the 302 response sets a URL-safe "user_id" cookie
    When I create another note with that valid "user_id" cookie
    Then the valid token is preserved or re-sent unchanged

  @regression @positive @api
  Scenario: User tracking is inactive without id seed
    Given the service is running without id seed
    When I create a note
    Then no "user_id" cookie is set

