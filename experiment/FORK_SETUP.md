# Fork Setup Runbook

Status: EXP-002 complete.

On 2026-05-02, forks were created under the authenticated user namespace because the proposed `speccommons` organization was not available to the account.

## Authentication Note

`gh api` authenticated successfully as `acyment`. `gh auth status` still reported an invalid default token in this shell, so verification used `gh api user` and repository API calls.

Authenticated user: `acyment`

## Actual Forks

- Runner fork: `acyment/slop-code-bench`
- Problems fork: `acyment/scb-problems`

## Fork Commands Used

Runner:

```bash
gh api -X POST repos/SprocketLab/slop-code-bench/forks
```

Problems:

```bash
gh api -X POST repos/gabeorlanski/scb-problems/forks
```

## Clone And Branch Commands Used

Runner:

```bash
git clone --branch experiment/gherkin-drift-pilot https://github.com/acyment/slop-code-bench.git repos/slop-code-bench
cd repos/slop-code-bench
git remote add upstream https://github.com/SprocketLab/slop-code-bench.git
```

Problems:

```bash
git clone --branch experiment/gherkin-drift-pilot https://github.com/acyment/scb-problems.git repos/scb-problems
cd repos/scb-problems
git remote add upstream https://github.com/gabeorlanski/scb-problems.git
```

Remote branches were created with:

```bash
gh api -X POST repos/acyment/slop-code-bench/git/refs \
  -f ref=refs/heads/experiment/gherkin-drift-pilot \
  -f sha=03bf1f56752bdb4dc3e607d291870972ddd5f214

gh api -X POST repos/acyment/scb-problems/git/refs \
  -f ref=refs/heads/experiment/gherkin-drift-pilot \
  -f sha=8be2bd10bad43a3c0068bdafd05f8eb065a7dc80
```

## Verification Commands

Run in each clone:

```bash
git remote -v
git rev-parse HEAD
git branch --show-current
```

Expected runner HEAD:

```text
03bf1f56752bdb4dc3e607d291870972ddd5f214
```

Expected problems HEAD:

```text
8be2bd10bad43a3c0068bdafd05f8eb065a7dc80
```

Expected branch:

```text
experiment/gherkin-drift-pilot
```
