# Local Agent Profiles

These profiles are thin launch recipes for `adapters/generic_cli_agent_adapter.py`.
They do not claim official integration with any vendor or framework. The real
requirement is always the same: your runner must print the final answer to
stdout and write JSONL tool events to `HDF_TOOL_LOG_PATH`.

## Profile 1: Installed CLI Agent

Use this when the agent is available as a command on `PATH`.

```powershell
python .\agent_safety_eval_harness.py generate --clean --out-dir .\reports\local_cli_agent
python .\adapters\generic_cli_agent_adapter.py --scenarios .\reports\local_cli_agent\scenarios.json --out .\reports\local_cli_agent\model_runs.json --trace-dir .\reports\local_cli_agent\raw_traces --adapter-id local_cli_agent:run_001 --trace-source local_cli_jsonl -- my-agent-command --task-file $env:HDF_SAFE_TASK_PATH
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\local_cli_agent\model_runs.json --out-dir .\reports\local_cli_agent_eval
python .\scan_artifacts.py .\reports\local_cli_agent .\reports\local_cli_agent_eval --out-dir .\reports\local_cli_agent_secret_scan
python .\build_real_agent_readiness.py --eval-dir .\reports\local_cli_agent_eval --secret-scan-dir .\reports\local_cli_agent_secret_scan --out-dir .\reports\local_cli_agent_readiness
```

If the CLI cannot write JSONL tool events directly, wrap it with a small script
that converts its tool callbacks, logs, or structured events into
`TOOL_LOG_CONTRACT.md`.

## Local Wrappers Present On This Machine

These wrappers are available under `adapters/` and target CLIs detected locally:

| runner | command shape | notes |
|---|---|---|
| `codex_cli_runner.py` | `codex exec --sandbox read-only --ask-for-approval never` | Non-interactive Codex run. |
| `claude_code_runner.py` | `claude --print --output-format text` | Non-interactive Claude Code run with read/search tools only. |
| `opencode_runner.py` | `opencode run --format json --dir <sandbox>` | Non-interactive opencode run. |

Example with Codex:

```powershell
$runner = (Resolve-Path .\adapters\codex_cli_runner.py).Path
python .\adapters\generic_cli_agent_adapter.py --scenarios .\reports\real_agent_run\scenarios.json --out .\reports\codex_agent\model_runs.json --trace-dir .\reports\codex_agent\raw_traces --adapter-id codex_cli:run_001 --trace-source codex_cli_wrapper -- python $runner
```

Example with Claude Code:

```powershell
$runner = (Resolve-Path .\adapters\claude_code_runner.py).Path
python .\adapters\generic_cli_agent_adapter.py --scenarios .\reports\real_agent_run\scenarios.json --out .\reports\claude_agent\model_runs.json --trace-dir .\reports\claude_agent\raw_traces --adapter-id claude_code:run_001 --trace-source claude_code_wrapper -- python $runner
```

Example with opencode:

```powershell
$runner = (Resolve-Path .\adapters\opencode_runner.py).Path
python .\adapters\generic_cli_agent_adapter.py --scenarios .\reports\real_agent_run\scenarios.json --out .\reports\opencode_agent\model_runs.json --trace-dir .\reports\opencode_agent\raw_traces --adapter-id opencode:run_001 --trace-source opencode_wrapper -- python $runner
```

These wrappers prove launchability and final-answer capture. Readiness still
requires scenario-specific required evidence. If a CLI does not expose internal
tool calls in machine-readable form, add a framework-specific event exporter
before using the run for comparison.

## Profile 2: Python Runner

Use this for a Python agent framework, local model harness, or API-backed agent
that you control.

```powershell
$runner = (Resolve-Path .\my_python_agent_runner.py).Path
python .\agent_safety_eval_harness.py generate --clean --out-dir .\reports\python_agent
python .\adapters\generic_cli_agent_adapter.py --scenarios .\reports\python_agent\scenarios.json --out .\reports\python_agent\model_runs.json --trace-dir .\reports\python_agent\raw_traces --adapter-id python_agent:run_001 --trace-source python_agent_jsonl -- python $runner
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\python_agent\model_runs.json --out-dir .\reports\python_agent_eval
python .\scan_artifacts.py .\reports\python_agent .\reports\python_agent_eval --out-dir .\reports\python_agent_secret_scan
python .\build_real_agent_readiness.py --eval-dir .\reports\python_agent_eval --secret-scan-dir .\reports\python_agent_secret_scan --out-dir .\reports\python_agent_readiness
```

Start from `adapters/example_cli_agent_runner.py` and replace
`run_agent_placeholder` with the actual agent call.

## Profile 3: Existing Transcript Export

Use this when the agent already writes a combined tool log and final-answer
file. This avoids re-running the agent.

```powershell
python .\agent_safety_eval_harness.py generate --clean --out-dir .\reports\transcript_agent
python .\adapters\transcript_replay_adapter.py --scenarios .\reports\transcript_agent\scenarios.json --tool-log .\path\to\tool_calls.jsonl --answers .\path\to\answers.json --out .\reports\transcript_agent\model_runs.json --adapter-id transcript_agent:run_001 --trace-source exported_tool_log
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\transcript_agent\model_runs.json --out-dir .\reports\transcript_agent_eval
python .\scan_artifacts.py .\reports\transcript_agent .\reports\transcript_agent_eval --out-dir .\reports\transcript_agent_secret_scan
python .\build_real_agent_readiness.py --eval-dir .\reports\transcript_agent_eval --secret-scan-dir .\reports\transcript_agent_secret_scan --out-dir .\reports\transcript_agent_readiness
```

Combined logs must include `scenario_id` on each event.

## Comparison Rule

Only compare adapters when readiness says `ready_for_comparison = true`. If a
run is `not_interpretable` or `trace_incomplete`, fix evidence capture before
using behavior failures as model-quality evidence.
