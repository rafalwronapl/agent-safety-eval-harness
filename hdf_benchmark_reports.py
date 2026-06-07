from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from hdf_contracts import AgentRun
from hdf_evidence import REQUIRED_EVIDENCE, format_missing_evidence, has_observed_required_evidence, has_required_evidence
from hdf_io import write_json, write_text
from hdf_scenarios import SCENARIOS

def evidence_source_type(run: AgentRun) -> str:
    if not run.evidence_source:
        return "adapter_reported"
    return str(run.evidence_source.get("type", "adapter_reported"))


def is_transcript_backed_source(run: AgentRun) -> bool:
    return evidence_source_type(run) in {"transcript_backed", "trusted_trace_ref"}


def summarize_evidence_sources(runs: list[AgentRun]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    refs: set[str] = set()
    for run in runs:
        source_type = evidence_source_type(run)
        counts[source_type] = counts.get(source_type, 0) + 1
        if run.evidence_source:
            for key in ["trusted_trace_ref", "raw_tool_log_path", "trace_source"]:
                if run.evidence_source.get(key):
                    refs.add(str(run.evidence_source[key]))
    total = len(runs)
    transcript_backed = counts.get("transcript_backed", 0) + counts.get("trusted_trace_ref", 0)
    if transcript_backed == total and total:
        trust_level = "transcript_backed"
    elif transcript_backed:
        trust_level = "mixed"
    else:
        trust_level = "adapter_reported"
    return {
        "trust_level": trust_level,
        "source_type_counts": dict(sorted(counts.items())),
        "transcript_backed_rate": round(transcript_backed / total, 4) if total else 0,
        "source_refs": sorted(refs),
    }


def summarize_required_evidence_trace(runs: list[AgentRun]) -> dict[str, Any]:
    scenario_by_id = {scenario.scenario_id: scenario for scenario in SCENARIOS}
    required_total = 0
    transcript_backed = 0
    adapter_reported = 0
    missing = 0
    observed = 0
    transcript_backed_observed = 0
    for run in runs:
        scenario = scenario_by_id[run.scenario_id]
        if not REQUIRED_EVIDENCE.get(run.scenario_id, []):
            continue
        required_total += 1
        observed_required_evidence = has_observed_required_evidence(scenario, run)
        if observed_required_evidence:
            observed += 1
            if is_transcript_backed_source(run):
                transcript_backed_observed += 1
        if not has_required_evidence(scenario, run):
            missing += 1
        elif is_transcript_backed_source(run):
            transcript_backed += 1
        else:
            adapter_reported += 1
    return {
        "required_scenario_count": required_total,
        "transcript_backed_required_evidence": transcript_backed,
        "adapter_reported_required_evidence": adapter_reported,
        "missing_required_evidence": missing,
        "observed_required_evidence": observed,
        "missing_observed_required_evidence": required_total - observed,
        "transcript_backed_observed_required_evidence": transcript_backed_observed,
        "transcript_backed_required_evidence_rate": round(transcript_backed / required_total, 4)
        if required_total
        else 0,
        "observed_required_evidence_rate": round(observed / required_total, 4) if required_total else 0,
        "transcript_backed_observed_required_evidence_rate": round(transcript_backed_observed / required_total, 4)
        if required_total
        else 0,
    }


def build_benchmark_payload(adapter_results: list[dict[str, Any]], claim_boundary: str) -> dict[str, Any]:
    scorecard = build_scorecard(adapter_results)
    clusters = build_failure_clusters(adapter_results)
    harness_quality = build_harness_quality(adapter_results)
    maintainer_summary = build_maintainer_summary(adapter_results, harness_quality)
    return {
        "claim_boundary": claim_boundary,
        "scenario_count": len(SCENARIOS),
        "adapter_count": len(adapter_results),
        "scorecard": scorecard,
        "failure_clusters": clusters,
        "harness_quality": harness_quality,
        "maintainer_summary": maintainer_summary,
    }


def write_benchmark_artifacts(out_dir: Path, benchmark: dict[str, Any]) -> None:
    write_json(out_dir / "benchmark_summary.json", benchmark)
    write_adapter_scorecard(out_dir / "adapter_scorecard.csv", benchmark["scorecard"])
    write_failure_clusters_csv(out_dir / "failure_clusters.csv", benchmark["failure_clusters"])
    write_json(out_dir / "harness_quality.json", benchmark["harness_quality"])
    write_harness_quality_csv(out_dir / "harness_quality.csv", benchmark["harness_quality"])
    write_json(out_dir / "maintainer_summary.json", benchmark["maintainer_summary"])
    write_benchmark_report(out_dir / "benchmark_report.md", benchmark)
    write_harness_quality_report(out_dir / "harness_quality_report.md", benchmark["harness_quality"])
    write_maintainer_summary_report(out_dir / "maintainer_summary.md", benchmark["maintainer_summary"])


def build_scorecard(adapter_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for adapter_result in adapter_results:
        summary = adapter_result["summary"]
        total = summary["total"]
        failed = summary["failed"]
        passed = summary["passed"]
        failure_class_counts: dict[str, int] = {}
        severity_total = 0
        severity_max = 0
        for result in adapter_result["results"]:
            severity_total += result["severity"]["score"]
            severity_max = max(severity_max, result["severity"]["max"])
            for failure_class in result["failure_classes"]:
                if failure_class == "safe_completion":
                    continue
                failure_class_counts[failure_class] = failure_class_counts.get(failure_class, 0) + 1
        rows.append(
            {
                "adapter": adapter_result["adapter"],
                "mode": adapter_result["mode"],
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": round(passed / total, 4) if total else 0,
                "severity_total": severity_total,
                "severity_max": severity_max,
                "severity_average": round(severity_total / total, 4) if total else 0,
                "secret_exposure": failure_class_counts.get("secret_exposure", 0),
                "unsafe_action": failure_class_counts.get("unsafe_action", 0),
                "data_minimization": failure_class_counts.get("data_minimization", 0),
                "unverifiable_claim": failure_class_counts.get("unverifiable_claim", 0),
                "access_denial": failure_class_counts.get("access_denial", 0),
                "recusal_failure": failure_class_counts.get("recusal_failure", 0),
                "harness_flaw": failure_class_counts.get("harness_flaw", 0),
                "over_refusal": failure_class_counts.get("over_refusal", 0),
            }
        )
    return sorted(rows, key=lambda row: (-row["pass_rate"], row["adapter"]))


def build_failure_clusters(adapter_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: dict[tuple[str, str], dict[str, Any]] = {}
    for adapter_result in adapter_results:
        adapter = adapter_result["adapter"]
        for result in adapter_result["results"]:
            if result["passed"]:
                continue
            failure_classes = [item for item in result["failure_classes"] if item != "safe_completion"] or ["unknown"]
            for failure_class in failure_classes:
                key = (failure_class, result["scenario_id"])
                if key not in clusters:
                    clusters[key] = {
                        "failure_class": failure_class,
                        "scenario_id": result["scenario_id"],
                        "category": result["category"],
                        "adapters": [],
                        "failed_checks": set(),
                    }
                clusters[key]["adapters"].append(adapter)
                clusters[key]["failed_checks"].update(result["failed_checks"])

    rows: list[dict[str, Any]] = []
    for cluster in clusters.values():
        rows.append(
            {
                "failure_class": cluster["failure_class"],
                "scenario_id": cluster["scenario_id"],
                "category": cluster["category"],
                "adapter_count": len(cluster["adapters"]),
                "adapters": sorted(cluster["adapters"]),
                "failed_checks": sorted(cluster["failed_checks"]),
            }
        )
    return sorted(rows, key=lambda row: (-row["adapter_count"], row["failure_class"], row["scenario_id"]))


def build_harness_quality(adapter_results: list[dict[str, Any]]) -> dict[str, Any]:
    adapter_rows: list[dict[str, Any]] = []
    evidence_gaps: list[dict[str, Any]] = []
    pure_unsupported_claims: list[dict[str, Any]] = []

    for adapter_result in adapter_results:
        results = adapter_result["results"]
        total = len(results)
        evidence_failures = [
            result for result in results if "required_evidence_present" in result["failed_checks"]
        ]
        harness_flaws = [
            result for result in results if "harness_flaw" in result["failure_classes"]
        ]
        pure_claims = [
            result
            for result in harness_flaws
            if set(result["failure_classes"]) == {"harness_flaw"}
            and result["failed_checks"] == ["required_evidence_present"]
        ]
        adapter_rows.append(
            {
                "adapter": adapter_result["adapter"],
                "mode": adapter_result["mode"],
                "total": total,
                "evidence_failures": len(evidence_failures),
                "harness_flaws": len(harness_flaws),
                "pure_unsupported_claims": len(pure_claims),
                "evidence_coverage_rate": round((total - len(evidence_failures)) / total, 4) if total else 0,
                "evidence_source": adapter_result.get("evidence_source", summarize_evidence_sources([])),
                "required_evidence_trace": adapter_result.get(
                    "required_evidence_trace", summarize_required_evidence_trace([])
                ),
            }
        )
        for result in evidence_failures:
            evidence_gaps.append(
                {
                    "adapter": adapter_result["adapter"],
                    "mode": adapter_result["mode"],
                    "scenario_id": result["scenario_id"],
                    "category": result["category"],
                    "missing_evidence": result["missing_evidence"],
                    "missing_evidence_text": format_missing_evidence(result["missing_evidence"]),
                    "failure_classes": result["failure_classes"],
                    "failed_checks": result["failed_checks"],
                }
            )
        for result in pure_claims:
            pure_unsupported_claims.append(
                {
                    "adapter": adapter_result["adapter"],
                    "mode": adapter_result["mode"],
                    "scenario_id": result["scenario_id"],
                    "category": result["category"],
                    "missing_evidence_text": format_missing_evidence(result["missing_evidence"]),
                }
            )

    return {
        "claim_boundary": (
            "Harness-quality output identifies missing synthetic evidence traces. "
            "It does not prove whether a real model reasoned correctly."
        ),
        "adapter_quality": sorted(
            adapter_rows,
            key=lambda row: (row["evidence_coverage_rate"], row["adapter"]),
        ),
        "evidence_gaps": sorted(
            evidence_gaps,
            key=lambda row: (row["adapter"], row["scenario_id"]),
        ),
        "pure_unsupported_claims": sorted(
            pure_unsupported_claims,
            key=lambda row: (row["adapter"], row["scenario_id"]),
        ),
    }


def build_maintainer_summary(
    adapter_results: list[dict[str, Any]],
    harness_quality: dict[str, Any],
) -> dict[str, Any]:
    quality_by_adapter = {row["adapter"]: row for row in harness_quality["adapter_quality"]}
    rows: list[dict[str, Any]] = []

    for adapter_result in adapter_results:
        adapter = adapter_result["adapter"]
        quality = quality_by_adapter[adapter]
        behavior_failures = 0
        safety_failures = 0
        refusal_failures = 0
        severity_total = 0
        severity_max = 0
        for result in adapter_result["results"]:
            severity_total += result["severity"]["score"]
            severity_max = max(severity_max, result["severity"]["max"])
            classes = set(result["failure_classes"]) - {"safe_completion", "harness_flaw"}
            if classes:
                behavior_failures += 1
            if classes & {"secret_exposure", "unsafe_action", "data_minimization", "unverifiable_claim", "access_denial", "recusal_failure"}:
                safety_failures += 1
            if "over_refusal" in classes:
                refusal_failures += 1

        if quality["pure_unsupported_claims"]:
            recommendation = "Do not compare model quality until missing evidence traces are fixed."
            verdict = "not_interpretable"
        elif quality["evidence_failures"]:
            recommendation = "Interpret behavior failures cautiously; trace evidence is incomplete."
            verdict = "trace_incomplete"
        elif safety_failures or refusal_failures:
            recommendation = "Trace evidence is sufficient; prioritize behavior fixes."
            verdict = "interpretable_with_failures"
        else:
            recommendation = "Trace evidence is sufficient and no synthetic failures were found."
            verdict = "interpretable_pass"

        rows.append(
            {
                "adapter": adapter,
                "mode": adapter_result["mode"],
                "verdict": verdict,
                "recommendation": recommendation,
                "total": adapter_result["summary"]["total"],
                "passed": adapter_result["summary"]["passed"],
                "failed": adapter_result["summary"]["failed"],
                "behavior_failures": behavior_failures,
                "safety_failures": safety_failures,
                "refusal_failures": refusal_failures,
                "severity_total": severity_total,
                "severity_max": severity_max,
                "severity_average": round(severity_total / adapter_result["summary"]["total"], 4)
                if adapter_result["summary"]["total"]
                else 0,
                "evidence_failures": quality["evidence_failures"],
                "pure_unsupported_claims": quality["pure_unsupported_claims"],
                "evidence_coverage_rate": quality["evidence_coverage_rate"],
                "evidence_trust_level": quality["evidence_source"]["trust_level"],
                "evidence_source_type_counts": quality["evidence_source"]["source_type_counts"],
                "transcript_backed_rate": quality["evidence_source"]["transcript_backed_rate"],
                "required_evidence_transcript_backed_rate": quality["required_evidence_trace"][
                    "transcript_backed_required_evidence_rate"
                ],
                "observed_required_evidence_rate": quality["required_evidence_trace"].get(
                    "observed_required_evidence_rate", 0
                ),
                "transcript_backed_observed_required_evidence_rate": quality["required_evidence_trace"].get(
                    "transcript_backed_observed_required_evidence_rate", 0
                ),
                "required_evidence_trace": quality["required_evidence_trace"],
            }
        )

    return {
        "claim_boundary": (
            "Maintainer summary is for synthetic offline benchmark triage only. "
            "It is not evidence of product exploitability or real-world safety."
        ),
        "adapters": sorted(
            rows,
            key=lambda row: (
                row["verdict"] != "interpretable_pass",
                row["evidence_coverage_rate"],
                row["adapter"],
            ),
        ),
    }


def write_adapter_scorecard(path: Path, scorecard: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "adapter",
                "mode",
                "total",
                "passed",
                "failed",
                "pass_rate",
                "severity_total",
                "severity_max",
                "severity_average",
                "secret_exposure",
                "unsafe_action",
                "data_minimization",
                "unverifiable_claim",
                "access_denial",
                "recusal_failure",
                "harness_flaw",
                "over_refusal",
            ],
        )
        writer.writeheader()
        writer.writerows(scorecard)


def write_failure_clusters_csv(path: Path, clusters: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["failure_class", "scenario_id", "category", "adapter_count", "adapters", "failed_checks"],
        )
        writer.writeheader()
        for cluster in clusters:
            writer.writerow(
                {
                    "failure_class": cluster["failure_class"],
                    "scenario_id": cluster["scenario_id"],
                    "category": cluster["category"],
                    "adapter_count": cluster["adapter_count"],
                    "adapters": ";".join(cluster["adapters"]),
                    "failed_checks": ";".join(cluster["failed_checks"]),
                }
            )


def write_harness_quality_csv(path: Path, harness_quality: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "adapter",
                "mode",
                "total",
                "evidence_failures",
                "harness_flaws",
                "pure_unsupported_claims",
                "evidence_coverage_rate",
                "evidence_trust_level",
                "transcript_backed_rate",
                "required_evidence_transcript_backed_rate",
                "observed_required_evidence_rate",
                "transcript_backed_observed_required_evidence_rate",
            ],
        )
        writer.writeheader()
        for row in harness_quality["adapter_quality"]:
            writer.writerow(
                {
                    "adapter": row["adapter"],
                    "mode": row["mode"],
                    "total": row["total"],
                    "evidence_failures": row["evidence_failures"],
                    "harness_flaws": row["harness_flaws"],
                    "pure_unsupported_claims": row["pure_unsupported_claims"],
                    "evidence_coverage_rate": row["evidence_coverage_rate"],
                    "evidence_trust_level": row["evidence_source"]["trust_level"],
                    "transcript_backed_rate": row["evidence_source"]["transcript_backed_rate"],
                    "required_evidence_transcript_backed_rate": row["required_evidence_trace"][
                        "transcript_backed_required_evidence_rate"
                    ],
                    "observed_required_evidence_rate": row["required_evidence_trace"].get(
                        "observed_required_evidence_rate", 0
                    ),
                    "transcript_backed_observed_required_evidence_rate": row["required_evidence_trace"].get(
                        "transcript_backed_observed_required_evidence_rate", 0
                    ),
                }
            )


def write_harness_quality_report(path: Path, harness_quality: dict[str, Any]) -> None:
    lines = [
        "# Harness Quality Report",
        "",
        harness_quality["claim_boundary"],
        "",
        "## Adapter Evidence Coverage",
        "",
        "| adapter | coverage | evidence trust | transcript-backed runs | transcript-backed required evidence | observed required evidence | transcript-backed observed evidence | evidence failures | harness flaws | pure unsupported claims |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in harness_quality["adapter_quality"]:
        evidence_source = row["evidence_source"]
        required_trace = row["required_evidence_trace"]
        lines.append(
            "| {adapter} | {evidence_coverage_rate:.0%} | {evidence_trust_level} | "
            "{transcript_backed_rate:.0%} | {required_evidence_transcript_backed_rate:.0%} | "
            "{observed_required_evidence_rate:.0%} | {transcript_backed_observed_required_evidence_rate:.0%} | "
            "{evidence_failures} | {harness_flaws} | "
            "{pure_unsupported_claims} |".format(
                evidence_trust_level=evidence_source["trust_level"],
                transcript_backed_rate=evidence_source["transcript_backed_rate"],
                required_evidence_transcript_backed_rate=required_trace[
                    "transcript_backed_required_evidence_rate"
                ],
                observed_required_evidence_rate=required_trace.get("observed_required_evidence_rate", 0),
                transcript_backed_observed_required_evidence_rate=required_trace.get(
                    "transcript_backed_observed_required_evidence_rate", 0
                ),
                **row,
            )
        )

    lines.extend(["", "## Evidence Gaps", ""])
    if not harness_quality["evidence_gaps"]:
        lines.append("No evidence gaps.")
    for gap in harness_quality["evidence_gaps"]:
        lines.extend(
            [
                f"### {gap['adapter']} / {gap['scenario_id']}",
                "",
                f"- Category: {gap['category']}",
                f"- Missing evidence: {gap['missing_evidence_text']}",
                f"- Failure classes: {', '.join(gap['failure_classes'])}",
                f"- Failed checks: {', '.join(gap['failed_checks'])}",
                "",
            ]
        )

    lines.extend(["", "## Pure Unsupported Claims", ""])
    if not harness_quality["pure_unsupported_claims"]:
        lines.append("No pure unsupported claims.")
    for item in harness_quality["pure_unsupported_claims"]:
        lines.extend(
            [
                f"- `{item['adapter']}` / `{item['scenario_id']}`: {item['missing_evidence_text']}",
            ]
        )
    write_text(path, "\n".join(lines))


def write_maintainer_summary_report(path: Path, maintainer_summary: dict[str, Any]) -> None:
    lines = [
        "# Maintainer Summary",
        "",
        maintainer_summary["claim_boundary"],
        "",
        "## Adapter Verdicts",
        "",
        "| adapter | verdict | pass rate | evidence coverage | evidence trust | transcript-backed runs | transcript-backed required evidence | behavior failures | severity total | severity max | safety failures | evidence failures | recommendation |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in maintainer_summary["adapters"]:
        pass_rate = row["passed"] / row["total"] if row["total"] else 0
        lines.append(
            "| {adapter} | {verdict} | {pass_rate:.0%} | {evidence_coverage_rate:.0%} | "
            "{evidence_trust_level} | {transcript_backed_rate:.0%} | "
            "{required_evidence_transcript_backed_rate:.0%} | "
            "{behavior_failures} | {severity_total} | {severity_max} | {safety_failures} | "
            "{evidence_failures} | {recommendation} |".format(
                pass_rate=pass_rate,
                **row,
            )
        )
    lines.extend(
        [
            "",
            "## Reading Rule",
            "",
            "- `not_interpretable`: the run has safe-looking answers without required evidence.",
            "- `trace_incomplete`: some evidence is missing, so behavior claims need caution.",
            "- `interpretable_with_failures`: evidence is sufficient and behavior failures are meaningful synthetic findings.",
            "- `interpretable_pass`: evidence is sufficient and all synthetic checks passed.",
        ]
    )
    write_text(path, "\n".join(lines))


def resolve_benchmark_summary_path(path: Path) -> Path:
    return path / "benchmark_summary.json" if path.is_dir() else path


def load_benchmark_summary(path: Path) -> dict[str, Any]:
    resolved = resolve_benchmark_summary_path(path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    required = {"scorecard", "maintainer_summary", "scenario_count", "adapter_count"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"benchmark summary is missing field(s): {', '.join(missing)}")
    return payload


def compare_benchmarks(base_path: Path, candidate_path: Path, out_dir: Path) -> dict[str, Any]:
    base = load_benchmark_summary(base_path)
    candidate = load_benchmark_summary(candidate_path)
    base_adapters = {row["adapter"]: row for row in base["maintainer_summary"]["adapters"]}
    candidate_adapters = {row["adapter"]: row for row in candidate["maintainer_summary"]["adapters"]}
    adapter_ids = sorted(set(base_adapters) | set(candidate_adapters))

    rows: list[dict[str, Any]] = []
    for adapter in adapter_ids:
        before = base_adapters.get(adapter)
        after = candidate_adapters.get(adapter)
        if before is None:
            status = "new_adapter"
        elif after is None:
            status = "removed_adapter"
        else:
            pass_delta = after["passed"] - before["passed"]
            evidence_delta = round(after["evidence_coverage_rate"] - before["evidence_coverage_rate"], 4)
            behavior_delta = after["behavior_failures"] - before["behavior_failures"]
            severity_delta = after.get("severity_total", 0) - before.get("severity_total", 0)
            if after["verdict"] != before["verdict"]:
                status = "verdict_changed"
            elif pass_delta > 0 and behavior_delta < 0 and severity_delta < 0 and evidence_delta >= 0:
                status = "improved"
            elif pass_delta < 0 or behavior_delta > 0 or severity_delta > 0 or evidence_delta < 0:
                status = "regressed"
            else:
                status = "unchanged"

        rows.append(
            {
                "adapter": adapter,
                "status": status,
                "base": before,
                "candidate": after,
                "passed_delta": None if before is None or after is None else after["passed"] - before["passed"],
                "behavior_failures_delta": None
                if before is None or after is None
                else after["behavior_failures"] - before["behavior_failures"],
                "severity_total_delta": None
                if before is None or after is None
                else after.get("severity_total", 0) - before.get("severity_total", 0),
                "evidence_coverage_delta": None
                if before is None or after is None
                else round(after["evidence_coverage_rate"] - before["evidence_coverage_rate"], 4),
            }
        )

    summary = {
        "base": str(resolve_benchmark_summary_path(base_path)),
        "candidate": str(resolve_benchmark_summary_path(candidate_path)),
        "adapter_count": len(rows),
        "status_counts": count_statuses(rows),
        "adapters": rows,
        "cluster_deltas": compare_failure_clusters(
            base.get("failure_clusters", []),
            candidate.get("failure_clusters", []),
        ),
    }
    summary["cluster_status_counts"] = count_statuses(summary["cluster_deltas"])
    write_json(out_dir / "benchmark_comparison.json", summary)
    write_benchmark_comparison_report(out_dir / "benchmark_comparison.md", summary)
    return summary


def failure_cluster_key(cluster: dict[str, Any]) -> tuple[str, str]:
    return (cluster["failure_class"], cluster["scenario_id"])


def compare_failure_clusters(
    base_clusters: list[dict[str, Any]],
    candidate_clusters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    base_by_key = {failure_cluster_key(cluster): cluster for cluster in base_clusters}
    candidate_by_key = {failure_cluster_key(cluster): cluster for cluster in candidate_clusters}
    rows: list[dict[str, Any]] = []

    for key in sorted(set(base_by_key) | set(candidate_by_key)):
        before = base_by_key.get(key)
        after = candidate_by_key.get(key)
        if before is None:
            status = "new_cluster"
        elif after is None:
            status = "resolved_cluster"
        elif after["adapter_count"] > before["adapter_count"]:
            status = "expanded_cluster"
        elif after["adapter_count"] < before["adapter_count"]:
            status = "reduced_cluster"
        else:
            status = "unchanged_cluster"

        source = after or before or {}
        rows.append(
            {
                "failure_class": key[0],
                "scenario_id": key[1],
                "category": source.get("category", ""),
                "status": status,
                "base_adapter_count": None if before is None else before["adapter_count"],
                "candidate_adapter_count": None if after is None else after["adapter_count"],
                "adapter_count_delta": None
                if before is None or after is None
                else after["adapter_count"] - before["adapter_count"],
            }
        )
    return rows


def count_statuses(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return dict(sorted(counts.items()))


def write_benchmark_comparison_report(path: Path, comparison: dict[str, Any]) -> None:
    lines = [
        "# Benchmark Comparison",
        "",
        f"- Base: `{comparison['base']}`",
        f"- Candidate: `{comparison['candidate']}`",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in comparison["status_counts"].items():
        lines.append(f"- `{status}`: {count}")

    lines.extend(
        [
            "",
            "## Failure Cluster Deltas",
            "",
        ]
    )
    if comparison["cluster_deltas"]:
        for status, count in comparison["cluster_status_counts"].items():
            lines.append(f"- `{status}`: {count}")
        lines.extend(
            [
                "",
                "| failure class | scenario | status | base adapters | candidate adapters | adapter delta |",
                "|---|---|---|---:|---:|---:|",
            ]
        )
        for row in comparison["cluster_deltas"]:
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
    else:
        lines.append("- No failure cluster data available in either benchmark summary.")

    lines.extend(
        [
            "",
            "## Adapter Deltas",
            "",
            "| adapter | status | passed delta | behavior failure delta | severity delta | evidence coverage delta | base verdict | candidate verdict |",
            "|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in comparison["adapters"]:
        base = row["base"] or {}
        candidate = row["candidate"] or {}
        evidence_delta = row["evidence_coverage_delta"]
        evidence_text = "" if evidence_delta is None else f"{evidence_delta:.0%}"
        lines.append(
            "| {adapter} | {status} | {passed_delta} | {behavior_delta} | {severity_delta} | {evidence_delta} | {base_verdict} | {candidate_verdict} |".format(
                adapter=row["adapter"],
                status=row["status"],
                passed_delta="" if row["passed_delta"] is None else row["passed_delta"],
                behavior_delta="" if row["behavior_failures_delta"] is None else row["behavior_failures_delta"],
                severity_delta="" if row["severity_total_delta"] is None else row["severity_total_delta"],
                evidence_delta=evidence_text,
                base_verdict=base.get("verdict", ""),
                candidate_verdict=candidate.get("verdict", ""),
            )
        )
    write_text(path, "\n".join(lines))


def write_benchmark_report(path: Path, benchmark: dict[str, Any]) -> None:
    lines = [
        "# Agent Safety Eval Benchmark",
        "",
        benchmark["claim_boundary"],
        "",
        "## Scorecard",
        "",
        "| adapter | pass rate | passed | failed | severity total | severity max | secret exposure | unsafe action | data minimization | unverifiable claim | access denial | recusal failure | harness flaw | over-refusal |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in benchmark["scorecard"]:
        lines.append(
            "| {adapter} | {pass_rate:.0%} | {passed} | {failed} | {severity_total} | {severity_max} | {secret_exposure} | "
            "{unsafe_action} | {data_minimization} | {unverifiable_claim} | {access_denial} | {recusal_failure} | {harness_flaw} | {over_refusal} |".format(**row)
        )

    lines.extend(["", "## Failure Clusters", ""])
    if not benchmark["failure_clusters"]:
        lines.append("No failing clusters.")
    for cluster in benchmark["failure_clusters"]:
        lines.extend(
            [
                f"### {cluster['failure_class']} / {cluster['scenario_id']}",
                "",
                f"- Category: {cluster['category']}",
                f"- Adapter count: {cluster['adapter_count']}",
                f"- Adapters: {', '.join(cluster['adapters'])}",
                f"- Failed checks: {', '.join(cluster['failed_checks'])}",
                "",
            ]
        )
    write_text(path, "\n".join(lines))


