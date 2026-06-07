from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_adapter(summary: dict[str, Any]) -> dict[str, Any]:
    adapters = summary["maintainer_summary"]["adapters"]
    if not adapters:
        raise ValueError("maintainer_summary contains no adapters")
    return adapters[0]


def build_demo_report(
    safe_eval: Path,
    leaky_eval: Path,
    regression: Path,
) -> str:
    safe_summary = load_json(safe_eval / "evaluation_summary.json")
    leaky_summary = load_json(leaky_eval / "evaluation_summary.json")
    comparison = load_json(regression / "benchmark_comparison.json")
    safe = first_adapter(safe_summary)
    leaky = first_adapter(leaky_summary)
    comparison_row = comparison["adapters"][0]

    lines = [
        "# Agent Safety Eval Harness Demo",
        "",
        "## Claim Boundary",
        "",
        "This demo uses synthetic offline scenarios only. It does not prove product exploitability, real-world model safety, or real secret exposure.",
        "",
        "## What This Demonstrates",
        "",
        "The harness separates model behavior failures from trace/evidence quality failures.",
        "",
        "A normal benchmark can say whether an adapter passed. This demo also says whether the result is interpretable.",
        "",
        "## Demo Case",
        "",
        "Two runs use the same logical adapter id:",
        "",
        "- base run: safe sandbox reader",
        "- candidate run: leaky analysis variant",
        "",
        "Both runs read generated sandbox files and provide tool-call evidence. The candidate intentionally leaks synthetic analysis labels and makes one unverifiable aggregate claim.",
        "",
        "## Base Run",
        "",
        f"- Adapter: `{safe['adapter']}`",
        f"- Verdict: `{safe['verdict']}`",
        f"- Passed: `{safe['passed']}/{safe['total']}`",
        f"- Evidence coverage: `{safe['evidence_coverage_rate']:.0%}`",
        f"- Behavior failures: `{safe['behavior_failures']}`",
        "",
        "## Candidate Run",
        "",
        f"- Adapter: `{leaky['adapter']}`",
        f"- Verdict: `{leaky['verdict']}`",
        f"- Passed: `{leaky['passed']}/{leaky['total']}`",
        f"- Evidence coverage: `{leaky['evidence_coverage_rate']:.0%}`",
        f"- Behavior failures: `{leaky['behavior_failures']}`",
        f"- Safety failures: `{leaky['safety_failures']}`",
        "",
        "## Regression Result",
        "",
        f"- Status: `{comparison_row['status']}`",
        f"- Passed delta: `{comparison_row['passed_delta']}`",
        f"- Behavior failure delta: `{comparison_row['behavior_failures_delta']}`",
        f"- Evidence coverage delta: `{comparison_row['evidence_coverage_delta']:.0%}`",
        f"- Base verdict: `{comparison_row['base']['verdict']}`",
        f"- Candidate verdict: `{comparison_row['candidate']['verdict']}`",
        "",
        "## Why This Matters",
        "",
        "The candidate did not fail because evidence disappeared. Evidence coverage stayed unchanged. That makes the regression meaningful: behavior got worse while trace quality remained sufficient.",
        "",
        "The harness also has separate baselines for evidence-free safe-looking answers, which are classified as `not_interpretable` rather than as genuine safe passes.",
        "",
        "## Key Artifacts",
        "",
        f"- Safe maintainer summary: `{safe_eval / 'maintainer_summary.md'}`",
        f"- Candidate maintainer summary: `{leaky_eval / 'maintainer_summary.md'}`",
        f"- Regression comparison: `{regression / 'benchmark_comparison.md'}`",
        "",
        "## Reproduce",
        "",
        "```powershell",
        ".\\reproduce.ps1",
        "```",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a concise demo report from generated benchmark artifacts.")
    parser.add_argument("--safe-eval", type=Path, default=Path("reports/sandbox_reader_eval"))
    parser.add_argument("--leaky-eval", type=Path, default=Path("reports/sandbox_reader_leaky_eval"))
    parser.add_argument("--regression", type=Path, default=Path("reports/sandbox_reader_regression"))
    parser.add_argument("--out", type=Path, default=Path("reports/DEMO_REPORT.md"))
    args = parser.parse_args(argv)

    report = build_demo_report(args.safe_eval, args.leaky_eval, args.regression)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
