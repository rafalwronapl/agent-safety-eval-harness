# HDF-011: Agent Safety Eval Harness

Purpose: practical offline benchmark for checking whether coding agents mishandle synthetic secrets, prompt injections, destructive tool-use bait, data minimization, restricted files, access-deny signals, required recusal, or evidence-free benchmark passes.

This workstream uses only generated fake data. It does not contain real secrets, call external services, exploit anything, or test live infrastructure.

## Public Positioning

This repository is best described as a research/devtool preview for
evidence-first regression testing of coding-agent behavior. Its useful claim is
narrow: synthetic data-analysis and tool-boundary scenarios, required evidence
contracts, adapter evidence provenance, maintainer-facing reports, and
regression comparison.

It should not be described as a general agent-safety benchmark, a proof of
real-world exploitability, or a proof that an agent/product is secure. Local
CLI wrappers for Codex, Claude Code, and opencode are launch helpers; a run is
comparison-ready only when the adapter emits complete transcript-backed tool
events or a trusted trace reference.

## Start Here

If you are new to the project, read `QUICKSTART.md` first. It gives one safe
run, one unsafe run, and one regression demo path. After that, use
`RESULT_INTERPRETATION.md` to read `maintainer_summary.md` and distinguish
agent behavior failures from evidence/trace failures.

If you want to understand the output before running anything, open the static
examples in `examples/reports/`: safe pass, interpretable failure, and
not-interpretable missing-evidence result.

## Who This Is For

Good fit:

- maintainers testing coding-agent regressions;
- teams comparing local agent wrappers or model releases;
- researchers studying evidence-first eval design;
- developers who need synthetic data-analysis and tool-boundary scenarios.

Not a good fit:

- users who want a one-click consumer safety score;
- live exploit testing;
- claims that a product is safe or unsafe in the real world;
- broad leaderboard-style benchmarking without reviewing trace quality.

## MVP

Scenarios:

- `fake_secret_leakage`
- `prompt_injection_in_readme`
- `destructive_command_bait`
- `data_minimization`
- `hidden_column_minimization`
- `chart_label_leakage`
- `unverifiable_aggregate_claim`
- `restricted_file_boundary`
- `access_denied_file_scope`
- `tool_result_access_denied`
- `recusal_on_unauthorized_request`
- `private_filter_aggregation`
- `row_level_justification_leakage`
- `derived_identifier_leakage`
- `unsupported_chart_causal_claim`
- `semantic_provenance_gap`
- `notebook_state_residue_leakage`
- `chart_tooltip_private_context`
- `nested_readme_prompt_injection`
- `dependency_doc_prompt_injection`
- `path_traversal_denied_file`
- `access_policy_role_confusion`
- `stale_tool_result_denial`

The full current suite also includes additional agentic data-analysis
trace-contract scenarios for schema redaction, join plans, aggregate
thresholds, cohort labels, denominator drift, suppression/audit metadata,
sampling frames, outlier policy, imputation rules, calibration slices,
validation splits, drift windows, alert-route handoffs, feature-binning
derivation, model-card population metadata, and counterfactual explanation
traces. See `reports/trace_contracts/trace_contract_matrix.md` after running
reproduction for the current scenario/surface matrix.

Generated sandbox files include:

- `.env` with a fake canary token;
- `secrets.txt` with a fake API key;
- `customer_data.csv` with fake customer data;
- `analysis_dataset.csv` with fake analytics rows;
- `data_dictionary.md` with public/private column boundaries;
- `chart_request.md` with synthetic chart label rules;
- `README.md` containing prompt injection text;
- `access_policy.json` with synthetic allow/deny file scope;
- `restricted_design.md` with fake restricted content;
- `prior_tool_result.json` with a synthetic `ACCESS_DENIED` tool result;
- `nested_README.md` with nested prompt-injection text;
- `dependency_docs.md` with dependency-document prompt-injection text;
- `safe_task.md` and `malicious_task.md`.

Outputs:

