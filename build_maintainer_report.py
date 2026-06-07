from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_UNIQUENESS = Path("UNIQUENESS.md")
DEFAULT_UNIQUENESS_GATE = Path("AI_IT_UNIQUENESS_GATE.json")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_uniqueness_boundary(path: Path) -> str:
    if not path.exists():
        return "Use only the narrow synthetic offline claim boundary documented in this repository."
    text = path.read_text(encoding="utf-8")
    marker = "## Allowed Claim"
    if marker not in text:
        return "Use only the narrow synthetic offline claim boundary documented in this repository."
    return text.split(marker, 1)[1].split("##", 1)[0].strip()


def top_scorecard_rows(benchmark: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    return sorted(
        benchmark["scorecard"],
        key=lambda row: (-row["severity_total"], row["adapter"]),
    )[:limit]


def top_cluster_rows(benchmark: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    return sorted(
        benchmark.get("failure_clusters", []),
        key=lambda row: (-row["adapter_count"], row["failure_class"], row["scenario_id"]),
    )[:limit]


def cluster_delta_rows(comparison: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    priority = {
        "new_cluster": 0,
        "expanded_cluster": 1,
        "reduced_cluster": 2,
        "resolved_cluster": 3,
        "unchanged_cluster": 4,
    }
    return sorted(
        comparison.get("cluster_deltas", []),
        key=lambda row: (priority.get(row["status"], 99), row["failure_class"], row["scenario_id"]),
    )[:limit]


def load_uniqueness_gate(path: Path, project_id: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = load_json(path)
    for entry in payload.get("entries", []):
        if entry.get("id") == project_id:
            return entry
    return None


def build_maintainer_report(
    benchmark_dir: Path,
    comparison_dir: Path | None,
    uniqueness_path: Path,
    uniqueness_gate_path: Path | None = None,
    uniqueness_project_id: str = "agentic-data-analysis-safety",
) -> str:
    benchmark = load_json(benchmark_dir / "benchmark_summary.json")
    uniqueness_claim = load_uniqueness_boundary(uniqueness_path)
    uniqueness_gate = (
        load_uniqueness_gate(uniqueness_gate_path, uniqueness_project_id)
        if uniqueness_gate_path is not None
        else None
    )
    comparison = None
    if comparison_dir is not None:
        comparison_path = comparison_dir / "benchmark_comparison.json"
        if comparison_path.exists():
            comparison = load_json(comparison_path)

    lines = [
        "# Maintainer Evaluation Report",
        "",
        "## Claim Boundary",
        "",
        "This report is for synthetic offline regression triage. It is not evidence of product exploitability, real secret exposure, or broad real-world agent safety.",
        "",
        "Allowed narrow claim:",
        "",
        uniqueness_claim,
        "",
        "## Uniqueness Gate Snapshot",
        "",
    ]
    if uniqueness_gate is None:
        lines.extend(
            [
                "- No uniqueness gate snapshot was available for this report.",
                "- Re-run the HDF uniqueness gate before broadening claims.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"- Project id: `{uniqueness_gate['id']}`",
                f"- Local verdict: `{uniqueness_gate['uniqueness_verdict']}`",
                f"- Max collision risk: `{uniqueness_gate['max_collision_risk']}`",
                f"- Narrowed claim: {uniqueness_gate['narrowed_claim']}",
                "",
                "| baseline | collision risk | scope |",
                "|---|---:|---|",
            ]
        )
        for baseline in uniqueness_gate["nearest_baselines"][:4]:
            lines.append(
                "| {baseline_name} | {collision_risk} | {scope} |".format(**baseline)
            )
        lines.append("")

    lines.extend(
        [
            "## Overall Result",
            "",
            f"- Scenario count: `{benchmark['scenario_count']}`",
            f"- Adapter count: `{benchmark['adapter_count']}`",
            f"- Claim boundary from run: {benchmark['claim_boundary']}",
            "",
            "## Adapter Triage",
            "",
            "| adapter | verdict | pass rate | evidence coverage | evidence trust | transcript-backed required evidence | behavior failures | severity total | severity max | recommendation |",
            "|---|---|---:|---:|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in benchmark["maintainer_summary"]["adapters"]:
        pass_rate = row["passed"] / row["total"] if row["total"] else 0
        format_row = dict(row)
        format_row["evidence_trust_level"] = row.get("evidence_trust_level", "adapter_reported")
        format_row["required_evidence_transcript_backed_rate"] = row.get(
            "required_evidence_transcript_backed_rate", 0
        )
        lines.append(
            "| {adapter} | {verdict} | {pass_rate:.0%} | {evidence_coverage_rate:.0%} | "
            "{evidence_trust_level} | {required_evidence_transcript_backed_rate:.0%} | "
            "{behavior_failures} | {severity_total} | {severity_max} | {recommendation} |".format(
                pass_rate=pass_rate,
                **format_row,
            )
        )

    lines.extend(
        [
            "",
            "## Highest Severity Adapters",
            "",
            "| adapter | severity total | severity max | failed | secret exposure | unsafe action | data minimization | access denial | harness flaw |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in top_scorecard_rows(benchmark):
        lines.append(
            "| {adapter} | {severity_total} | {severity_max} | {failed} | {secret_exposure} | "
            "{unsafe_action} | {data_minimization} | {access_denial} | {harness_flaw} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Failure Clusters To Inspect",
            "",
        ]
    )
    clusters = top_cluster_rows(benchmark)
    if clusters:
        lines.extend(
            [
                "| failure class | scenario | category | adapters | failed checks |",
                "|---|---|---|---:|---|",
            ]
        )
        for row in clusters:
            lines.append(
                "| {failure_class} | {scenario_id} | {category} | {adapter_count} | {failed_checks} |".format(
                    failure_class=row["failure_class"],
                    scenario_id=row["scenario_id"],
                    category=row["category"],
                    adapter_count=row["adapter_count"],
                    failed_checks=", ".join(row["failed_checks"]),
                )
            )
    else:
        lines.append("- No failure clusters found.")

    if comparison is not None:
        lines.extend(
            [
                "",
                "## Regression Signal",
                "",
            ]
        )
        for status, count in comparison["status_counts"].items():
            lines.append(f"- Adapter `{status}`: `{count}`")
        for status, count in comparison.get("cluster_status_counts", {}).items():
            lines.append(f"- Cluster `{status}`: `{count}`")

        deltas = cluster_delta_rows(comparison)
        if deltas:
            lines.extend(
                [
                    "",
                    "| failure class | scenario | status | base adapters | candidate adapters | adapter delta |",
                    "|---|---|---|---:|---:|---:|",
                ]
            )
            for row in deltas:
                lines.append(
                    "| {failure_class} | {scenario_id} | {status} | {base_adapter_count} | "
                    "{candidate_adapter_count} | {adapter_count_delta} |".format(
                        failure_class=row["failure_class"],
                        scenario_id=row["scenario_id"],
                        status=row["status"],
                        base_adapter_count="" if row["base_adapter_count"] is None else row["base_adapter_count"],
                        candidate_adapter_count=""
                        if row["candidate_adapter_count"] is None
                        else row["candidate_adapter_count"],
                        adapter_count_delta="" if row["adapter_count_delta"] is None else row["adapter_count_delta"],
                    )
                )

    lines.extend(
        [
            "",
            "## Decision Rule",
            "",
            "- Treat `not_interpretable` as a trace/evidence problem before comparing model behavior.",
            "- Prioritize high severity with sufficient evidence coverage and transcript-backed required evidence over raw fail counts.",
            "- Treat new or expanded clusters under the same adapter id as regression candidates.",
            "- Do not broaden novelty claims without re-running the HDF uniqueness gate and second-agent review.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a maintainer-facing synthetic benchmark report.")
    parser.add_argument("--benchmark", type=Path, default=Path("reports/benchmark"))
    parser.add_argument("--comparison", type=Path, default=Path("reports/benchmark_comparison"))
    parser.add_argument("--uniqueness", type=Path, default=DEFAULT_UNIQUENESS)
    parser.add_argument("--uniqueness-gate", type=Path, default=DEFAULT_UNIQUENESS_GATE)
    parser.add_argument("--uniqueness-project-id", default="agentic-data-analysis-safety")
    parser.add_argument("--out", type=Path, default=Path("reports/MAINTAINER_EVALUATION_REPORT.md"))
    args = parser.parse_args(argv)

    report = build_maintainer_report(
        args.benchmark,
        args.comparison,
        args.uniqueness,
        args.uniqueness_gate,
        args.uniqueness_project_id,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
