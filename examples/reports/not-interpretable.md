# Example: Not Interpretable

This snapshot shows the most important evidence-first distinction: a real-agent
run can be transcript-backed and still not be comparison-ready.

Source shape: Codex CLI JSONL full run before structured trace coverage.

| adapter | verdict | pass rate | evidence coverage | evidence trust | transcript-backed runs | behavior failures | safety failures | evidence failures |
|---|---|---:|---:|---|---:|---:|---:|---:|
| `codex_cli:json_transcript` | `not_interpretable` | 42% | 42% | `transcript_backed` | 100% | 3 | 3 | 23 |

How to read it:

- `transcript_backed` means the adapter preserved raw execution evidence.
- `not_interpretable` means required scenario evidence is still missing.
- Do not compare model quality from this run until logging or structured trace coverage improves.

Why it happened:

Codex CLI emitted native shell command events, but many HDF scenarios require
domain-level structured events such as:

- `emit_schema_report`
- `emit_join_plan`
- `emit_metric_card`
- `emit_provenance`
- `emit_access_decision`

Those are not native shell commands. Real-agent adapters can now ask the agent
to emit them through the final-answer `HDF_TOOL_CALLS_JSONL` block documented in
`STRUCTURED_TRACE_CONTRACT.md`.

Reading rule:

If evidence quality is weak, fix logging first. If evidence quality is strong,
treat behavior failures as meaningful synthetic regressions.
