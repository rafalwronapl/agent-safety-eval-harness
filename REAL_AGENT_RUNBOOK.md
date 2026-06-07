# Real Agent Runbook

Purpose: run a real local agent against the synthetic HDF scenarios while keeping
tool evidence transcript-backed and avoiding real secrets in the harness repo.
Use `REAL_AGENT_ADAPTER_CHECKLIST.md` before treating a run as product-grade.
Use `LOCAL_AGENT_PROFILES.md` to choose between installed CLI, Python runner, or
existing transcript replay integration.

## 1. Generate Synthetic Scenarios

```powershell
python .\agent_safety_eval_harness.py generate --clean --out-dir .\reports\real_agent_run
```

This writes synthetic sandboxes and `reports\real_agent_run\scenarios.json`.

## 2. Wrap The Agent Command

The recommended integration path is `adapters/generic_cli_agent_adapter.py`.
It runs one command per scenario and sets:

- `HDF_SCENARIO_ID`
- `HDF_SANDBOX_PATH`
- `HDF_SAFE_TASK_PATH`
- `HDF_TOOL_LOG_PATH`

Your command should:

- read the task from `HDF_SAFE_TASK_PATH`;
- keep credentials in environment variables or an external secret store;
- print the final user-visible answer to stdout;
- append one JSON object per tool call to `HDF_TOOL_LOG_PATH`;
- never place real secrets in generated sandboxes, model outputs, or committed files.

The adapter runs the command with `cwd` set to the current scenario sandbox.
Use an installed executable or an absolute path to your runner script.

Minimal tool-log event:

```json
{"tool":"read_file","args":{"path":"README.md"},"allowed":true,"note":"read permitted overview"}
```

The adapter also accepts `name` or `tool_name` instead of `tool`, `arguments`
instead of `args`, and `result.allowed` instead of top-level `allowed`.
The complete shared JSONL event contract is in `TOOL_LOG_CONTRACT.md`.

## 3. Smoke Test With The Example Runner

Fast path:

```powershell
.\real_agent_smoke.ps1
```

Manual equivalent:

```powershell
$runner = (Resolve-Path .\adapters\example_cli_agent_runner.py).Path
python .\adapters\generic_cli_agent_adapter.py --scenarios .\reports\real_agent_run\scenarios.json --out .\reports\real_agent_run\model_runs.example.json --trace-dir .\reports\real_agent_run\raw_traces_example --adapter-id example_cli_agent:placeholder --trace-source example_cli_jsonl -- python $runner
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\real_agent_run\model_runs.example.json --out-dir .\reports\real_agent_eval_example
```

The example runner is intentionally simple and will not satisfy all
scenario-specific evidence contracts. Its job is to verify the launch, stdout,
environment variables, and JSONL transcript path.

The generic CLI adapter continues after per-scenario timeouts. Timed-out
scenarios are written as `status = "error"` runs, so the final report shows
which scenario failed without losing the rest of the evaluation.

## 4. Run A Real Agent

Replace the command after `--` with your runner:

```powershell
$runner = (Resolve-Path .\my_agent_runner.py).Path
python .\adapters\generic_cli_agent_adapter.py --scenarios .\reports\real_agent_run\scenarios.json --out .\reports\real_agent_run\model_runs.json --trace-dir .\reports\real_agent_run\raw_traces --adapter-id my_agent:run_001 --trace-source my_agent_tool_logger -- python $runner
python .\agent_safety_eval_harness.py evaluate-runs --runs .\reports\real_agent_run\model_runs.json --out-dir .\reports\real_agent_eval
python .\scan_artifacts.py .\reports\real_agent_run .\reports\real_agent_eval --out-dir .\reports\real_agent_secret_scan
python .\build_real_agent_readiness.py --eval-dir .\reports\real_agent_eval --secret-scan-dir .\reports\real_agent_secret_scan --out-dir .\reports\real_agent_readiness
```

If your agent framework already saves a combined tool log and answers file, use
`adapters/transcript_replay_adapter.py` instead.

## 5. Interpret The Result

Read these first:

- `reports\real_agent_eval\maintainer_summary.md`
- `reports\real_agent_eval\harness_quality_report.md`
- `reports\real_agent_eval\benchmark_summary.json`
- `reports\real_agent_secret_scan\artifact_secret_scan.md`
- `reports\real_agent_readiness\real_agent_readiness.md`

Key product metrics:

- `evidence_coverage_rate`: required synthetic evidence matched the run's tool calls.
- `evidence_trust_level`: whether the run was adapter-reported, mixed, or transcript-backed.
- `required_evidence_transcript_backed_rate`: required evidence was present and backed by raw trace-style metadata.
- `evidence_source.notes`: for the generic CLI adapter, the raw JSONL event count per scenario.

Do not treat `adapter_reported` results as independent proof that real tools
executed. For product audits, prioritize `transcript_backed` runs and preserve
the raw trace directory outside any public artifact.
