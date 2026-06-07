from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from hdf_benchmark_reports import (
    build_benchmark_payload,
    build_failure_clusters,
    build_harness_quality,
    build_maintainer_summary,
    build_scorecard,
    compare_benchmarks,
    summarize_evidence_sources,
    summarize_required_evidence_trace,
    write_adapter_scorecard,
    write_benchmark_artifacts,
    write_benchmark_comparison_report,
    write_benchmark_report,
    write_failure_clusters_csv,
    write_harness_quality_csv,
    write_harness_quality_report,
    write_maintainer_summary_report,
)
from hdf_contracts import AgentRun, Scenario, ToolCall, ValidationResult
from hdf_evidence import format_missing_evidence
from hdf_generation import generate_scenarios
from hdf_io import assert_safe_clean_target, write_json
from hdf_model_runs import (
    load_runs,
    serialize_run,
    validate_evidence_source,
    validate_model_runs_file,
    validate_model_runs_payload,
    write_validation_report,
)
from hdf_run_reports import write_report, write_scores_csv, write_tool_calls
from hdf_scenarios import SCENARIOS
from hdf_scoring import *
from hdf_scoring_metadata import SEVERITY_WEIGHTS
from hdf_stub_adapters import run_adapter_stub
from hdf_surfaces import SCENARIO_SURFACES, SURFACE_DIFFERENTIATORS
from hdf_synthetic_data import *
from hdf_trace_contracts import build_trace_contract_matrix, write_trace_contract_matrix

def run_stub_suite(out_dir: Path, mode: str = "safe") -> list[AgentRun]:
    runs = [run_adapter_stub(scenario, mode) for scenario in SCENARIOS]
    write_json(out_dir / "model_runs.json", [serialize_run(run) for run in runs])
    return runs


def verify_runs(out_dir: Path, runs: list[AgentRun]) -> dict[str, Any]:
    scenario_by_id = {scenario.scenario_id: scenario for scenario in SCENARIOS}
    results = [score_run(scenario_by_id[run.scenario_id], run) for run in runs]
    summary = {
        "total": len(results),
        "passed": sum(1 for result in results if result["passed"]),
        "failed": sum(1 for result in results if not result["passed"]),
    }
    verdict = {
        "claim_boundary": (
            "Synthetic offline harness only. Results show behavior against fake "
            "scenarios and fake secrets, not product exploitability."
        ),
        "summary": summary,
        "results": results,
    }
    write_json(out_dir / "verdict.json", verdict)
    write_report(out_dir / "report.md", verdict)
    write_tool_calls(out_dir / "tool_calls.jsonl", runs)
    write_scores_csv(out_dir / "scores.csv", results)
    return verdict


def run_all(out_dir: Path, mode: str, clean: bool = False) -> dict[str, Any]:
    generate_scenarios(out_dir, clean=clean)
    runs = run_stub_suite(out_dir, mode=mode)
    return verify_runs(out_dir, runs)


def parse_modes(raw_modes: str) -> list[str]:
    modes = [mode.strip() for mode in raw_modes.split(",") if mode.strip()]
    if not modes:
        raise ValueError("at least one benchmark mode is required")
    allowed = {"safe", "unsafe", "over_refusal", "unsupported_claim"}
    unknown = sorted(set(modes) - allowed)
    if unknown:
        raise ValueError(f"unknown benchmark mode(s): {', '.join(unknown)}")
    return modes


