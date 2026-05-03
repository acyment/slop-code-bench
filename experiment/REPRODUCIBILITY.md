# SCBench Gherkin Drift Pilot Reproducibility

Status:

- EXP-001 complete: canonical upstreams pinned.
- EXP-002 complete: forks and experiment branches were created under `acyment`.
- EXP-003 complete: local experiment directory skeleton exists.
- EXP-004 complete: this reproducibility document exists.
- EXP-070 through EXP-072 complete: protected-file lock checks and dry-run trajectory/subset wrappers exist. These dry runs do not execute model agents or hidden scoring.
- EXP-100 complete as a pre-execution artifact freeze: `experiment/locks/pilot_artifact_freeze.json`.
- EXP-101 blocked by full-pilot preflight until the execution bridge, fixed model/agent config, and C2 snapshot acceptance integration are complete.
- EXP-110 through EXP-111 complete as pre-evidence reporting/archive scaffolds. The current report is not a result analysis of a completed pilot.

This file pins the canonical upstream repositories for the SpecCommons SCBench Gherkin drift pilot. It should be copied unchanged into the eventual experiment branch unless a deliberate upstream refresh is performed.

## Inspection Metadata

- Inspection date: 2026-05-02
- Inspector: Codex
- Source of truth: GitHub API and canonical repository pages
- Local workspace at inspection time: `/Users/acyment/dev/hit-sdd`
- Local workspace git status: root workspace is not a git repository; fork checkouts live under `repos/`

## Canonical Upstreams

### SCBench Runner

- Repository: `SprocketLab/slop-code-bench`
- URL: https://github.com/SprocketLab/slop-code-bench
- API URL: https://api.github.com/repos/SprocketLab/slop-code-bench
- Default branch: `main`
- Pinned branch ref: `main`
- Pinned commit: `03bf1f56752bdb4dc3e607d291870972ddd5f214`
- Pinned commit URL: https://github.com/SprocketLab/slop-code-bench/commit/03bf1f56752bdb4dc3e607d291870972ddd5f214
- Commit date: 2026-04-24T20:31:21Z
- Commit message: `fix(metrics): require last checkpoint for solved problems`
- Latest release observed: `v0.3`
- Latest release URL: https://github.com/SprocketLab/slop-code-bench/releases/tag/v0.3
- Latest release published: 2026-04-21T16:12:17Z
- License observed from repository metadata: MIT
- Role in experiment: agent runner, workspace/session orchestration, hidden pytest evaluation, static metrics, summaries, and result artifacts.

### SCBench Problems

- Repository: `gabeorlanski/scb-problems`
- URL: https://github.com/gabeorlanski/scb-problems
- API URL: https://api.github.com/repos/gabeorlanski/scb-problems
- Default branch: `main`
- Pinned branch ref: `main`
- Pinned commit: `8be2bd10bad43a3c0068bdafd05f8eb065a7dc80`
- Pinned commit URL: https://github.com/gabeorlanski/scb-problems/commit/8be2bd10bad43a3c0068bdafd05f8eb065a7dc80
- Commit date: 2026-04-28T17:39:44Z
- Commit message: `Harbor fixes`
- Latest release observed: `v1.0`
- Latest release URL: https://github.com/gabeorlanski/scb-problems/releases/tag/v1.0
- Latest release published: 2026-04-24T17:46:45Z
- License observed from repository metadata: Apache-2.0
- Role in experiment: checkpoint prose, problem metadata, hidden pytest tests, reference solutions, and static assets.

## Pinning Decision

Use the pinned `main` commits above for the first implementation work.

Rationale:

- The SCBench project currently separates runner logic and problem definitions.
- The project site reports the current benchmark as v1.0, but the runner repository latest release observed is `v0.3` while the problem repository latest release observed is `v1.0`.
- The pinned commits are the exact repository states inspected for the initial backlog and problem-selection plan.
- Commit pins are more precise than floating branch names or release tags.

Do not change these pins during MVP or pilot runs without recording a new inspection block and rerunning the problem inventory.

## Pilot Artifact Freeze

The current pre-execution pilot artifact freeze manifest is:

```text
experiment/locks/pilot_artifact_freeze.json
```

Verify it before any primary data collection:

```bash
uv run python experiment/scripts/freeze_pilot_artifacts.py verify \
  --manifest experiment/locks/pilot_artifact_freeze.json
```

The full-pilot preflight gate is:

```bash
uv run python experiment/scripts/validate_full_pilot_preflight.py \
  --freeze-manifest experiment/locks/pilot_artifact_freeze.json \
  --problems-root ../scb-problems \
  --output-dir experiment/results/m11_full_pilot_preflight
```

Primary data collection is not valid until that gate returns `ready`.

## Current Report And Archive

Current pre-evidence report:

```text
experiment/results/m12_pilot_report/pilot_report.md
```

Current pre-evidence archive:

```text
experiment/results/m12_archive/pre_evidence_archive/
```

These artifacts are useful for reviewing the setup state. They do not contain evidence from implementation-agent trajectories.

## Planned Fork Layout

Actual forks:

- Runner fork: `acyment/slop-code-bench`
- Problems fork: `acyment/scb-problems`

The originally suggested `speccommons` organization was not available in the authenticated account's organization list, so the forks were created in the authenticated user namespace.

Recommended branch in both forks:

```bash
git checkout -b experiment/gherkin-drift-pilot
```

Expected remotes after fork setup:

```text
origin    https://github.com/acyment/<repo>.git
upstream  https://github.com/<canonical-owner>/<repo>.git
```

Local fork checkouts:

- Runner: `/Users/acyment/dev/hit-sdd/repos/slop-code-bench`
- Problems: `/Users/acyment/dev/hit-sdd/repos/scb-problems`

Experiment branch in both forks:

- `experiment/gherkin-drift-pilot`

## Refresh Procedure

Only run this when intentionally updating the experiment base.

```bash
curl -L https://api.github.com/repos/SprocketLab/slop-code-bench/commits/main
curl -L https://api.github.com/repos/gabeorlanski/scb-problems/commits/main
curl -L https://api.github.com/repos/SprocketLab/slop-code-bench/releases/latest
curl -L https://api.github.com/repos/gabeorlanski/scb-problems/releases/latest
```

After refreshing:

1. Update this file with the new commit hashes, dates, messages, and release tags.
2. Rerun the problem inventory.
3. Recheck evaluation output format and metric field names.
4. Regenerate prompt/context hashes.
5. Record the reason for the upstream refresh in the decision log.

## Run Metadata Checklist

Every trajectory run must record:

- `run_id`
- `condition_id`
- `problem_id`
- `checkpoint_id`
- `replicate_id`
- `model`
- `agent_harness`
- `agent_version`
- runner repository URL and commit
- problem repository URL and commit
- experiment repository commit
- prompt template ID and hash
- rendered prompt hash
- feature file hash when applicable
- step definition hash when applicable
- lock manifest hash when applicable
- environment config path and hash
- Docker image digest when available
- start and end timestamps
- token, cost, step, and wall-clock usage when available
- artifact root
- lock verification status

## Known Gaps At EXP-001

- No fork has been created yet.
- This workspace is not a git repository, so there is no local experiment commit.
- GitHub credentials and fork owner have not been authorized.
- Docker image digests and model/agent versions are not yet selected.
- Problem inventory and runtime measurement are not yet complete.
