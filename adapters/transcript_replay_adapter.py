from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_safety_eval_harness import SCENARIOS, AgentRun, ToolCall, serialize_run


ADAPTER_ID = "transcript_replay_adapter:real_agent"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def load_answers(path: Path) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    answers: dict[str, dict[str, str]] = {}
    if isinstance(payload, dict) and "runs" in payload:
        payload = payload["runs"]
    if isinstance(payload, dict):
        for scenario_id, answer in payload.items():
            if isinstance(answer, str):
                answers[str(scenario_id)] = {"final_answer": answer, "status": "completed"}
            elif isinstance(answer, dict):
                final_answer = answer.get("final_answer")
                status = answer.get("status", "completed")
                if not isinstance(final_answer, str) or status not in {"completed", "refused", "error"}:
                    raise ValueError(f"answer for {scenario_id} must include string final_answer and valid status")
                answers[str(scenario_id)] = {"final_answer": final_answer, "status": str(status)}
            else:
                raise ValueError(f"answer for {scenario_id} must be a string or object")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                raise ValueError(f"answers[{index}] must be an object")
            scenario_id = item.get("scenario_id")
            final_answer = item.get("final_answer")
            status = item.get("status", "completed")
            if not isinstance(scenario_id, str) or not isinstance(final_answer, str):
                raise ValueError(f"answers[{index}] must include scenario_id and final_answer strings")
            if status not in {"completed", "refused", "error"}:
                raise ValueError(f"answers[{index}].status must be completed, refused, or error")
            answers[scenario_id] = {"final_answer": final_answer, "status": str(status)}
    else:
        raise ValueError("answers payload must be an object, list, or object with runs")
    return answers


def event_scenario_id(event: dict[str, Any]) -> str:
    scenario_id = event.get("scenario_id") or event.get("scenario")
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ValueError("tool-log event is missing scenario_id")
    return scenario_id


def event_tool_name(event: dict[str, Any]) -> str:
    tool = event.get("tool") or event.get("name") or event.get("tool_name")
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError(f"tool-log event for {event_scenario_id(event)} is missing tool/name")
    return tool


def event_args(event: dict[str, Any]) -> dict[str, Any]:
    args = event.get("args", event.get("arguments", {}))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError as exc:
            raise ValueError(f"tool-log event arguments are not valid JSON: {exc}") from exc
    if not isinstance(args, dict):
        raise ValueError(f"tool-log event for {event_scenario_id(event)} has non-object args")
    return args


def event_allowed(event: dict[str, Any]) -> bool:
    if "allowed" in event:
        allowed = event["allowed"]
    elif isinstance(event.get("result"), dict) and "allowed" in event["result"]:
        allowed = event["result"]["allowed"]
    else:
        allowed = True
    if not isinstance(allowed, bool):
        raise ValueError(f"tool-log event for {event_scenario_id(event)} has non-boolean allowed")
    return allowed


def event_note(event: dict[str, Any]) -> str:
    note = event.get("note") or event.get("reason") or event.get("summary") or "raw tool log event"
    if not isinstance(note, str):
        raise ValueError(f"tool-log event for {event_scenario_id(event)} has non-string note")
    return note


def build_tool_calls(events: list[dict[str, Any]]) -> dict[str, list[ToolCall]]:
    calls_by_scenario: dict[str, list[ToolCall]] = {}
    for event in events:
        scenario_id = event_scenario_id(event)
        calls_by_scenario.setdefault(scenario_id, []).append(
            ToolCall(
                scenario_id=scenario_id,
                tool=event_tool_name(event),
                args=event_args(event),
                allowed=event_allowed(event),
                note=event_note(event),
            )
        )
    return calls_by_scenario


def build_runs(
    scenarios_path: Path,
    tool_log_path: Path,
    answers_path: Path,
    adapter_id: str,
    trace_source: str,
) -> list[AgentRun]:
    scenario_ids = [item["scenario_id"] for item in json.loads(scenarios_path.read_text(encoding="utf-8"))]
    known_ids = {scenario.scenario_id for scenario in SCENARIOS}
    unknown_ids = sorted(set(scenario_ids) - known_ids)
    if unknown_ids:
        raise ValueError(f"scenario manifest contains unknown scenario(s): {', '.join(unknown_ids)}")

    answers = load_answers(answers_path)
    missing_answers = sorted(set(scenario_ids) - set(answers))
    if missing_answers:
        raise ValueError(f"answers file is missing scenario(s): {', '.join(missing_answers)}")

    calls_by_scenario = build_tool_calls(read_jsonl(tool_log_path))
    unknown_log_ids = sorted(set(calls_by_scenario) - set(scenario_ids))
    if unknown_log_ids:
        raise ValueError(f"tool log contains unknown scenario(s): {', '.join(unknown_log_ids)}")

    runs: list[AgentRun] = []
    for scenario_id in scenario_ids:
        answer = answers[scenario_id]
        runs.append(
            AgentRun(
                scenario_id=scenario_id,
                adapter=adapter_id,
                status=answer["status"],
                final_answer=answer["final_answer"],
                tool_calls=calls_by_scenario.get(scenario_id, []),
                evidence_source={
                    "type": "transcript_backed",
                    "trace_source": trace_source,
                    "raw_tool_log_path": str(tool_log_path),
                },
            )
        )
    return runs


def write_runs(path: Path, runs: list[AgentRun]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([serialize_run(run) for run in runs], indent=2, sort_keys=True), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay raw agent tool transcripts into model_runs.json.")
    parser.add_argument("--scenarios", required=True, help="Path to scenarios.json generated by the harness.")
    parser.add_argument("--tool-log", required=True, help="Raw JSONL tool-call log captured from the agent runner.")
    parser.add_argument("--answers", required=True, help="JSON file with final answers keyed by scenario_id.")
    parser.add_argument("--out", required=True, help="Where to write model_runs.json.")
    parser.add_argument("--adapter-id", default=ADAPTER_ID, help="Adapter ID to write into every run.")
    parser.add_argument("--trace-source", default="raw_jsonl_tool_log", help="Human-readable trace source label.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        runs = build_runs(
            scenarios_path=Path(args.scenarios),
            tool_log_path=Path(args.tool_log),
            answers_path=Path(args.answers),
            adapter_id=args.adapter_id,
            trace_source=args.trace_source,
        )
        write_runs(Path(args.out), runs)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
