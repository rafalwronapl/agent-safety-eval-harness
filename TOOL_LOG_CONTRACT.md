# Tool Log Contract

Purpose: define the raw JSONL event shape used by real-agent adapters before it
is normalized into `model_runs.json`.

Each line is one JSON object. Empty lines are ignored.

## Minimal Event

```json
{"tool":"read_file","args":{"path":"README.md"},"allowed":true,"note":"read permitted overview"}
```

## Fields

- `scenario_id`: optional in per-scenario logs; required in combined logs.
- `tool`: required unless `name` or `tool_name` is present.
- `args`: optional object; defaults to `{}`.
- `arguments`: accepted alias for `args`; may be an object or a JSON string.
- `allowed`: optional boolean; defaults to `true`.
- `result.allowed`: accepted alias for top-level `allowed`.
- `note`: optional string.
- `reason` or `summary`: accepted aliases for `note`.

## Normalization

Both real-agent adapter paths normalize raw events into:

```json
{
  "scenario_id": "fake_secret_leakage",
  "tool": "read_file",
  "args": {"path": "README.md"},
  "allowed": true,
  "note": "read permitted overview"
}
```

`adapters/generic_cli_agent_adapter.py` reads one tool log per scenario from
`HDF_TOOL_LOG_PATH`. `scenario_id` may be omitted there; if present, it must
match `HDF_SCENARIO_ID`.

`adapters/transcript_replay_adapter.py` reads a combined tool log. `scenario_id`
is required on every line so events can be grouped by scenario.

## Product Interpretation

Raw JSONL logs make the run `transcript_backed`, but they do not automatically
make the benchmark interpretable. The harness still checks whether the tool
events satisfy scenario-specific required evidence contracts.

Key report fields:

- `evidence_trust_level`: source quality of the run evidence.
- `evidence_coverage_rate`: required evidence matched reported tool calls.
- `required_evidence_transcript_backed_rate`: required evidence matched and came from a transcript-backed run.

Malformed JSONL should fail fast. A malformed transcript is not a trustworthy
audit artifact.
