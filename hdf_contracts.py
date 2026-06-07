from __future__ import annotations

from dataclasses import dataclass
from typing import Any


EvidenceRequirement = tuple[str, str | None]
EvidenceGroup = list[EvidenceRequirement]


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    category: str
    title: str
    safe_task: str
    malicious_task: str
    expected_checks: dict[str, bool]


@dataclass
class ToolCall:
    scenario_id: str
    tool: str
    args: dict[str, Any]
    allowed: bool
    note: str


@dataclass
class AgentRun:
    scenario_id: str
    adapter: str
    status: str
    final_answer: str
    tool_calls: list[ToolCall]
    evidence_source: dict[str, Any] | None = None


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
