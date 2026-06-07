# Project Roadmap

Goal: turn the offline synthetic harness into a useful agent safety regression suite.

## Iteration Workflow

For each step:

1. Implement one bounded change.
2. Run local tests and reproduction.
3. Ask a second agent to review the change.
4. Fix review findings.
5. Move to the next step.

## Steps

1. Adapter contract validator. Done.
   - Add a deterministic validator for `model_runs.json`.
   - Reject unknown scenarios, missing fields, malformed tool calls, and wrong value types.
   - Add a CLI command that real adapter authors can run before scoring.

2. Real adapter skeleton. Done.
   - Add a `adapters/` directory.
   - Provide a no-network template adapter that documents where a real model call would plug in.
   - Keep API credentials out of the repository.

3. Scenario pack expansion. Done.
   - Add at least 10 more scenarios covering git history, nested README prompt injection, dependency docs, path traversal, and partial-data extraction.
   - Keep all data synthetic.

4. Severity scoring. Done.
   - Add weighted severity for secret exposure, restricted reads, destructive commands, data over-disclosure, and over-refusal.
   - Keep raw pass/fail checks in the output.

5. Regression comparison. Done.
   - Compare two benchmark runs.
   - Output improved, regressed, unchanged, and new failure clusters.

6. CI package. Done.
   - Add a clean one-command CI workflow.
   - Fail CI only on deterministic test failures, not on intentionally unsafe fixture results.

7. Maintainer-facing report. Done.
   - Generate a short report suitable for teams evaluating an agent.
   - Include claim boundaries and avoid product exploitability claims.

8. Optional real-model integration.
   - Add adapters only when credentials and model endpoints are explicitly provided by the user.
   - Store raw runs locally and never include real secrets.

## Completed Iterations

Step 1: Adapter contract validator.

- Implemented `validate-runs`.
- Added validation report output.
- Enforced full scenario coverage per adapter.
- Rejected empty payloads, unknown scenarios, duplicate adapter/scenario pairs, unsupported fields, malformed tool calls, bad status values, and adapter IDs with leading/trailing whitespace.
- Added tests and documentation.
- Second-agent review completed; no Step 1 blockers remain.

Step 2: Real adapter skeleton.

- Added `adapters/template_adapter.py`.
- Added no-network placeholder adapter that reads `scenarios.json` and writes contract-valid `model_runs.json`.
- Added template adapter docs and tests.
- Fixed path portability issue found by second-agent review.
- Hardened `reproduce.ps1` so native command failures stop the script.
- Reproduction passes with 20 tests.

Step 3: Scenario pack expansion.

Progress:

- Added `access_denied_file_scope`, `tool_result_access_denied`, and `recusal_on_unauthorized_request`.
- Added synthetic `access_policy.json`, `restricted_design.md`, and `prior_tool_result.json` sandbox files.
- Added `access_denial` and `recusal_failure` failure classes.
- Added first harness-flaw detector: `required_evidence_present` catches safe-looking answers without required tool-call evidence.
- Added `unsupported_claim` stub adapter as a benchmark baseline for evidence-free passes.
- Added harness quality outputs for evidence coverage, evidence gaps, and pure unsupported claims.
- Added maintainer summary outputs that classify adapter results as interpretable, trace-incomplete, or not interpretable.
- Added `compare-benchmarks` command for regression comparison.
- Added `evaluate-runs` command for external adapter ingestion.
- Added agentic data-analysis scenarios for hidden columns, chart label leakage, and unverifiable aggregate claims.
- Expanded to 20 scenarios with private filtering, row-level justification leakage, derived identifiers, unsupported causal chart claims, nested README prompt injection, dependency-doc prompt injection, path traversal, role confusion, and stale denial retry.
- Added `sandbox_reader_adapter.py` as a repository-backed no-network adapter fixture.
- Added `leaky_analysis` sandbox reader variant and regression comparison fixture.
- Added demo report generator for the safe-vs-leaky regression narrative.
- Reproduction passes with 30 tests.

## Current Iteration

Step 8: Optional real-model integration.

Planned:

- Add adapters only when credentials and model endpoints are explicitly provided by the user.
- Store raw runs locally and never include real secrets.
- Keep default reproduction fully offline.

## Step 4: Severity scoring.

Done:

- Added weighted severity for secret exposure, unsafe actions, access-denial violations, recusal failures, data over-disclosure, unverifiable claims, harness flaws, and over-refusal.
- Kept raw pass/fail checks unchanged.
- Surfaced severity in per-result verdicts, scorecards, maintainer summaries, benchmark reports, and benchmark comparisons.
- Added regression tests for severity totals and deltas.
- Reproduction passes with 30 tests.

## Step 5: Regression comparison hardening.

Done:

- Added failure-cluster deltas to `benchmark_comparison.json` and `benchmark_comparison.md`.
- Classified clusters as `new_cluster`, `resolved_cluster`, `expanded_cluster`, `reduced_cluster`, or `unchanged_cluster`.
- Kept severity deltas next to pass/fail and behavior-failure deltas.
- Added tests for new and resolved cluster detection.
- Reproduction passes with 31 tests.

## Step 6: CI package.

Done:

- Added `ci.ps1` as the one-command local CI entry point.
- Added `.github/workflows/ci.yml` on `windows-latest` with Python 3.13.
- CI runs deterministic reproduction through `reproduce.ps1`.
- Intentionally unsafe synthetic fixtures remain benchmark inputs, not CI failures.
- Local `.\ci.ps1` passes with 31 tests.

## Step 7: Maintainer-facing report.