def run_benchmark(out_dir: Path, modes: list[str], clean: bool = False) -> dict[str, Any]:
    generate_scenarios(out_dir, clean=clean)
    adapter_results: list[dict[str, Any]] = []
    all_runs: list[AgentRun] = []

    for mode in modes:
        run_dir = out_dir / "adapter_runs" / mode
        runs = [run_adapter_stub(scenario, mode=mode) for scenario in SCENARIOS]
        write_json(run_dir / "model_runs.json", [serialize_run(run) for run in runs])
        verdict = verify_runs(run_dir, runs)
        adapter_results.append(
            {
                "mode": mode,
                "adapter": f"adapter_stub:{mode}",
                "summary": verdict["summary"],
                "results": verdict["results"],
                "evidence_source": summarize_evidence_sources(runs),
                "required_evidence_trace": summarize_required_evidence_trace(runs),
            }
        )
        all_runs.extend(runs)

    scorecard = build_scorecard(adapter_results)
    clusters = build_failure_clusters(adapter_results)
    harness_quality = build_harness_quality(adapter_results)
    maintainer_summary = build_maintainer_summary(adapter_results, harness_quality)
    benchmark = {
        "claim_boundary": (
            "Synthetic offline benchmark only. Results compare adapters against fake "
            "scenarios and fake secrets, not product exploitability."
        ),
        "scenario_count": len(SCENARIOS),
        "adapter_count": len(adapter_results),
        "scorecard": scorecard,
        "failure_clusters": clusters,
        "harness_quality": harness_quality,
        "maintainer_summary": maintainer_summary,
    }
    write_json(out_dir / "benchmark_summary.json", benchmark)
    write_json(out_dir / "all_model_runs.json", [serialize_run(run) for run in all_runs])
    write_adapter_scorecard(out_dir / "adapter_scorecard.csv", scorecard)
    write_failure_clusters_csv(out_dir / "failure_clusters.csv", clusters)
    write_json(out_dir / "harness_quality.json", harness_quality)
    write_harness_quality_csv(out_dir / "harness_quality.csv", harness_quality)
    write_json(out_dir / "maintainer_summary.json", maintainer_summary)
    write_benchmark_report(out_dir / "benchmark_report.md", benchmark)
    write_harness_quality_report(out_dir / "harness_quality_report.md", harness_quality)
    write_maintainer_summary_report(out_dir / "maintainer_summary.md", maintainer_summary)
    return benchmark


def build_adapter_results_from_runs(runs: list[AgentRun]) -> list[dict[str, Any]]:
    scenario_by_id = {scenario.scenario_id: scenario for scenario in SCENARIOS}
    runs_by_adapter: dict[str, list[AgentRun]] = {}
    for run in runs:
        runs_by_adapter.setdefault(run.adapter, []).append(run)

    adapter_results: list[dict[str, Any]] = []
    for adapter, adapter_runs in sorted(runs_by_adapter.items()):
        results = [score_run(scenario_by_id[run.scenario_id], run) for run in adapter_runs]
        summary = {
            "total": len(results),
            "passed": sum(1 for result in results if result["passed"]),
            "failed": sum(1 for result in results if not result["passed"]),
        }
        adapter_results.append(
            {
                "mode": adapter,
                "adapter": adapter,
                "summary": summary,
                "results": results,
                "evidence_source": summarize_evidence_sources(adapter_runs),
                "required_evidence_trace": summarize_required_evidence_trace(adapter_runs),
            }
        )
    return adapter_results


def evaluate_runs_file(out_dir: Path, runs_path: Path) -> dict[str, Any]:
    validation = validate_model_runs_file(runs_path)
    write_validation_report(out_dir / "validation_report.json", validation, runs_path)
    if not validation.valid:
        joined = "; ".join(validation.errors[:10])
        raise ValueError(f"invalid model_runs payload: {joined}")

    runs = load_runs(runs_path)
    write_json(out_dir / "model_runs.normalized.json", [serialize_run(run) for run in runs])
    verdict = verify_runs(out_dir, runs)
    adapter_results = build_adapter_results_from_runs(runs)
    benchmark = build_benchmark_payload(
        adapter_results,
        (
            "External adapter evaluation against synthetic offline scenarios. "
            "Results do not prove product exploitability or real-world safety."
        ),
    )
    write_benchmark_artifacts(out_dir, benchmark)
    write_json(
        out_dir / "evaluation_summary.json",
        {
            "source": str(runs_path),
            "validation": {
                "valid": validation.valid,
                "error_count": len(validation.errors),
            },
            "verdict_summary": verdict["summary"],
            "adapter_count": benchmark["adapter_count"],
            "maintainer_summary": benchmark["maintainer_summary"],
        },
    )
    return benchmark


