@problem_textdrop @checkpoint_002
Feature: Markdown rendering and JSON submissions

  Background:
    Given the HTTP service is running

  @core @positive @api @markdown
  Scenario: Submit markdown as JSON and render supported inline and block elements
    When I submit a JSON request to "POST /submit":
      """
      {"body":"# My Note\n\nSome **bold** text and a [link](https://example.com).","mode":"markdown"}
      """
    Then the response status is 302
    When I request "GET /n/{noteID}"
    Then the HTML body contains "<h1 id=\"my-note\">My Note</h1>"
    And the HTML body contains "<strong>bold</strong>"
    And the HTML body contains "<a href=\"https://example.com\">link</a>"

  @core @positive @api @markdown
  Scenario: Language-tagged fenced code blocks contain token span wrappers
    When I submit markdown content with a fenced code block tagged "python"
    And I request the stored note view
    Then the rendered code block is inside "pre code"
    And the rendered code block contains span elements around tokens

  @core @positive @api @markdown
  Scenario: Duplicate heading slugs are not disambiguated
    When I submit markdown with two headings that slugify to "install"
    And I request the stored note view
    Then both heading elements have id "install"

  @edge @negative @api
  Scenario Outline: Invalid input format or mode is rejected
    When I submit a request to "POST /submit" with "<condition>"
    Then the response status is 400
    And the response body is a complete HTML document

    Examples:
      | condition |
      | unsupported Content-Type |
      | unsupported markdown mode |
      | invalid UTF-8 body |
      | whitespace-only content |

