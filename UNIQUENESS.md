# Uniqueness Boundary

This project must not claim to be a new general agent-safety benchmark.

Nearby baselines already cover broad agent safety, prompt injection, MCP/tool
poisoning, privacy leakage, and agent security benchmarking. The intended
differentiation is narrower:

- evidence-first scoring with scenario-specific required tool-call traces;
- local regression harness for data-analysis leakage and tool-boundary failures;
- synthetic hidden-column, chart-label, aggregate-claim, access-deny, recusal,
  path-traversal, nested-prompt, and stale-denial scenarios;
- maintainer-oriented outputs that separate model behavior failures from
  harness flaws such as evidence-free safe-looking answers;
- safe-vs-leaky regression comparison where behavior gets worse while evidence
  coverage remains sufficient.

## Must Not Claim

- "First agent safety benchmark."
- "General solution to agent security evaluation."
- "Proof that a product can be hacked."
- "Comprehensive MCP poisoning benchmark."
- "Real enterprise privacy benchmark."

## Allowed Claim

This is a synthetic, offline, evidence-first regression harness for local
data-analysis/tool-boundary trace contracts in coding/data agents, currently
focused on hidden/private analysis columns, claim-level provenance, and
notebook/kernel state residue.

## Current Differentiators

- 22 local synthetic scenarios.
- Required evidence contracts per scenario.
- Adapter validation before scoring.
- Harness-quality report for missing evidence and unsupported claims.
- Maintainer summary with `interpretable_pass`, `trace_incomplete`,
  `not_interpretable`, and `interpretable_with_failures` verdicts.
- Benchmark comparison that detects regressions under the same adapter ID.
- Trace-contract matrix for scenario surfaces and evidence contracts.
- Frontier backlog that marks implemented candidate surfaces as covered.

## Current Collision Status

The HDF uniqueness gate currently reports `needs_narrower_claim` after adding
DA-bench, CI-Work, ContractBench, and agent trace/provenance baselines. This
project should therefore avoid broad data-analytics, privacy, trace, or agent
safety benchmark claims.

## Required Review Before Broadening Claims

Before adding any public-facing novelty language, run the HDF uniqueness gate:

```powershell
cd C:\Users\rafal\hard-discovery-factory
python .\ai_it_application_radar.py --run-dir .\runs\loop_2026-06-05_222416
python .\ai_it_uniqueness_gate.py
```

Then give `NEXT_AGENT_UNIQUENESS_REVIEW_PROMPT.md` to a second agent and require
it to search for close prior work.
