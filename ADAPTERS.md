# Adapter Interface

The harness is adapter-driven. An adapter turns one synthetic scenario into one `AgentRun` record.

Current built-in adapter:

- `adapter_stub:safe`
- `adapter_stub:unsafe`
- `adapter_stub:over_refusal`
- `adapter_stub:unsupported_claim`

Template adapter:

- `adapters/template_adapter.py`
- no network calls;
- reads generated `scenarios.json`;
- writes a contract-valid `model_runs.json`;
- intended as the copy/paste starting point for real model adapters;
- demonstrates adapter contract shape, not real model quality or safety.

Sandbox reader adapter:

- `adapters/sandbox_reader_adapter.py`
- no network calls;
- reads generated sandbox files from disk;
- computes simple safe answers for the synthetic scenarios;
- intended as a repository-backed fixture for `evaluate-runs`.

Transcript replay adapter:

- `adapters/transcript_replay_adapter.py`
- no network calls;
- converts raw JSONL tool-call logs plus final answers into `model_runs.json`;
- writes `evidence_source.type = "transcript_backed"` for every run;
- intended as the first integration point for real agent runners and framework-specific adapters.

Generic CLI agent adapter:

- `adapters/generic_cli_agent_adapter.py`
- `adapters/example_cli_agent_runner.py` shows the minimal command-side contract;
- runs any command once per generated scenario;
- passes scenario paths through environment variables;
- captures stdout as the final answer;
- reads per-scenario raw JSONL tool logs from `HDF_TOOL_LOG_PATH`;
- writes `evidence_source.type = "transcript_backed"` for every run;
- records per-run raw event count in `evidence_source.notes`;
- treats a per-scenario command timeout as `status = "error"` for that run and continues the remaining scenarios.

## Required Run Shape

```json
{
  "scenario_id": "fake_secret_leakage",
  "adapter": "adapter_name:variant",
  "status": "completed",
  "final_answer": "text shown to user",
  "evidence_source": {
    "type": "transcript_backed",
    "trace_source": "local_tool_logger",
    "raw_tool_log_path": "logs/tool_calls.jsonl",
    "notes": "raw_tool_log_event_count=1"
  },
  "tool_calls": [
    {
      "scenario_id": "fake_secret_leakage",
      "tool": "read_file",
      "args": {"path": "README.md"},
      "allowed": true,
      "note": "why this call happened"
    }
  ]
}
```

`evidence_source` is optional. If it is absent, the harness treats the run as
`adapter_reported`: useful for offline regression, but weaker than a run built
from preserved raw logs.

Accepted evidence source types:

- `adapter_reported`: the adapter reports `tool_calls` directly.
- `transcript_backed`: the adapter built the run from a raw tool log; requires `raw_tool_log_path`.
- `trusted_trace_ref`: the adapter links the run to a trusted external trace; requires `trusted_trace_ref`.

Allowed optional text fields are `trace_source`, `trusted_trace_ref`,
`raw_tool_log_path`, and `notes`.

For raw JSONL event details, see `TOOL_LOG_CONTRACT.md`.

For the generic CLI adapter, `notes` includes `raw_tool_log_event_count=N`.
An empty raw log can still be a real transcript of "no tools called", but it
will not satisfy scenario-specific required-evidence contracts.

## Integration Rule

Real model adapters should write `model_runs.json` in this shape, then call:

```powershell
python .\agent_safety_eval_harness.py validate-runs --runs .\path\to\model_runs.json --out-dir .\reports\model_eval
python .\agent_safety_eval_harness.py evaluate-runs --runs .\path\to\model_runs.json --out-dir .\reports\model_eval
```

Do not put real secrets in sandbox data or model outputs. The verifier is designed for synthetic canaries only.

Evidence limitation: `tool_calls` are adapter-reported unless `evidence_source`
marks them as transcript-backed or tied to a trusted trace reference. The
harness checks consistency, completeness, and scenario-specific evidence
contracts, but it does not independently prove that a reported external tool
call really executed. For production-grade audits, build adapters from raw tool
logs and preserve the original transcript outside `model_runs.json`.

## Template Adapter

```powershell
python .\agent_safety_eval_harness.py generate --clean --out-dir .\reports\template_adapter_run
python .\adapters\template_adapter.py --scenarios .\reports\template_adapter_run\scenarios.json --out .\reports\template_adapter_run\model_runs.json
python .\agent_safety_eval_harness.py validate-runs --runs .\reports\template_adapter_run\model_runs.json --out-dir .\reports\template_adapter_run
python .\agent_safety_eval_harness.py verify --runs .\reports\template_adapter_run\model_runs.json --out-dir .\reports\template_adapter_run
```

## Sandbox Reader Adapter

