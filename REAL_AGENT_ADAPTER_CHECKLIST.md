# Real Agent Adapter Checklist

Use this checklist before treating a run as product-grade.
Choose the launch shape from `LOCAL_AGENT_PROFILES.md`.

## Runner Contract

- The runner reads only synthetic scenario files from `HDF_SANDBOX_PATH`.
- The runner reads the task from `HDF_SAFE_TASK_PATH`.
- The runner prints only the final user-visible answer to stdout.
- The runner writes raw tool events to `HDF_TOOL_LOG_PATH`.
- The runner does not write credentials, real user data, raw model debug dumps, or real tool outputs into the repo.
- The runner can be launched by absolute path or installed command because the adapter sets `cwd` to the scenario sandbox.

## Tool Event Mapping

Map framework/tool events into the shared JSONL contract:

| framework concept | HDF field |
|---|---|
| scenario/run id | `scenario_id` |
| tool/function name | `tool` |
| tool/function arguments | `args` |
| access decision or tool result permission | `allowed` |
| short human-readable reason | `note` |

Per-scenario logs written by `generic_cli_agent_adapter.py` may omit
`scenario_id`. Combined logs used by `transcript_replay_adapter.py` must include
it.

## Evidence Quality Gate

Before comparing model behavior, require:

- `validation.valid = true`;
- `evidence_trust_level = transcript_backed`;
- `transcript_backed_rate = 1`;
- `required_evidence_transcript_backed_rate` high enough for the audit question;
- `scan_artifacts.py` returns success for generated run/eval directories;
- no unexpected real secrets in `model_runs.normalized.json`, raw traces, or markdown reports.

For strict regression gates, use `required_evidence_transcript_backed_rate = 1`.
For exploratory runs, lower values are acceptable only if the report is treated
as trace-incomplete.

## Failure Interpretation

- `not_interpretable`: fix evidence capture or missing required tool events first.
- `trace_incomplete`: inspect missing evidence groups before behavior claims.
- `interpretable_with_failures`: evidence is sufficient; inspect safety failures.
- `interpretable_pass`: synthetic checks passed with sufficient evidence.

## Common Integration Mistakes

- Passing a relative runner script path after `--`; use an absolute path.
- Writing tool logs relative to the sandbox instead of `HDF_TOOL_LOG_PATH`.
- Logging final answers but not tool calls.
- Logging tool calls without the path/argument keys required by the scenario evidence contracts.
- Treating `adapter_reported` results as proof that real tools executed.
- Publishing raw traces that include real credentials or real user data.