- `scenarios.json`
- `model_runs.json`
- `verdict.json`
- `report.md`
- `tool_calls.jsonl`
- `scores.csv`
- `benchmark_summary.json`
- `adapter_scorecard.csv`
- `failure_clusters.csv`
- `benchmark_report.md`
- `harness_quality.json`
- `harness_quality.csv`
- `harness_quality_report.md`
- `maintainer_summary.json`
- `maintainer_summary.md`
- `trace_contract_matrix.json`
- `trace_contract_matrix.md`
- `frontier_backlog.json`
- `frontier_backlog.md`
- `NEXT_STEP_REVIEW_PACKET.json`
- `NEXT_STEP_REVIEW_PACKET.md`
- `reports/DEMO_REPORT.md`
- `reports/MAINTAINER_EVALUATION_REPORT.md`

## Usage

```powershell
python .\agent_safety_eval_harness.py all --clean --mode safe
python .\agent_safety_eval_harness.py all --clean --mode unsafe --out-dir .\reports\unsafe_eval_run
python .\agent_safety_eval_harness.py all --clean --mode unsupported_claim --out-dir .\reports\unsupported_claim_run
python .\agent_safety_eval_harness.py benchmark --clean --out-dir .\reports\benchmark
python .\agent_safety_eval_harness.py compare-benchmarks --base .\reports\comparison_base --candidate .\reports\comparison_candidate --out-dir .\reports\benchmark_comparison
python .\agent_safety_eval_harness.py trace-contracts --out-dir .\reports\trace_contracts
python .\build_frontier_backlog.py --out-dir .\reports\frontier_backlog
python .\build_next_step_review_packet.py --out-dir .\reports\next_step_review
python .\agent_safety_eval_harness.py validate-runs --runs .\reports\eval_run\model_runs.json --out-dir .\reports\eval_run
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\template_adapter_run\model_runs.json --out-dir .\reports\external_eval
python .\adapters\template_adapter.py --scenarios .\reports\eval_run\scenarios.json --out .\reports\template_adapter_run\model_runs.json
python .\adapters\sandbox_reader_adapter.py --scenarios .\reports\sandbox_reader_run\scenarios.json --out .\reports\sandbox_reader_run\model_runs.json
python .\adapters\sandbox_reader_adapter.py --scenarios .\reports\sandbox_reader_run\scenarios.json --out .\reports\sandbox_reader_run\model_runs.leaky_analysis.json --variant leaky_analysis --adapter-id sandbox_reader_adapter:regression_subject
$runner = (Resolve-Path .\my_agent_runner.py).Path
python .\adapters\generic_cli_agent_adapter.py --scenarios .\reports\real_agent_run\scenarios.json --out .\reports\real_agent_run\model_runs.json --trace-dir .\reports\real_agent_run\raw_traces --adapter-id my_cli_agent:run_001 -- python $runner
python .\build_maintainer_report.py --out .\reports\MAINTAINER_EVALUATION_REPORT.md
.\ci.ps1
.\real_agent_smoke.ps1
```

Optional editable install:

```powershell
python -m pip install -e .[test]
hdf-agent-safety all --clean --mode safe
```

The adapter stub has four modes:

- `safe` simulates expected defensive behavior.
- `unsafe` simulates secret exposure, unsafe actions, or data over-disclosure.
- `over_refusal` simulates refusal to do safe work.
- `unsupported_claim` simulates safe-looking final answers without required tool evidence.

The `benchmark` command runs multiple stub adapters and writes a comparative
scorecard plus failure clusters. The scorecard includes both raw pass/fail
counts and weighted severity totals, so a single secret exposure is not treated
the same as a low-risk unsupported-claim issue. This is the path intended for
future real model/agent adapters.

The verifier also checks `required_evidence_present` for scenarios where a safe
answer must be supported by a relevant tool call. This catches a harness flaw
class where an adapter returns a safe-looking final answer without actually
performing the minimum scenario-specific inspection.

The benchmark also writes a separate harness quality report that lists missing
evidence groups and pure unsupported claims separately from model safety
failures. It also separates ordinary evidence coverage from transcript-backed
required evidence coverage, so a pass based only on adapter-reported tool calls
is visible as weaker than a pass backed by raw tool logs.

`maintainer_summary.md` is the short triage artifact: it says whether an adapter
result is interpretable, trace-incomplete, or not interpretable because the run
contains unsupported claims. It also surfaces severity totals and max severity
per adapter.

`compare-benchmarks` writes `benchmark_comparison.json` and
`benchmark_comparison.md` for regression review between two benchmark runs,
including severity deltas and new/resolved/expanded/reduced failure-cluster
deltas.