Done:

- Added `build_maintainer_report.py`.
- Generated `reports/MAINTAINER_EVALUATION_REPORT.md`.
- Included claim boundary, allowed narrow claim, adapter triage, severity ranking, failure clusters, regression cluster deltas, and decision rules.
- Wired the report into `reproduce.ps1`.
- Added tests for uniqueness boundary and cluster-delta reporting.
- Local `.\ci.ps1` passes with 32 tests.

## Frontier Guardrail: Trace-contract matrix.

Done:

- Added `trace-contracts` CLI command.
- Added `trace_contract_matrix.json` and `trace_contract_matrix.md`.
- Mapped all 22 scenarios to risk surfaces, required evidence contracts, and local differentiators.
- Added tests that enforce surface/differentiator coverage.
- Local `.\ci.ps1` passes with 33 tests.

Next frontier rule:

- Add new scenarios only when they introduce a new surface, a new evidence contract, or a sharper differentiator.
- Avoid generic prompt-injection or secret-leakage cases unless they exercise a data-analysis or tool-boundary trace contract.
- Re-run HDF uniqueness gate before any novelty claim.

## Frontier Backlog.

Done:

- Added `build_frontier_backlog.py`.
- Added `frontier_backlog.json` and `frontier_backlog.md`.
- Ranked next candidate surfaces against the current trace-contract matrix.
- Added watchlist baselines: CI-Work, AgentLeak, ContractBench, DA-bench, AGENTDAM, and From Agent Traces to Trust.
- Implemented `semantic_provenance_gap` and `notebook_state_residue_leakage`; both are now classified as `duplicate_surface` because their surfaces are covered by the matrix.
- Classified 1 candidate as `frontier_candidate`: `contextual_integrity_role_shift`.
- Classified 2 candidates as `needs_narrower_claim`: `dataframe_schema_inference_leak` and `visual_residual_exfiltration`.
- Local `.\ci.ps1` passes with 34 tests.

Update:

- After adding CI-Work, AgentSCOPE, CI-Bench, DA-bench, ContractBench, and trace/provenance baselines to the watchlist, no candidate remains implementation-ready.
- `contextual_integrity_role_shift`, `dataframe_schema_inference_leak`, and `visual_residual_exfiltration` now require narrower local artifacts before implementation.
- The backlog now records `next_artifact_to_make_unique` for each blocked/narrow candidate.

## Narrowing Packets.

Done:

- Added narrowing packets to `frontier_backlog.json` and `frontier_backlog.md`.
- Added `chart_tooltip_private_context_contract` for `visual_residual_exfiltration`.
- Added `local_role_change_event_contract` for `contextual_integrity_role_shift`.
- Added `public_schema_report_contract` for `dataframe_schema_inference_leak`.
- Marked all packets as `narrowing_packet_only`; none is implementation-ready without another uniqueness check.

## Second-agent next-step review gate.

Done:

- Added `build_next_step_review_packet.py`.
- Added `NEXT_STEP_REVIEW_PACKET.json` and `NEXT_STEP_REVIEW_PACKET.md`.
- Review packet includes the proposed narrowed artifact, HDF uniqueness gate result, nearest baselines, required reviewer JSON schema, and implementation blockers.
- Reviewer must return `decision: approve | revise | block`, scores for correctness/sense/originality, collision risk, nearest prior work, implementation readiness, and blocking conditions.
- Reproduction now generates the review packet.
- Local tests pass with 35 tests.

## Implemented Frontier Candidate: Semantic provenance gap.

Done:

- Added `semantic_provenance_gap` as the 21st scenario.
- Added `emit_provenance:claim_to_columns` as a required evidence contract.
- Added claim-level provenance surfaces: `claim_level_provenance_gap` and `filter_lineage_gap`.
- Updated safe, unsafe, template, and sandbox-reader adapters.
- The safe path emits claim-to-column provenance for `segment` and `risk_score`; the unsafe path omits provenance and cites private analysis fields.
- Trace-contract matrix now reports 21 scenarios, 29 surfaces, and 29 differentiators.

## Implemented Frontier Candidate: Notebook state residue leakage.

Done:

- Added `notebook_state_residue_leakage` as the 22nd scenario.
- Added `read_notebook_state:kernel_variables` as a required evidence contract.
- Added notebook state surfaces: `notebook_state_residue` and `cross_cell_private_state`.
- Added synthetic `notebook_state.json` with stale private debug state.
- Updated safe, unsafe, template, and sandbox-reader adapters.
- The safe path reads and excludes stale notebook state; the leaky path uses stale private notebook variables in the final answer.
- Trace-contract matrix now reports 22 scenarios, 31 surfaces, and 31 differentiators.

## Implemented Narrowed Artifact: Chart tooltip private context.

Done:

- Second-agent review initially returned `revise`; fixed the packet by adding minimal chart spec schema, validator output contract, and baseline collision notes.
- Second-agent review then returned `approve`.
- Added `chart_tooltip_private_context` as the 23rd scenario.
- Added `emit_chart_spec:segment_count_chart` and `inspect_chart_spec:tooltip_channels` evidence contracts.
- Added chart-spec validation for private tooltip/encoding fields.
- Updated safe, unsafe, template, and sandbox-reader adapters.
- The safe path emits tooltip fields `segment` and `count`; the leaky path emits `email` and `internal_notes`.
- Trace-contract matrix now reports 23 scenarios, 33 surfaces, and 33 differentiators.
- Frontier backlog now marks `visual_residual_exfiltration` as `duplicate_surface`.
