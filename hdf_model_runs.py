from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hdf_contracts import AgentRun, ToolCall, ValidationResult
from hdf_io import write_json
from hdf_scenarios import SCENARIOS


def serialize_run(run: AgentRun) -> dict[str, Any]:
    payload = asdict(run)
    payload["tool_calls"] = [asdict(call) for call in run.tool_calls]
    if payload.get("evidence_source") is None:
        payload.pop("evidence_source", None)
    return payload


def validate_evidence_source(prefix: str, value: Any) -> list[str]:
    errors: list[str] = []
    allowed_fields = {"type", "trace_source", "trusted_trace_ref", "raw_tool_log_path", "notes"}
    if not isinstance(value, dict):
        return [f"{prefix}.evidence_source must be an object"]
    extra_fields = sorted(set(value) - allowed_fields)
    if extra_fields:
        errors.append(f"{prefix}.evidence_source has unsupported field(s): {', '.join(extra_fields)}")
    source_type = value.get("type")
    if source_type not in {"adapter_reported", "transcript_backed", "trusted_trace_ref"}:
        errors.append(
            f"{prefix}.evidence_source.type must be one of adapter_reported, transcript_backed, trusted_trace_ref"
        )
    if source_type == "transcript_backed":
        raw_path = value.get("raw_tool_log_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            errors.append(f"{prefix}.evidence_source.raw_tool_log_path is required for transcript_backed")
    if source_type == "trusted_trace_ref":
        trace_ref = value.get("trusted_trace_ref")
        if not isinstance(trace_ref, str) or not trace_ref.strip():
            errors.append(f"{prefix}.evidence_source.trusted_trace_ref is required for trusted_trace_ref")
    for optional_text in ["trace_source", "trusted_trace_ref", "raw_tool_log_path", "notes"]:
        if optional_text in value and not isinstance(value[optional_text], str):
            errors.append(f"{prefix}.evidence_source.{optional_text} must be a string")
    return errors


def validate_model_runs_payload(payload: Any) -> ValidationResult:
    errors: list[str] = []
    scenario_ids = {scenario.scenario_id for scenario in SCENARIOS}
    required_run_fields = {"scenario_id", "adapter", "status", "final_answer", "tool_calls"}
    optional_run_fields = {"evidence_source"}
    run_fields = required_run_fields | optional_run_fields
    tool_call_fields = {"scenario_id", "tool", "args", "allowed", "note"}

    if not isinstance(payload, list):
        return ValidationResult(False, ["model_runs payload must be a list"])
    if not payload:
        return ValidationResult(False, ["model_runs payload must contain at least one run"])

    seen_pairs: set[tuple[str, str]] = set()
    scenarios_by_adapter: dict[str, set[str]] = {}
    for index, item in enumerate(payload):
        prefix = f"run[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue

        for field_name in sorted(required_run_fields):
            if field_name not in item:
                errors.append(f"{prefix}.{field_name} is required")
        extra_fields = sorted(set(item) - run_fields)
        if extra_fields:
            errors.append(f"{prefix} has unsupported field(s): {', '.join(extra_fields)}")

        scenario_id = item.get("scenario_id")
        adapter = item.get("adapter")
        if not isinstance(scenario_id, str):
            errors.append(f"{prefix}.scenario_id must be a string")
        elif scenario_id not in scenario_ids:
            errors.append(f"{prefix}.scenario_id is unknown: {scenario_id}")

        if not isinstance(adapter, str) or not adapter.strip():
            errors.append(f"{prefix}.adapter must be a non-empty string")
        elif adapter != adapter.strip():
            errors.append(f"{prefix}.adapter must not contain leading or trailing whitespace")

        if isinstance(scenario_id, str) and isinstance(adapter, str):
            pair = (adapter, scenario_id)
            if pair in seen_pairs:
                errors.append(f"{prefix} duplicates adapter/scenario pair: {adapter} / {scenario_id}")
            seen_pairs.add(pair)
            if adapter.strip() and scenario_id in scenario_ids:
                scenarios_by_adapter.setdefault(adapter, set()).add(scenario_id)

        if item.get("status") not in {"completed", "refused", "error"}:
            errors.append(f"{prefix}.status must be one of completed, refused, error")

        if not isinstance(item.get("final_answer"), str):
            errors.append(f"{prefix}.final_answer must be a string")

        if "evidence_source" in item:
            errors.extend(validate_evidence_source(prefix, item["evidence_source"]))

        tool_calls = item.get("tool_calls")
        if not isinstance(tool_calls, list):
            errors.append(f"{prefix}.tool_calls must be a list")
            continue

        for call_index, call in enumerate(tool_calls):
            call_prefix = f"{prefix}.tool_calls[{call_index}]"
            if not isinstance(call, dict):
                errors.append(f"{call_prefix} must be an object")
                continue
            for field_name in sorted(tool_call_fields):
                if field_name not in call:
                    errors.append(f"{call_prefix}.{field_name} is required")
            extra_call_fields = sorted(set(call) - tool_call_fields)
            if extra_call_fields:
                errors.append(f"{call_prefix} has unsupported field(s): {', '.join(extra_call_fields)}")
            if call.get("scenario_id") != scenario_id:
                errors.append(f"{call_prefix}.scenario_id must match parent scenario_id")
            if not isinstance(call.get("tool"), str) or not call.get("tool"):
                errors.append(f"{call_prefix}.tool must be a non-empty string")
            if not isinstance(call.get("args"), dict):
                errors.append(f"{call_prefix}.args must be an object")
            if not isinstance(call.get("allowed"), bool):
                errors.append(f"{call_prefix}.allowed must be a boolean")
            if not isinstance(call.get("note"), str):
                errors.append(f"{call_prefix}.note must be a string")

    for adapter, submitted_scenarios in sorted(scenarios_by_adapter.items()):
        missing = sorted(scenario_ids - submitted_scenarios)
        if missing:
            errors.append(f"adapter {adapter} is missing scenario(s): {', '.join(missing)}")

    return ValidationResult(not errors, errors)


def validate_model_runs_file(path: Path) -> ValidationResult:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ValidationResult(False, [f"file not found: {path}"])
    except json.JSONDecodeError as exc:
        return ValidationResult(False, [f"invalid JSON: {exc}"])
    except OSError as exc:
        return ValidationResult(False, [f"unable to read file: {path}: {exc}"])
    return validate_model_runs_payload(payload)


def write_validation_report(path: Path, result: ValidationResult, source: Path) -> None:
    payload = {
        "source": str(source),
        "valid": result.valid,
        "errors": result.errors,
        "error_count": len(result.errors),
    }
    write_json(path, payload)


def load_runs(path: Path) -> list[AgentRun]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validation = validate_model_runs_payload(payload)
    if not validation.valid:
        joined = "; ".join(validation.errors[:10])
        raise ValueError(f"invalid model_runs payload: {joined}")
    runs: list[AgentRun] = []
    for item in payload:
        calls = [ToolCall(**call) for call in item["tool_calls"]]
        runs.append(
            AgentRun(
                scenario_id=item["scenario_id"],
                adapter=item["adapter"],
                status=item["status"],
                final_answer=item["final_answer"],
                tool_calls=calls,
                evidence_source=item.get("evidence_source"),
            )
        )
    return runs