```powershell
python .\agent_safety_eval_harness.py generate --clean --out-dir .\reports\sandbox_reader_run
python .\adapters\sandbox_reader_adapter.py --scenarios .\reports\sandbox_reader_run\scenarios.json --out .\reports\sandbox_reader_run\model_runs.json --adapter-id sandbox_reader_adapter:regression_subject
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\sandbox_reader_run\model_runs.json --out-dir .\reports\sandbox_reader_eval
python .\adapters\sandbox_reader_adapter.py --scenarios .\reports\sandbox_reader_run\scenarios.json --out .\reports\sandbox_reader_run\model_runs.leaky_analysis.json --variant leaky_analysis --adapter-id sandbox_reader_adapter:regression_subject
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\sandbox_reader_run\model_runs.leaky_analysis.json --out-dir .\reports\sandbox_reader_leaky_eval
python .\agent_safety_eval_harness.py compare-benchmarks --base .\reports\sandbox_reader_eval --candidate .\reports\sandbox_reader_leaky_eval --out-dir .\reports\sandbox_reader_regression
```

The `leaky_analysis` variant intentionally leaks synthetic analysis labels or
asserts an unverifiable aggregate while keeping evidence coverage complete. It
is a regression fixture, not a safe adapter.

Use `--adapter-id` when comparing safe and leaky variants as the same logical
adapter; otherwise comparison treats them as distinct adapters.

## Transcript Replay Adapter

Use this adapter when a real agent runner can save:

- one final answer per scenario; and
- one raw JSONL event per tool call.

```powershell
python .\agent_safety_eval_harness.py generate --clean --out-dir .\reports\real_agent_run
python .\adapters\transcript_replay_adapter.py --scenarios .\reports\real_agent_run\scenarios.json --tool-log .\reports\real_agent_run\tool_calls.jsonl --answers .\reports\real_agent_run\answers.json --out .\reports\real_agent_run\model_runs.json --adapter-id my_agent:run_001 --trace-source my_agent_tool_logger
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\real_agent_run\model_runs.json --out-dir .\reports\real_agent_eval
```

Minimal `tool_calls.jsonl` event:

```json
{"scenario_id":"fake_secret_leakage","tool":"read_file","args":{"path":"README.md"},"allowed":true,"note":"read permitted overview"}
```

The adapter also accepts `name` or `tool_name` instead of `tool`, `arguments`
instead of `args`, and `result.allowed` instead of top-level `allowed`. This
keeps the replay path portable across agent frameworks while still normalizing
to the harness contract.
The full shared event contract is documented in `TOOL_LOG_CONTRACT.md`.

Minimal `answers.json`:

```json
{
  "fake_secret_leakage": {
    "status": "completed",
    "final_answer": "The agent's final response for this scenario."
  }
}
```

The answers file must cover every scenario in `scenarios.json`. Tool calls may
be empty for a scenario, but then the harness will likely mark the result as
trace-incomplete because required evidence is missing.

## Generic CLI Agent Adapter

Use this adapter when the agent can be launched as a local command. The adapter
runs the command once per scenario and sets these environment variables:

- `HDF_SCENARIO_ID`
- `HDF_SANDBOX_PATH`
- `HDF_SAFE_TASK_PATH`
- `HDF_TOOL_LOG_PATH`

The command should print the final answer to stdout and write one JSONL event
per tool call to `HDF_TOOL_LOG_PATH`.

```powershell
python .\agent_safety_eval_harness.py generate --clean --out-dir .\reports\generic_cli_run
$runner = (Resolve-Path .\my_agent_runner.py).Path
python .\adapters\generic_cli_agent_adapter.py --scenarios .\reports\generic_cli_run\scenarios.json --out .\reports\generic_cli_run\model_runs.json --trace-dir .\reports\generic_cli_run\raw_traces --adapter-id my_cli_agent:run_001 --trace-source my_cli_tool_logger -- python $runner
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\generic_cli_run\model_runs.json --out-dir .\reports\generic_cli_eval
```

Minimal agent-side tool log event:

```json
{"tool":"read_file","args":{"path":"README.md"},"allowed":true,"note":"read permitted overview"}
```

`scenario_id` is optional in per-scenario logs. If present, it must match
`HDF_SCENARIO_ID`. The adapter also accepts `name` or `tool_name` instead of
`tool`, `arguments` instead of `args`, and `result.allowed` instead of top-level
`allowed`.
The full shared event contract is documented in `TOOL_LOG_CONTRACT.md`.

For a real adapter, replace `run_model_placeholder` in `template_adapter.py`.
Keep credentials in environment variables or an external secret store, never in
the generated sandbox or committed files.

The template adapter intentionally returns simple safe placeholder answers. Its
full verifier pass only proves the adapter contract and no-network skeleton
work; it is not evidence about any real model or product.

For real adapters, prefer `evaluate-runs` over raw `verify`. It produces the
validation report, scenario verdicts, harness quality report, maintainer
summary, and benchmark-compatible summary in one run.

## Validation Rules

`validate-runs` rejects:

- malformed JSON;
- non-list payloads;
- empty payloads;
- unknown `scenario_id` values;
- missing required fields;
- unsupported extra fields;
- incomplete adapter runs, meaning each adapter present in a file must submit exactly one run for every known scenario;
- adapter IDs with leading or trailing whitespace;
- duplicate adapter/scenario pairs;
- status values outside `completed`, `refused`, `error`;
- malformed tool calls;
- tool-call `scenario_id` values that do not match the parent run.

A single `model_runs.json` may contain one adapter or multiple adapters. Multi-adapter
files are useful for benchmark aggregation, but every adapter in the file must
cover the full scenario set so pass rates cannot be inflated by partial runs.
