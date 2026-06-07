from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_adapter(payload: dict[str, Any]) -> dict[str, Any]:
    adapters = payload["adapters"]
    if not adapters:
        raise ValueError("payload contains no adapters")
    return adapters[0]


def build_report(readiness_dir: Path, secret_scan_dir: Path, eval_dir: Path) -> str:
    readiness = load_json(readiness_dir / "real_agent_readiness.json")
    secret_scan = load_json(secret_scan_dir / "artifact_secret_scan.json")
    maintainer = load_json(eval_dir / "maintainer_summary.json")
    ready_row = first_adapter(readiness)
    maintainer_row = first_adapter(maintainer)

    lines = [
        "# Real-Agent Harness Demo",
        "",
        "## Claim Boundary",
        "",
        "This demo shows the local real-agent ingestion path on synthetic scenarios. It does not prove real-world model safety or product exploitability.",
        "",
        "## What This Demonstrates",
        "",
        "A run can be transcript-backed and still not be ready for comparison if the agent did not produce the scenario-specific required evidence.",
        "",
        "## Example Runner Result",
        "",
        f"- Adapter: `{ready_row['adapter']}`",
        f"- Ready for comparison: `{ready_row['ready_for_comparison']}`",
        f"- Verdict: `{ready_row['verdict']}`",
        f"- Evidence trust: `{ready_row['evidence_trust_level']}`",
        f"- Evidence coverage: `{ready_row['evidence_coverage_rate']:.0%}`",
        f"- Transcript-backed runs: `{ready_row['transcript_backed_rate']:.0%}`",
        f"- Transcript-backed required evidence: `{ready_row['required_evidence_transcript_backed_rate']:.0%}`",
        f"- Blocking reasons: `{', '.join(ready_row['blocking_reasons']) or 'none'}`",
        "",
        "## Artifact Hygiene",
        "",
        f"- Files scanned: `{secret_scan['file_count']}`",
        f"- Credential-like findings: `{secret_scan['finding_count']}`",
        "",
        "## Maintainer Signal",
        "",
        f"- Passed: `{maintainer_row['passed']}/{maintainer_row['total']}`",
        f"- Severity total: `{maintainer_row['severity_total']}`",
        f"- Recommendation: {maintainer_row['recommendation']}",
        "",
        "## Why This Matters",
        "",
        "The generic CLI path is working: stdout, raw JSONL traces, validation, evaluation, secret scan, and readiness summary all run end to end.",
        "",
        "The placeholder runner is intentionally not ready because it logs only a safe-task read. A real adapter must log the actual file/tool events needed by each scenario contract.",
        "",
        "## Reproduce",
        "",
        "```powershell",
        ".\\real_agent_smoke.ps1",
        "```",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a real-agent ingestion demo report.")
    parser.add_argument("--readiness", type=Path, default=Path("reports/real_agent_smoke_readiness"))
    parser.add_argument("--secret-scan", type=Path, default=Path("reports/real_agent_smoke_secret_scan"))
    parser.add_argument("--eval-dir", type=Path, default=Path("reports/real_agent_smoke_eval"))
    parser.add_argument("--out", type=Path, default=Path("reports/REAL_AGENT_DEMO_REPORT.md"))
    args = parser.parse_args(argv)

    report = build_report(args.readiness, args.secret_scan, args.eval_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
