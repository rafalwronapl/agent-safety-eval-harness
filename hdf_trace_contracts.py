from __future__ import annotations

from pathlib import Path
from typing import Any

from hdf_evidence import REQUIRED_EVIDENCE, evidence_contract_for_scenario, format_evidence_group
from hdf_io import write_json, write_text
from hdf_scenarios import SCENARIOS
from hdf_surfaces import SCENARIO_SURFACES, SURFACE_DIFFERENTIATORS


def build_trace_contract_matrix() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    surface_counts: dict[str, int] = {}
    differentiator_counts: dict[str, int] = {}

    for scenario in SCENARIOS:
        evidence_groups = REQUIRED_EVIDENCE.get(scenario.scenario_id, [])
        surfaces = SCENARIO_SURFACES[scenario.scenario_id]
        differentiators = sorted({SURFACE_DIFFERENTIATORS[surface] for surface in surfaces})
        category_counts[scenario.category] = category_counts.get(scenario.category, 0) + 1
        for surface in surfaces:
            surface_counts[surface] = surface_counts.get(surface, 0) + 1
        for differentiator in differentiators:
            differentiator_counts[differentiator] = differentiator_counts.get(differentiator, 0) + 1
        entries.append(
            {
                "scenario_id": scenario.scenario_id,
                "category": scenario.category,
                "title": scenario.title,
                "surfaces": surfaces,
                "differentiators": differentiators,
                "required_evidence": evidence_contract_for_scenario(scenario.scenario_id),
                "required_evidence_text": [format_evidence_group(group) for group in evidence_groups],
                "expected_checks": scenario.expected_checks,
            }
        )

    return {
        "claim_boundary": (
            "Trace-contract matrix for synthetic offline scenarios only. "
            "It documents required evidence and leakage/tool-boundary surfaces; it does not prove novelty or real-world exploitability."
        ),
        "scenario_count": len(entries),
        "category_counts": dict(sorted(category_counts.items())),
        "surface_counts": dict(sorted(surface_counts.items())),
        "differentiator_counts": dict(sorted(differentiator_counts.items())),
        "entries": entries,
    }


def write_trace_contract_matrix(out_dir: Path) -> dict[str, Any]:
    matrix = build_trace_contract_matrix()
    write_json(out_dir / "trace_contract_matrix.json", matrix)
    write_trace_contract_matrix_report(out_dir / "trace_contract_matrix.md", matrix)
    return matrix


def write_trace_contract_matrix_report(path: Path, matrix: dict[str, Any]) -> None:
    lines = [
        "# Trace Contract Matrix",
        "",
        matrix["claim_boundary"],
        "",
        f"- Scenario count: `{matrix['scenario_count']}`",
        f"- Category count: `{len(matrix['category_counts'])}`",
        f"- Surface count: `{len(matrix['surface_counts'])}`",
        f"- Differentiator count: `{len(matrix['differentiator_counts'])}`",
        "",
        "## Category Counts",
        "",
    ]
    for category, count in matrix["category_counts"].items():
        lines.append(f"- `{category}`: {count}")

    lines.extend(
        [
            "",
            "## Scenario Contracts",
            "",
            "| scenario | category | surfaces | required evidence | differentiators |",
            "|---|---|---|---|---|",
        ]
    )
    for entry in matrix["entries"]:
        lines.append(
            "| {scenario_id} | {category} | {surfaces} | {required_evidence} | {differentiators} |".format(
                scenario_id=entry["scenario_id"],
                category=entry["category"],
                surfaces=", ".join(entry["surfaces"]),
                required_evidence="; ".join(entry["required_evidence_text"]),
                differentiators=", ".join(entry["differentiators"]),
            )
        )

    lines.extend(
        [
            "",
            "## Decision Rule",
            "",
            "- Add new scenarios only when they introduce a new surface, a new evidence contract, or a sharper differentiator.",
            "- Avoid generic prompt-injection or secret-leakage cases unless they exercise a data-analysis or tool-boundary trace contract.",
            "- Re-run the HDF uniqueness gate before claiming novelty beyond this matrix.",
        ]
    )
    write_text(path, "\n".join(lines))
