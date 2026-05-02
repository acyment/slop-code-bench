# Risk Register

| ID | Risk | Impact | Mitigation |
| --- | --- | --- | --- |
| R01 | Gherkin adds information not present in original spec. | C1/C2 may look better because of extra requirements, not format/harness. | Maintain a conversion ledger classifying every example; add later information-parity Gherkin ablation. |
| R02 | Visible tests encourage overfitting. | C2 may pass visible checks while hidden correctness degrades. | Keep hidden SCBench tests final; track hidden failure after visible pass; vary visible examples where possible. |
| R03 | Agent modifies the harness. | C2 condition becomes invalid. | Hash locked files before/after every checkpoint; mark run invalid on changes. |
| R04 | Refactoring prompts introduce behavior changes. | C3/C4 may conflate refactoring with new bugs. | Refactor-only prompts require all visible checks and hidden scorer evaluation; analyze C3 separately from C0-C2. |
| R05 | Problem selection bias. | Pilot may overstate or understate benefits. | Predefine selection criteria; report excluded problems; expand after MVP; pair conditions by problem. |
| R06 | Metrics do not capture meaningful technical drift. | Results may miss real maintainability changes. | Reuse SCBench verbosity/erosion first; add change amplification, dependency creep, and runtime growth; inspect examples qualitatively. |
| R07 | Hidden tests conflict with Gherkin interpretation. | C2 may be penalized for a plausible but incompatible reading. | During conversion, map scenarios to original prose; after failures, classify conflict vs implementation defect without changing scores. |
| R08 | Benchmark repo structure makes clean integration hard. | Experiment changes may contaminate SCBench comparability. | Keep additions under `experiment/`; wrap existing commands; document unavoidable upstream changes. |
| R09 | Cost/runtime becomes too high. | Full pilot may be unaffordable. | Run MVP first; cap replicates; choose 5-6 moderate problems; record cost per trajectory before scaling. |
| R10 | Results do not generalize across models. | One-harness pilot may reflect model-specific behavior. | State limits clearly; add second model/harness only after pipeline is stable. |
| R11 | C2 acceptance harness itself is buggy or brittle. | Agent may be steered toward wrong behavior. | Maintainer-authored steps; run steps against reference solutions; include harness error classification. |
| R12 | Checkpoint configs disable prior tests for some problems. | Regression metrics become inconsistent. | Flag such problems in selection; C2 should still run prior Gherkin scenarios; analyze separately. |
| R13 | Service/API tasks are flaky. | False regressions and noisy survival estimates. | Prefer CLI MVP; use deterministic ports, timeouts, teardown; classify infrastructure failures. |
| R14 | Benchmark contamination concerns. | Public docs might accidentally expose benchmark details. | Do not copy hidden tests into public prompts; avoid publishing complete problem specs beyond upstream licensing norms. |

