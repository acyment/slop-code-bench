@problem_textdrop @checkpoint_003
Feature: Metadata OpenGraph table of contents and preview rendering

  Background:
    Given the HTTP service is running

  @core @positive @api @markdown
  Scenario: Stored markdown note exposes extracted title preview and OpenGraph tags
    When I submit markdown content:
      """
      # Project Setup Guide

      This guide walks through initial configuration for new contributors.

      ## Prerequisites
      """
    And I request the stored note view
    Then the HTML head contains "<title>Project Setup Guide</title>"
    And the HTML head contains an OpenGraph title with "Project Setup Guide"
    And the HTML head contains an OpenGraph description with the first paragraph text

  @core @positive @api @markdown
  Scenario: TOC directive renders navigation and removes directive text
    When I submit markdown with a standalone "{{ toc 2 3 }}" directive and matching headings
    And I request the stored note view
    Then the HTML body contains a "nav.table-of-contents" element
    And the navigation contains links to heading fragment IDs in levels 2 through 3
    And the literal "{{ toc" directive text is absent from the rendered page

  @core @positive @api
  Scenario: Render endpoint previews without storing content
    When I submit a JSON request to "POST /render":
      """
      {"body":"Just a quick note about the deployment schedule.","mode":"markdown"}
      """
    Then the response status is 200
    And the HTML title is "TextDrop - Preview"
    And the OpenGraph title is "TextDrop"
    And no note ID is generated or persisted

  @edge @negative @api
  Scenario: GET render is not a route
    When I request "GET /render"
    Then the response status is 404
    And the response body is a complete HTML document

