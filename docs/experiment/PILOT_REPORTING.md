# Pilot Reporting

Status: Milestone 12 reporting scaffold.

The current report is a pre-evidence report. It validates reporting and archival mechanics, but it does not analyze an evidence-producing full pilot because EXP-101 remains blocked by the full-pilot gate.

## Generate Report

```bash
uv run python experiment/scripts/generate_pilot_report.py \
  --analysis-summary experiment/results/m10_mvp_dry_run/analysis/summary.json \
  --analysis-dir experiment/results/m10_mvp_dry_run/analysis \
  --preflight experiment/results/m11_full_pilot_preflight/preflight.json \
  --freeze-manifest experiment/locks/pilot_artifact_freeze.json \
  --output-dir experiment/results/m12_pilot_report
```

Outputs:

- `experiment/results/m12_pilot_report/pilot_report.md`
- `experiment/results/m12_pilot_report/report_summary.json`

The report explicitly marks the claim status as `not_tested` when no hidden SCBench evaluation results are available.

## Archive Artifacts

```bash
uv run python experiment/scripts/archive_artifacts.py \
  --output-dir experiment/results/m12_archive/pre_evidence_archive
```

Outputs:

- `experiment/results/m12_archive/pre_evidence_archive/archive_manifest.json`
- `experiment/results/m12_archive/pre_evidence_archive/archive_manifest.md`
- `experiment/results/m12_archive/pre_evidence_archive/files/`

The archive intentionally excludes common secret-bearing filenames and cache/build artifacts. It does not archive raw API credentials or local agent auth files.

## Evidence Rule

The final pilot report cannot claim support for the research hypothesis until:

1. the full-pilot preflight returns `ready`,
2. C0/C1/C2 trajectories have executed,
3. hidden SCBench evaluations are exported,
4. visible C2 acceptance results are linked to agent checkpoint snapshots,
5. cost/runtime data are present where the agent harness exposes them.
