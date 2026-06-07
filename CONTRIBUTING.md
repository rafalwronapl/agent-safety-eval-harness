# Contributing

This repository is a narrow, synthetic, offline regression harness for
agent-safety trace contracts. Keep changes aligned with that claim.

## Development

Run the deterministic local check before opening a change:

```powershell
.\ci.ps1
```

For a faster test-only loop:

```powershell
python -m pytest -q
```

## Scenario Changes

New scenarios should:

- use generated fake data only;
- define explicit expected checks;
- define required evidence in `hdf_evidence.py`;
- exercise a data-analysis or tool-boundary trace contract;
- avoid broad benchmark or exploitability claims.

Prefer scenarios that expose a missing trace, access-boundary, data
minimization, or maintainer-debugging failure mode. Generic prompt-injection
or secret-leak cases are only useful when they add a distinct evidence
contract.

## Adapter Changes

Real-agent adapters must not be treated as comparison-ready unless their tool
events are transcript-backed or backed by a trusted trace reference. Adapter
self-reporting is useful for smoke tests, but reports must keep it separate
from transcript-backed evidence.

Adapters should write `model_runs.json` using the schema documented in
`SCHEMAS.md` and raw tool events using `TOOL_LOG_CONTRACT.md`.

## Claim Boundary

Allowed claim: this is an offline, synthetic, evidence-first regression harness
for agent data-analysis and tool-boundary failures.

Do not claim:

- first or general agent-safety benchmark;
- proof of real exploitability;
- proof that an agent or product is secure;
- full real-agent tool-call coverage unless the adapter emits complete
  transcript-backed tool events.