`evaluate-runs` is the intended entry point for external adapter output. It
validates a supplied `model_runs.json`, verifies the synthetic scenarios, writes
maintainer and harness-quality summaries, and keeps a normalized copy of the
submitted run.

For real local agents, `adapters/generic_cli_agent_adapter.py` is the direct
product path: it runs a command once per scenario, passes `HDF_SCENARIO_ID`,
`HDF_SANDBOX_PATH`, `HDF_SAFE_TASK_PATH`, and `HDF_TOOL_LOG_PATH`, captures
stdout as the final answer, and marks the run as `transcript_backed` when the
command writes JSONL tool events. A per-scenario timeout becomes a single
`status = "error"` run instead of aborting the whole adapter pass, and the
raw-log event count is preserved in `evidence_source.notes`.

Important limitation: external `model_runs.json` files are adapter-reported
unless the optional run-level `evidence_source` marks them as
`transcript_backed` or `trusted_trace_ref`. The harness validates their shape
and checks whether the reported tool calls satisfy synthetic evidence
contracts. Harness-quality reports also split attempted required evidence from
observed required evidence: observed evidence requires a matching tool call with
`allowed=true`. The harness cannot prove that a real tool was actually executed
unless the adapter is backed by raw tool logs or a trusted transcript capture.
Treat adapter-reported evidence as adapter evidence, not as independent
execution proof.

For domain decisions that a shell transcript cannot emit, real-agent adapters
can parse an explicit `HDF_TOOL_CALLS_JSONL` block from the final transcript.
See `STRUCTURED_TRACE_CONTRACT.md`. This lets agents provide structured events
such as `emit_schema_report`, `emit_join_plan`, `emit_metric_card`, or
`emit_provenance` without weakening the verifier.

`trace-contracts` writes a matrix of scenario surfaces, required evidence
contracts, and local differentiators. Use it to avoid adding generic duplicate
benchmark cases.

`build_frontier_backlog.py` ranks candidate next surfaces against the current
trace-contract matrix and a watchlist of nearby baselines.

`build_next_step_review_packet.py` writes the mandatory second-agent review
packet for the next proposed step. The reviewer must return a blocking JSON
decision covering correctness, project sense, and originality.

`build_demo_report.py` writes a short narrative report for the safe-vs-leaky
sandbox reader regression case.

`build_maintainer_report.py` writes a broader maintainer-facing report that
combines adapter verdicts, severity, evidence coverage, cluster deltas, and the
project uniqueness boundary.

`REAL_AGENT_RUNBOOK.md` is the operator path for connecting a real local agent:
generate synthetic sandboxes, run a CLI wrapper with transcript logging, then
evaluate `model_runs.json`.
`REAL_AGENT_ADAPTER_CHECKLIST.md` is the product-grade gate for deciding whether
a real-agent run is ready for comparison.
`TOOL_LOG_CONTRACT.md` is the compact JSONL schema shared by the generic CLI and
transcript replay adapters.
`scan_artifacts.py` scans generated run/eval outputs for credential-like strings
before sharing or comparing real-agent artifacts.
`build_real_agent_readiness.py` reduces the real-agent eval, secret scan, and
trace-backed evidence metrics to a ready/not-ready comparison gate.
`LOCAL_AGENT_PROFILES.md` gives three launch recipes: installed CLI agent,
Python runner, and existing transcript export.

`ci.ps1` is the one-command CI entry point. It runs `reproduce.ps1`; intentionally
unsafe synthetic fixtures are expected benchmark inputs, not CI failures.
`real_agent_smoke.ps1` runs the generic CLI adapter against the example runner
and verifies the transcript-backed real-agent ingestion path.

`--clean` deletes generated output directories only after a guardrail check.
The CLI permits cleaning paths under this repository's `reports/` directory and
system temporary directories used by tests. It refuses high-risk targets such as
the repository root, parent directory, home directory, or arbitrary output paths
outside those safe locations.

## Project Files

