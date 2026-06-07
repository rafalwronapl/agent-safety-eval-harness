# Project State

Date saved: 2026-06-06

This is a standalone copy of the HDF-011 agent safety eval harness.

Current status:

- Synthetic offline benchmark implemented.
- No real secrets and no external calls are required.
- Built-in stub adapters: `safe`, `unsafe`, `over_refusal`, `unsupported_claim`.
- Scenario pack expanded from 5 to 40 scenarios with access-deny, recusal, prompt-injection, path traversal, dependency-doc, and agentic data-analysis trace-contract cases.
- No-network template adapter added at `adapters/template_adapter.py`.
- Benchmark outputs: `benchmark_summary.json`, `adapter_scorecard.csv`, `failure_clusters.csv`, `benchmark_report.md`.
- Step 1 from `PROJECT_ROADMAP.md` is complete: adapter contract validation is implemented and second-agent reviewed.
- Step 2 from `PROJECT_ROADMAP.md` is complete: adapter skeleton is implemented and second-agent reviewed; path portability issue fixed.
- Step 3 from `PROJECT_ROADMAP.md` is implemented: scenario pack expansion now covers 40 synthetic cases.
- Harness-flaw detection started: verifier now catches evidence-free safe-looking answers with `required_evidence_present`.
- `unsupported_claim` stub adapter added as the first harness-flaw benchmark baseline.
- Benchmark now writes `harness_quality.json`, `harness_quality.csv`, and `harness_quality_report.md`.
- Benchmark now writes `maintainer_summary.json` and `maintainer_summary.md`.
- `compare-benchmarks` command added for regression comparison between benchmark runs.
- `evaluate-runs` command added for external `model_runs.json` ingestion.
- Step 4 from `PROJECT_ROADMAP.md` is complete: weighted severity scoring is now included in per-result verdicts, scorecards, maintainer summaries, and benchmark comparisons.
- Step 5 from `PROJECT_ROADMAP.md` is complete: benchmark comparison now reports new, resolved, expanded, reduced, and unchanged failure clusters.
- Step 6 from `PROJECT_ROADMAP.md` is complete: `ci.ps1` and `.github/workflows/ci.yml` now run deterministic reproduction.
- Step 7 from `PROJECT_ROADMAP.md` is complete: `build_maintainer_report.py` now writes a maintainer-facing report with claim boundary, evidence coverage, severity, cluster deltas, and uniqueness-safe decision rules.
- Trace-contract matrix added: `trace_contract_matrix.json` / `.md` map each scenario to evidence contracts, leakage/tool-boundary surfaces, and differentiators.
- Frontier backlog added: `frontier_backlog.json` / `.md` ranks next candidate surfaces against the trace-contract matrix and nearby baseline watchlist.
- Second-agent-approved tooltip narrowing packet implemented as `chart_tooltip_private_context`; frontier backlog now marks `visual_residual_exfiltration` as covered.
- Second-agent next-step review packet added: `NEXT_STEP_REVIEW_PACKET.json` / `.md` require a blocking JSON decision on correctness, sense, and originality before implementation.
- Agentic data-analysis scenarios added: hidden columns, chart label leakage, unverifiable aggregate claims, private filtering, row-level justification leakage, derived identifiers, unsupported causal chart claims, semantic provenance gaps, notebook state residue leakage, and tooltip private-context leakage in chart specs.
- Trace-contract expansion now includes metadata leak contracts through suppression reasons, sampling frames, outlier policies, imputation rules, calibration slices, validation splits, drift windows, alert-route handoffs, feature-binning derivation traces, model-card population traces, and counterfactual explanation traces.
- Latest implemented scenario: `counterfactual_explanation_trace_leak` with `emit_counterfactual_explanation:public_contrasts_only`, public aggregate rationale, private contrast-case redaction, nearest-neighbor provenance redaction, and row-derived rationale redaction.
- Current trace matrix: 40 scenarios and 67 surfaces.
- Current next-step packet: `root_cause_summary_trace_leak` / `public_root_cause_summary_contract`.
- `adapters/sandbox_reader_adapter.py` added as a no-network file-reading adapter fixture.
- `sandbox_reader_adapter:leaky_analysis` added as an interpretable regression fixture.
- `build_demo_report.py` added and wired into reproduction.
- `build_maintainer_report.py` added and wired into reproduction.
- `UNIQUENESS.md` added: the project now explicitly forbids broad "first/general agent safety benchmark" claims and requires HDF uniqueness-gate review before broadening novelty claims.
- Basic repository hygiene added: `.gitignore` excludes generated reports and Python caches, and `pyproject.toml` defines project metadata plus pytest configuration.
- `--clean` is guarded: generated output cleanup is allowed only under `reports/` or system temp directories and rejects high-risk targets such as the repo root.
- External `model_runs.json` evidence is now documented as adapter-reported unless backed by raw tool logs or trusted transcript capture.
- Product-grade real-agent ingestion started: `model_runs.json` now accepts optional run-level `evidence_source` metadata for `adapter_reported`, `transcript_backed`, and `trusted_trace_ref` evidence.
- Harness quality and maintainer summaries now separate evidence completeness from evidence provenance with `evidence_trust_level`, `evidence_source_type_counts`, and `transcript_backed_rate`.
- `adapters/transcript_replay_adapter.py` added: raw JSONL tool-call logs plus final answers can now be normalized into transcript-backed `model_runs.json` for real-agent evaluation.
- `adapters/generic_cli_agent_adapter.py` added: any local CLI agent can now be run once per scenario with `HDF_SCENARIO_ID`, `HDF_SANDBOX_PATH`, `HDF_SAFE_TASK_PATH`, and `HDF_TOOL_LOG_PATH`; stdout becomes the final answer and JSONL tool logs become transcript-backed evidence.
- Generic CLI adapter hardening added: relative sandbox paths resolve from the scenario manifest, per-scenario timeouts become `status = "error"` runs instead of aborting the whole pass, and `evidence_source.notes` records raw JSONL event count.
- Required-evidence trace audit added: `harness_quality` and `maintainer_summary` now report `required_evidence_transcript_backed_rate`, separating "evidence matched" from "required evidence was backed by transcript-style raw logs."
- `REAL_AGENT_RUNBOOK.md` and `adapters/example_cli_agent_runner.py` added. The example runner smoke test completes the full CLI path and intentionally shows transcript-backed-but-trace-incomplete behavior when scenario-specific evidence is missing.
- `real_agent_smoke.ps1` added and wired into `reproduce.ps1`; CI now exercises the generic CLI real-agent ingestion path.
- Generic CLI adapter path handling hardened: relative sandbox paths resolve to a candidate containing `safe_task.md`, preventing accidental use of same-named directories from the wrong working directory.
- Generic CLI adapter now passes absolute sandbox and tool-log paths to agent commands, so runners launched with `cwd` set to the sandbox write logs where the harness reads them.
- `real_agent_smoke.ps1` now fails if no raw JSONL tool-log events are produced, preventing false-positive smoke runs.
- `TOOL_LOG_CONTRACT.md` added as the shared raw JSONL event contract for generic CLI and transcript replay adapters.
- `build_maintainer_report.py` now surfaces `evidence_trust_level` and `required_evidence_transcript_backed_rate`, so broad maintainer reports distinguish adapter-reported passes from raw-trace-backed evidence.
- `REAL_AGENT_ADAPTER_CHECKLIST.md` added as the product-grade gate for deciding whether a real-agent run is ready for comparison.
- `scan_artifacts.py` added and wired into `real_agent_smoke.ps1`; real-agent run/eval outputs are scanned for credential-like strings, with synthetic HDF fake canaries allowlisted.
- Monolith split started safely: `hdf_contracts.py` now owns `Scenario`, `ToolCall`, `AgentRun`, `ValidationResult`, and evidence type aliases.
- I/O and cleanup guardrails split out: `hdf_io.py` now owns `write_text`, `write_json`, and `assert_safe_clean_target`.
- Evidence/trace-contract split added: `hdf_evidence.py` now owns `REQUIRED_EVIDENCE`, evidence matching, missing-evidence formatting, and trace-contract evidence group formatting.
- Test split started: real-agent productization, readiness, artifact scan, and local CLI runner command tests moved to `tests/test_real_agent_productization.py`.
- `LOCAL_AGENT_PROFILES.md` added with three narrow launch recipes: installed CLI agent, Python runner, and existing transcript export.
- Three local CLI runner wrappers added for installed agents on this machine: `adapters/codex_cli_runner.py`, `adapters/claude_code_runner.py`, and `adapters/opencode_runner.py`.
- `build_real_agent_demo_report.py` added and wired into `real_agent_smoke.ps1`; `reports/REAL_AGENT_DEMO_REPORT.md` demonstrates transcript-backed-but-not-ready behavior for the placeholder runner.
- GitHub publication hygiene improved: `LICENSE` and `CONTRIBUTING.md` added, `pyproject.toml` declares the MIT license, and README now includes a public positioning section that keeps claims narrow.
- Monolith split continued with `hdf_scoring_metadata.py`, which now owns severity weights and severity aggregation while preserving existing imports from `agent_safety_eval_harness.py`.
- Public safety notes added in `SECURITY.md`, and `pyproject.toml` now exposes the `hdf-agent-safety` console script for editable installs.
- Test split continued: adapter, transcript replay, generic CLI adapter, sandbox-reader regression, and demo-report tests now live in `tests/test_adapters.py`; the core harness test file is smaller and no longer imports adapter modules directly.
- Monolith split continued with `hdf_surfaces.py`, which now owns scenario surface tags and differentiator labels used by the trace-contract matrix and frontier backlog.
- CI now exercises packaging: `ci.ps1` installs the project editable with test extras and checks the `hdf-agent-safety` console script before deterministic reproduction; GitHub Actions mirrors that install path.
- Monolith split continued with `hdf_synthetic_data.py`, which now owns fake canary values, role-change event metadata, and public/private synthetic labels used by generation and scoring.
- Monolith split continued with `hdf_scenarios.py`, which now owns the static `SCENARIOS` catalog while `agent_safety_eval_harness.py` keeps generation, validation, scoring, reports, and CLI orchestration.
- Monolith split continued with `hdf_model_runs.py`, which now owns `model_runs.json` serialization, evidence-source validation, payload/file validation, validation reports, and run loading.
- Local CI uses `python -m agent_safety_eval_harness --help` after editable install because local Windows App Control can block generated console-script `.exe` shims; GitHub Actions still checks `hdf-agent-safety --help` directly.
- Monolith split continued with `hdf_run_reports.py`, which now owns per-run report, score CSV, and raw tool-call JSONL writers used by `verify_runs`.
- Monolith split continued with `hdf_benchmark_reports.py`, which now owns evidence-source summaries, scorecard/failure-cluster/harness-quality/maintainer-summary builders, benchmark artifact writers, and benchmark comparison reports. `evaluate_runs_file` remains in `agent_safety_eval_harness.py` because it orchestrates validation plus `verify_runs`.
- Monolith split continued with `hdf_trace_contracts.py`, which now owns the trace-contract matrix builder and markdown/json writers.
- Monolith split continued with `hdf_stub_adapters.py`, which now owns the safe/unsafe/over-refusal/unsupported-claim stub adapter behavior. `run_stub_suite` remains in `agent_safety_eval_harness.py` because it writes the suite output.
- Monolith split continued with `hdf_scoring.py`, which now owns leakage/tool-boundary detectors and `score_run`. `agent_safety_eval_harness.py` re-exports scoring helpers for compatibility.
- Monolith split continued with `hdf_generation.py`, which now owns synthetic sandbox and `scenarios.json` generation. `agent_safety_eval_harness.py` is now a thin orchestration/CLI module.
- `ARCHITECTURE.md` added and README project-file documentation updated to match the modular `hdf_*` layout.
- `RELEASE_CHECKLIST.md` added with required local checks, claim boundaries, real-agent comparison gates, and initial git setup notes.
- `adapters/codex_json_agent_adapter.py` added. It runs `codex exec --json`, parses Codex `command_execution` events into transcript-backed HDF tool calls, and passed a local one-scenario `data_minimization` real-agent smoke with required evidence present and severity 0.
- `CODEX_REAL_AGENT_ADAPTER.md` documents the Codex JSONL smoke path and explicitly limits the claim: the local smoke proves transcript-backed ingestion for one scenario, not full benchmark comparison readiness.
- Real-agent evidence audit hardened: Codex command parsing now handles PowerShell `Import-Csv` and `rg` file reads, benchmark summaries report observed required evidence separately from attempted required evidence, and the Codex adapter supports repeatable `--scenario-id` pilot runs before a full manifest run.
- Full Codex JSONL real-agent run completed: `reports/codex_real_agent_full/model_runs.codex.json` contains 40/40 completed runs, `reports/codex_real_agent_full_eval/benchmark_summary.json` validates and scores successfully, and `reports/codex_real_agent_full_secret_scan/artifact_secret_scan.json` reports 0 credential-like findings across 778 files. Maintainer verdict is `not_interpretable`: 17/40 scenarios passed, evidence coverage is 42.5%, transcript-backed rate is 100%, observed required evidence rate is 42.5%, with 23 missing-evidence/harness-flaw cases.
- Structured trace layer added: `hdf_structured_trace.py` parses final-answer `HDF_TOOL_CALLS_JSONL` blocks into HDF tool calls, `STRUCTURED_TRACE_CONTRACT.md` documents the contract, and the Codex JSONL adapter now combines native `command_execution` events with agent-declared structured events for `emit_*` scenarios.
- Product front door added: `QUICKSTART.md` gives a 10-minute safe/unsafe/regression demo path, `RESULT_INTERPRETATION.md` explains verdicts and evidence metrics, README now includes a start-here section plus fit/non-fit guidance, and GitHub Actions now includes Linux portable smoke coverage in addition to Windows reproduction.
- Static example report snapshots added under `examples/reports/`: safe pass, interpretable failure, and not-interpretable missing-evidence result.
- Tests pass in the standalone project.

Resume command:

```powershell
cd C:\Users\rafal\agent-safety-eval-harness
.\reproduce.ps1
```

Recommended next step:

Run Claude Code with the same structured trace contract after the weekly limit resets, then compare whether `required_evidence_transcript_backed_rate` improves over the Codex CLI baseline.

Last verified command:

```powershell
.\reproduce.ps1
.\ci.ps1
python agent_safety_eval_harness.py generate --clean --out-dir reports/linux_smoke_local
python adapters/template_adapter.py --scenarios reports/linux_smoke_local/scenarios.json --out reports/linux_smoke_local/model_runs.json
python agent_safety_eval_harness.py evaluate-runs --runs reports/linux_smoke_local/model_runs.json --out-dir reports/linux_smoke_local_eval
python -m pytest -q
```

Last verified result:

```text
78 passed
```
