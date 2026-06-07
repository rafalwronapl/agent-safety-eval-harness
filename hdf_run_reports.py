from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hdf_contracts import AgentRun
from hdf_io import write_text


def write_tool_calls(path: Path, runs: list[AgentRun]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for run in runs:
            for call in run.tool_calls:
                handle.write(json.dumps(asdict(call), sort_keys=True) + "\n")


def write_scores_csv(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["scenario_id", "category", "adapter", "passed", "failure_classes", "failed_checks"],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "scenario_id": result["scenario_id"],
                    "category": result["category"],
                    "adapter": result["adapter"],
                    "passed": result["passed"],
                    "failure_classes": ";".join(result["failure_classes"]),
                    "failed_checks": ";".join(result["failed_checks"]),
                }
            )


def write_report(path: Path, verdict: dict[str, Any]) -> None:
    lines = [
        "# Agent Safety Eval Harness Report",
        "",
        verdict["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Scenarios: {verdict['summary']['total']}",
        f"- Passed: {verdict['summary']['passed']}",
        f"- Failed: {verdict['summary']['failed']}",
        "",
        "## Verdicts",
        "",
    ]
    for result in verdict["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        classes = ", ".join(result["failure_classes"]) or "none"
        failed = ", ".join(result["failed_checks"]) or "none"
        lines.extend(
            [
                f"### {result['scenario_id']} - {status}",
                "",
                f"- Category: {result['category']}",
                f"- Adapter: {result['adapter']}",
                f"- Classes: {classes}",
                f"- Failed checks: {failed}",
                "",
            ]
        )
    write_text(path, "\n".join(lines))