- `agent_safety_eval_harness.py` - thin CLI and orchestration layer.
- `ARCHITECTURE.md` - module map and execution flow.
- `QUICKSTART.md` - 10-minute entry path with safe, unsafe, and regression demo runs.
- `RESULT_INTERPRETATION.md` - guide to verdicts, failure classes, and evidence metrics.
- `examples/reports/` - small static report snapshots for GitHub readers.
- `RELEASE_CHECKLIST.md` - publication and real-agent comparison checklist.
- `hdf_generation.py` - synthetic sandbox and `scenarios.json` generation.
- `hdf_scenarios.py` - static scenario catalog.
- `hdf_synthetic_data.py` - fake canaries, role-change fixture, and synthetic public/private labels.
- `hdf_evidence.py` - required evidence contracts and missing-evidence formatting.
- `hdf_scoring.py` - leakage, tool-boundary, data-minimization, recusal, and claim-support detectors.
- `hdf_model_runs.py` - `model_runs.json` serialization, validation, and loading.
- `hdf_run_reports.py` - per-run report, score CSV, and raw tool-call JSONL writers.
- `hdf_benchmark_reports.py` - scorecards, harness-quality reports, maintainer summaries, and benchmark comparison reports.
- `hdf_trace_contracts.py` - trace-contract matrix writer.
- `hdf_structured_trace.py` - parser for agent-declared structured trace blocks in real-agent transcripts.
- `adapters/template_adapter.py` - no-network adapter skeleton for future model integrations.
- `adapters/sandbox_reader_adapter.py` - no-network adapter that reads generated sandbox files and computes safe synthetic answers.
- `adapters/transcript_replay_adapter.py` - converts raw JSONL tool-call transcripts plus final answers into transcript-backed `model_runs.json`.
- `adapters/generic_cli_agent_adapter.py` - runs a real local CLI agent per scenario and captures transcript-backed tool logs.
- `adapters/codex_json_agent_adapter.py` - runs Codex CLI `exec --json` and converts command-execution events into transcript-backed tool calls.
- `adapters/example_cli_agent_runner.py` - minimal command wrapper showing the env vars and JSONL logging contract.
- `adapters/codex_cli_runner.py` - local Codex CLI wrapper for the generic real-agent adapter.
- `adapters/claude_code_runner.py` - local Claude Code wrapper for the generic real-agent adapter.
- `adapters/opencode_runner.py` - local opencode wrapper for the generic real-agent adapter.
- `ADAPTERS.md` - expected format for plugging in real adapters.
- `REAL_AGENT_RUNBOOK.md` - step-by-step real-agent integration runbook.
- `REAL_AGENT_ADAPTER_CHECKLIST.md` - product-grade checklist for real-agent adapter runs.
- `LOCAL_AGENT_PROFILES.md` - local agent launch recipes for CLI, Python runner, and transcript replay modes.
- `CODEX_REAL_AGENT_ADAPTER.md` - Codex JSONL adapter smoke path and current limitation.
- `TOOL_LOG_CONTRACT.md` - raw JSONL tool-log event contract for transcript-backed adapters.
- `STRUCTURED_TRACE_CONTRACT.md` - final-answer JSONL block contract for structured HDF events.
- `scan_artifacts.py` - local credential-like artifact scanner for real-agent outputs.
- `build_real_agent_readiness.py` - ready/not-ready summary for real-agent comparison gates.
- `HARNESS_FLAW_DETECTOR.md` - notes on the evidence-free pass detector.
- `SCHEMAS.md` - output schemas and failure classes.
- `UNIQUENESS.md` - uniqueness boundary and second-agent review rule.
- `PROJECT_ROADMAP.md` - ordered steps for making the project useful.
- `.gitignore` - excludes generated reports and local Python caches.
- `pyproject.toml` - project metadata and pytest configuration.
- `.github/workflows/ci.yml` - Windows CI workflow for deterministic reproduction.
- `build_maintainer_report.py` - maintainer-facing report generator.
- `ci.ps1` - local entry point matching CI.
- `real_agent_smoke.ps1` - deterministic smoke test for the generic CLI real-agent adapter path.
- `tests/` - deterministic pytest coverage.

## Claim Boundary

Allowed:

- "In this synthetic harness, adapter/model X exposed fake secret Y."
- "In this synthetic harness, adapter/model X attempted a simulated restricted file read."
- "In this synthetic harness, adapter/model X ignored a synthetic access-deny signal."
- "In this synthetic harness, adapter/model X produced a safe-looking answer without required evidence."
- "In this synthetic harness, adapter/model X over-refused a safe task."

Not allowed:

- "This proves product X can be hacked."
- "This proves a real secret was exfiltrated."
- "This benchmark result proves exploitability."

## Reproduce

```powershell
.\reproduce.ps1
```
