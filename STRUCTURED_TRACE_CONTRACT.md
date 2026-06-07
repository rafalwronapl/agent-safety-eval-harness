# Structured Trace Contract

Real-agent adapters may capture two kinds of evidence:

- native tool events from the agent runtime, such as shell command executions;
- agent-declared HDF structured events embedded in the final transcript.

The second form is for scenarios that need domain decisions the shell cannot
emit by itself, for example `emit_schema_report`, `emit_join_plan`,
`emit_metric_card`, or `emit_provenance`.

## Final Answer Block

After the normal answer, the agent may append:

```text
HDF_TOOL_CALLS_JSONL_START
{"tool":"emit_provenance","args":{"claim":"claim_to_columns","columns":["segment","risk_score"]},"allowed":true,"note":"Mapped the public claim to permitted columns only."}
HDF_TOOL_CALLS_JSONL_END
```

Rules:

- one JSON object per line;
- required fields: `tool`, `args`, `allowed`, `note`;
- `args` must be an object;
- `allowed` must be a boolean;
- do not include secrets, private row values, names, emails, restricted file
  content, or private aliases in `args` or `note`;
- emit only events that the agent actually justified from local files, task
  text, or explicit sandbox policy/events.

## Trust Boundary

These events are transcript-backed because they come from the preserved raw
agent transcript. They are still agent-declared, not independently executed
system calls. The harness keeps this distinction by also preserving native tool
events and by reporting evidence coverage separately from behavior failures.
