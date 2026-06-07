from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_safety_eval_harness import SCENARIOS, AgentRun, ToolCall, serialize_run


ADAPTER_ID = "generic_cli_agent:real_agent"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSONL event: {exc}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"{path}:{line_number}: JSONL event must be an object")
        events.append(event)
    return events


def event_tool_name(event: dict[str, Any], scenario_id: str) -> str:
    tool = event.get("tool") or event.get("name") or event.get("tool_name")
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError(f"tool-log event for {scenario_id} is missing tool/name")
    return tool


def event_args(event: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    args = event.get("args", event.get("arguments", {}))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError as exc:
            raise ValueError(f"tool-log event for {scenario_id} has invalid JSON arguments: {exc}") from exc
    if not isinstance(args, dict):
        raise ValueError(f"tool-log event for {scenario_id} has non-object args")
    return args


def event_allowed(event: dict[str, Any], scenario_id: str) -> bool:
    if "allowed" in event:
        allowed = event["allowed"]
    elif isinstance(event.get("result"), dict) and "allowed" in event["result"]:
        allowed = event["result"]["allowed"]
    else:
        allowed = True
    if not isinstance(allowed, bool):
        raise ValueError(f"tool-log event for {scenario_id} has non-boolean allowed")
    return allowed


def event_note(event: dict[str, Any], scenario_id: str) -> str:
    note = event.get("note") or event.get("reason") or event.get("summary") or "raw generic CLI tool log event"
    if not isinstance(note, str):
        raise ValueError(f"tool-log event for {scenario_id} has non-string note")
    return note


def build_tool_calls(scenario_id: str, tool_log_path: Path) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for event in read_jsonl(tool_log_path):
        event_scenario = event.get("scenario_id") or event.get("scenario") or scenario_id
        if event_scenario != scenario_id:
            raise ValueError(
                f"{tool_log_path}: event scenario_id {event_scenario!r} does not match current scenario {scenario_id!r}"
            )
        calls.append(
            ToolCall(
                scenario_id=scenario_id,
                tool=event_tool_name(event, scenario_id),
                args=event_args(event, scenario_id),
                allowed=event_allowed(event, scenario_id),
                note=event_note(event, scenario_id),
            )
        )
    return calls


def load_scenarios(scenarios_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(scenarios_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("scenarios payload must be a list")
    known_ids = {scenario.scenario_id for scenario in SCENARIOS}
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"scenarios[{index}] must be an object")
        scenario_id = item.get("scenario_id")
        if not isinstance(scenario_id, str) or scenario_id not in known_ids:
            raise ValueError(f"scenarios[{index}].scenario_id is unknown")
        if not isinstance(item.get("sandbox_path"), str):
            raise ValueError(f"scenarios[{index}].sandbox_path must be a string")
    return payload


def run_agent_command(
    command: list[str],
    scenario_id: str,
    sandbox_path: Path,
    tool_log_path: Path,
    timeout_seconds: int,
) -> tuple[str, str]:
    env = os.environ.copy()
    safe_task_path = sandbox_path / "safe_task.md"
    env.update(
        {
            "HDF_SCENARIO_ID": scenario_id,
            "HDF_SANDBOX_PATH": str(sandbox_path),
            "HDF_SAFE_TASK_PATH": str(safe_task_path),
            "HDF_TOOL_LOG_PATH": str(tool_log_path),
        }
    )
    tool_log_path.parent.mkdir(parents=True, exist_ok=True)
    tool_log_path.write_text("", encoding="utf-8")
    try:
        completed = subprocess.run(
            command,
            cwd=sandbox_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "").strip() if isinstance(exc.stderr, str) else ""
        answer = stdout
        if stderr:
            answer = f"{answer}\n\nstderr:\n{stderr}".strip()
        if not answer:
            answer = f"Agent command timed out after {timeout_seconds} seconds."
        return "error", answer
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode == 0:
        return "completed", stdout
    answer = stdout
    if stderr:
        answer = f"{answer}\n\nstderr:\n{stderr}".strip()
    if not answer:
        answer = f"Agent command exited with code {completed.returncode}."
    return "error", answer


def build_runs(
    scenarios_path: Path,
    trace_dir: Path,
    command: list[str],
    adapter_id: str,
    trace_source: str,
    timeout_seconds: int,
) -> list[AgentRun]:
    manifest = load_scenarios(scenarios_path)
    manifest_base = scenarios_path.resolve().parent
    resolved_trace_dir = trace_dir.resolve()
    runs: list[AgentRun] = []
    for item in manifest:
        scenario_id = item["scenario_id"]
        sandbox_path = Path(item["sandbox_path"])
        if not sandbox_path.is_absolute():
            cwd_candidate = sandbox_path
            manifest_candidate = manifest_base / sandbox_path
            if (cwd_candidate / "safe_task.md").is_file():
                sandbox_path = cwd_candidate.resolve()
            else:
                sandbox_path = manifest_candidate.resolve()
        else:
            sandbox_path = sandbox_path.resolve()
        if not (sandbox_path / "safe_task.md").is_file():
            raise ValueError(f"{scenario_id}: sandbox_path does not contain safe_task.md: {sandbox_path}")
        tool_log_path = resolved_trace_dir / f"{scenario_id}.tool_calls.jsonl"
        status, final_answer = run_agent_command(
            command=command,
            scenario_id=scenario_id,
            sandbox_path=sandbox_path,
            tool_log_path=tool_log_path,
            timeout_seconds=timeout_seconds,
        )
        tool_calls = build_tool_calls(scenario_id, tool_log_path)
        runs.append(
            AgentRun(
                scenario_id=scenario_id,
                adapter=adapter_id,
                status=status,
                final_answer=final_answer,
                tool_calls=tool_calls,
                evidence_source={
                    "type": "transcript_backed",
                    "trace_source": trace_source,
                    "raw_tool_log_path": str(tool_log_path),
                    "notes": f"raw_tool_log_event_count={len(tool_calls)}",
                },
            )
        )
    return runs


def write_runs(path: Path, runs: list[AgentRun]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([serialize_run(run) for run in runs], indent=2, sort_keys=True), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a real CLI agent against each generated HDF scenario.")
    parser.add_argument("--scenarios", required=True, help="Path to scenarios.json generated by the harness.")
    parser.add_argument("--out", required=True, help="Where to write model_runs.json.")
    parser.add_argument("--trace-dir", required=True, help="Directory where per-scenario raw JSONL tool logs are written.")
    parser.add_argument("--adapter-id", default=ADAPTER_ID, help="Adapter ID to write into every run.")
    parser.add_argument("--trace-source", default="generic_cli_agent", help="Human-readable trace source label.")
    parser.add_argument("--timeout-seconds", type=int, default=120, help="Per-scenario command timeout.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("command is required after --")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    try:
        runs = build_runs(
            scenarios_path=Path(args.scenarios),
            trace_dir=Path(args.trace_dir),
            command=command,
            adapter_id=args.adapter_id,
            trace_source=args.trace_source,
            timeout_seconds=args.timeout_seconds,
        )
        write_runs(Path(args.out), runs)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
