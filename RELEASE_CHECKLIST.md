# Release Checklist

Use this before publishing the repository or comparing real-agent results.

## Required Local Checks

```powershell
.\ci.ps1
python -m pip wheel . --no-deps --wheel-dir .\reports\package_smoke
```

Expected result:

- editable install succeeds;
- deterministic reproduction writes reports;
- real-agent CLI smoke completes;
- pytest passes;
- wheel build succeeds.

## Claim Check

Allowed public description:

> Offline synthetic, evidence-first regression harness for coding-agent
> data-analysis and tool-boundary failures.

Do not claim:

- general or first agent-safety benchmark;
- proof of exploitability;
- proof that an agent or product is secure;
- full real-agent tool-call coverage unless the adapter emits complete
  transcript-backed tool events or a trusted trace reference.
- structured `emit_*` coverage unless the run includes raw native tool events
  or final-answer `HDF_TOOL_CALLS_JSONL` blocks that satisfy
  `STRUCTURED_TRACE_CONTRACT.md`.

## Real-Agent Comparison Gate

A real-agent run is comparison-ready only when:

- `model_runs.json` validates;
- required evidence is transcript-backed or has a trusted trace reference;
- artifact secret scan has zero credential-like findings;
- `build_real_agent_readiness.py` marks the adapter ready;
- raw traces have been reviewed before publication.
- structured trace blocks have been reviewed for private-data leakage and
  unsupported self-claims.

## Repository Setup

This directory may not already be a git repository. Before publishing:

```powershell
git init
git add .
git commit -m "Initial release"
```

Review generated artifacts before committing. `reports/` is ignored by default.
