from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def adapter_ready(row: dict[str, Any], min_required_trace_rate: float) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if row.get("evidence_trust_level") != "transcript_backed":
        reasons.append("evidence_trust_level is not transcript_backed")
    if row.get("transcript_backed_rate", 0) < 1:
        reasons.append("not all runs are transcript-backed")
    if row.get("required_evidence_transcript_backed_rate", 0) < min_required_trace_rate:
        reasons.append("required evidence is not sufficiently transcript-backed")
    if row.get("verdict") in {"not_interpretable", "trace_incomplete"}:
        reasons.append(f"verdict is {row.get('verdict')}")
    return not reasons, reasons


def build_readiness(
    eval_dir: Path,
    secret_scan_dir: Path | None,
    min_required_trace_rate: float,
) -> dict[str, Any]:
    benchmark = load_json(eval_dir / "benchmark_summary.json")
    secret_scan = None
    if secret_scan_dir is not None:
        scan_path = secret_scan_dir / "artifact_secret_scan.json"
        if scan_path.exists():
            secret_scan = load_json(scan_path)

    adapters: list[dict[str, Any]] = []
    for row in benchmark["maintainer_summary"]["adapters"]:
        ready, reasons = adapter_ready(row, min_required_trace_rate)
        adapters.append(
            {
                "adapter": row["adapter"],
                "ready_for_comparison": ready,
                "blocking_reasons": reasons,
                "verdict": row["verdict"],
                "evidence_trust_level": row.get("evidence_trust_level", "adapter_reported"),
                "evidence_coverage_rate": row.get("evidence_coverage_rate", 0),
                "transcript_backed_rate": row.get("transcript_backed_rate", 0),
                "required_evidence_transcript_backed_rate": row.get(
                    "required_evidence_transcript_backed_rate", 0
                ),
                "severity_total": row.get("severity_total", 0),
                "safety_failures": row.get("safety_failures", 0),
            }
        )

    secret_findings = None if secret_scan is None else secret_scan.get("finding_count", 0)
    if secret_findings:
        for row in adapters:
            row["ready_for_comparison"] = False
            row["blocking_reasons"].append("artifact secret scan has findings")

    return {
        "claim_boundary": (
            "Readiness only decides whether a synthetic real-agent run is suitable "
            "for comparison. It does not prove real-world safety."
        ),
        "eval_dir": str(eval_dir),
        "min_required_trace_rate": min_required_trace_rate,
        "secret_scan_finding_count": secret_findings,
        "ready_adapter_count": sum(1 for row in adapters if row["ready_for_comparison"]),
        "adapter_count": len(adapters),
        "adapters": adapters,
    }


def write_markdown(path: Path, readiness: dict[str, Any]) -> None:
    lines = [
        "# Real Agent Readiness",
        "",
        readiness["claim_boundary"],
        "",
        f"- Ready adapters: `{readiness['ready_adapter_count']}` / `{readiness['adapter_count']}`",
        f"- Min required evidence transcript-backed rate: `{readiness['min_required_trace_rate']:.0%}`",
        f"- Secret scan findings: `{readiness['secret_scan_finding_count']}`",
        "",
        "| adapter | ready | verdict | evidence trust | evidence coverage | transcript-backed runs | transcript-backed required evidence | blocking reasons |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in readiness["adapters"]:
        lines.append(
            "| {adapter} | {ready} | {verdict} | {evidence_trust_level} | "
            "{evidence_coverage_rate:.0%} | {transcript_backed_rate:.0%} | "
            "{required_evidence_transcript_backed_rate:.0%} | {reasons} |".format(
                adapter=row["adapter"],
                ready="yes" if row["ready_for_comparison"] else "no",
                verdict=row["verdict"],
                evidence_trust_level=row["evidence_trust_level"],
                evidence_coverage_rate=row["evidence_coverage_rate"],
                transcript_backed_rate=row["transcript_backed_rate"],
                required_evidence_transcript_backed_rate=row[
                    "required_evidence_transcript_backed_rate"
                ],
                reasons=", ".join(row["blocking_reasons"]) or "none",
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a readiness summary for real-agent eval output.")
    parser.add_argument("--eval-dir", type=Path, required=True)
    parser.add_argument("--secret-scan-dir", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("reports/real_agent_readiness"))
    parser.add_argument("--min-required-trace-rate", type=float, default=1.0)
    args = parser.parse_args(argv)
    if not 0 <= args.min_required_trace_rate <= 1:
        parser.error("--min-required-trace-rate must be between 0 and 1")

    readiness = build_readiness(args.eval_dir, args.secret_scan_dir, args.min_required_trace_rate)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "real_agent_readiness.json").write_text(
        json.dumps(readiness, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_markdown(args.out_dir / "real_agent_readiness.md", readiness)
    print(args.out_dir / "real_agent_readiness.md")
    return 0 if readiness["ready_adapter_count"] == readiness["adapter_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
