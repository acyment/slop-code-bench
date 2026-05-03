# Acceptance Steps

This directory contains maintainer-authored acceptance helper code for C2 and
later conditions. Implementation agents must not modify these files during
experiment trajectories.

Milestone 6 provides the helper substrate:

- `acceptance/cli.py`: command execution, artifact capture, JSONL parsing, and
  CLI assertions.
- `acceptance/api.py`: local HTTP service startup, health polling, requests,
  teardown, and server log capture.
- `acceptance/results.py`: scenario result records and JSONL writing.

Full feature parsing and automatic step dispatch are deferred to runner
integration. The smoke runner exercises these helpers directly against pinned
reference solutions.