def add_out_dir_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out-dir", default=None, help="Output directory for generated artifacts.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline synthetic agent safety eval harness.")
    parser.add_argument("--out-dir", default=None, help="Output directory for generated artifacts.")
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser("generate", help="Generate synthetic sandboxes and scenario manifest.")
    add_out_dir_arg(generate_parser)
    generate_parser.add_argument("--clean", action="store_true", help="Delete the output directory first.")

    run_parser = subparsers.add_parser("run-stub", help="Run the local adapter stub.")
    add_out_dir_arg(run_parser)
    run_parser.add_argument("--mode", choices=["safe", "unsafe", "over_refusal", "unsupported_claim"], default="safe")

    verify_parser = subparsers.add_parser("verify", help="Verify an existing model_runs.json.")
    add_out_dir_arg(verify_parser)
    verify_parser.add_argument("--runs", default="", help="Path to model_runs.json. Defaults to out-dir/model_runs.json.")

    validate_parser = subparsers.add_parser("validate-runs", help="Validate model_runs.json adapter output.")
    add_out_dir_arg(validate_parser)
    validate_parser.add_argument("--runs", default="", help="Path to model_runs.json. Defaults to out-dir/model_runs.json.")

    evaluate_parser = subparsers.add_parser("evaluate-runs", help="Validate, verify, and summarize external model_runs.json.")
    add_out_dir_arg(evaluate_parser)
    evaluate_parser.add_argument("--runs", required=True, help="Path to external model_runs.json.")

    all_parser = subparsers.add_parser("all", help="Generate, run stub, and verify.")
    add_out_dir_arg(all_parser)
    all_parser.add_argument("--mode", choices=["safe", "unsafe", "over_refusal", "unsupported_claim"], default="safe")
    all_parser.add_argument("--clean", action="store_true", help="Delete the output directory first.")

    benchmark_parser = subparsers.add_parser("benchmark", help="Run multiple stub adapters and aggregate results.")
    add_out_dir_arg(benchmark_parser)
    benchmark_parser.add_argument("--modes", default="safe,unsafe,over_refusal,unsupported_claim")
    benchmark_parser.add_argument("--clean", action="store_true", help="Delete the output directory first.")

    compare_parser = subparsers.add_parser("compare-benchmarks", help="Compare two benchmark_summary.json files or directories.")
    add_out_dir_arg(compare_parser)
    compare_parser.add_argument("--base", required=True, help="Base benchmark_summary.json or benchmark directory.")
    compare_parser.add_argument("--candidate", required=True, help="Candidate benchmark_summary.json or benchmark directory.")

    trace_parser = subparsers.add_parser("trace-contracts", help="Write the scenario trace-contract matrix.")
    add_out_dir_arg(trace_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir or "reports/eval_run")

    if args.command == "generate":
        try:
            generate_scenarios(out_dir, clean=args.clean)
        except ValueError as exc:
            print(f"error: {exc}")
            return 1
        return 0
    if args.command == "run-stub":
        run_stub_suite(out_dir, mode=args.mode)
        return 0
    if args.command == "verify":
        runs_path = Path(args.runs) if args.runs else out_dir / "model_runs.json"
        verify_runs(out_dir, load_runs(runs_path))
        return 0
    if args.command == "validate-runs":
        runs_path = Path(args.runs) if args.runs else out_dir / "model_runs.json"
        result = validate_model_runs_file(runs_path)
        write_validation_report(out_dir / "validation_report.json", result, runs_path)
        return 0 if result.valid else 1
    if args.command == "evaluate-runs":
        try:
            evaluate_runs_file(out_dir, Path(args.runs))
        except ValueError:
            return 1
        return 0
    if args.command == "all":
        try:
            run_all(out_dir, mode=args.mode, clean=args.clean)
        except ValueError as exc:
            print(f"error: {exc}")
            return 1
        return 0
    if args.command == "benchmark":
        try:
            run_benchmark(out_dir, modes=parse_modes(args.modes), clean=args.clean)
        except ValueError as exc:
            print(f"error: {exc}")
            return 1
        return 0
    if args.command == "compare-benchmarks":
        compare_benchmarks(Path(args.base), Path(args.candidate), out_dir)
        return 0
    if args.command == "trace-contracts":
        write_trace_contract_matrix(out_dir)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
