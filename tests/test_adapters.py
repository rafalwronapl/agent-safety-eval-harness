from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent_safety_eval_harness as harness
import build_demo_report
from adapters import generic_cli_agent_adapter
from adapters import sandbox_reader_adapter
from adapters import template_adapter
from adapters import transcript_replay_adapter

def test_template_adapter_generates_contract_valid_runs(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    runs = template_adapter.build_runs(tmp_path / "scenarios.json")

    assert len(runs) == len(harness.SCENARIOS)
    assert {run.adapter for run in runs} == {template_adapter.ADAPTER_ID}
    assert all(run.status == "completed" for run in runs)

    out_path = tmp_path / "model_runs.json"
    template_adapter.write_runs(out_path, runs)
    validation = harness.validate_model_runs_file(out_path)
    assert validation.valid


def test_template_adapter_cli_writes_valid_model_runs(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    out_path = tmp_path / "model_runs.json"

    exit_code = template_adapter.main(["--scenarios", str(tmp_path / "scenarios.json"), "--out", str(out_path)])

    assert exit_code == 0
    validation = harness.validate_model_runs_file(out_path)
    assert validation.valid


def test_template_adapter_end_to_end_verify_passes(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    out_path = tmp_path / "model_runs.json"
    template_adapter.main(["--scenarios", str(tmp_path / "scenarios.json"), "--out", str(out_path)])

    verdict = harness.verify_runs(tmp_path / "verified", harness.load_runs(out_path))

    assert verdict["summary"] == {"total": len(harness.SCENARIOS), "passed": len(harness.SCENARIOS), "failed": 0}


def test_template_adapter_resolves_relative_sandbox_paths_from_manifest_location(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    manifest = json.loads((tmp_path / "scenarios.json").read_text(encoding="utf-8"))
    for item in manifest:
        item["sandbox_path"] = str(Path(item["sandbox_path"]).relative_to(tmp_path))
    relative_manifest = tmp_path / "relative_scenarios.json"
    relative_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    runs = template_adapter.build_runs(relative_manifest)

    assert len(runs) == len(harness.SCENARIOS)
    assert all(run.adapter == template_adapter.ADAPTER_ID for run in runs)


def test_sandbox_reader_adapter_evaluate_runs_passes(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    out_path = tmp_path / "model_runs.json"

    exit_code = sandbox_reader_adapter.main(["--scenarios", str(tmp_path / "scenarios.json"), "--out", str(out_path)])

    assert exit_code == 0
    validation = harness.validate_model_runs_file(out_path)
    assert validation.valid
    benchmark = harness.evaluate_runs_file(tmp_path / "evaluated", out_path)
    summary = benchmark["maintainer_summary"]["adapters"][0]
    assert summary["adapter"] == sandbox_reader_adapter.ADAPTER_ID
    assert summary["verdict"] == "interpretable_pass"
    assert summary["evidence_coverage_rate"] == 1
    assert summary["passed"] == len(harness.SCENARIOS)


def test_transcript_replay_adapter_builds_transcript_backed_runs(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    source_runs = sandbox_reader_adapter.build_runs(tmp_path / "scenarios.json")
    answers_path = tmp_path / "answers.json"
    tool_log_path = tmp_path / "tool_calls.jsonl"
    out_path = tmp_path / "transcript_model_runs.json"
    answers_path.write_text(
        json.dumps(
            {
                run.scenario_id: {"status": run.status, "final_answer": run.final_answer}
                for run in source_runs
            }
        ),
        encoding="utf-8",
    )
    tool_log_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "scenario_id": call.scenario_id,
                    "tool": call.tool,
                    "args": call.args,
                    "allowed": call.allowed,
                    "note": call.note,
                }
            )
            for run in source_runs
            for call in run.tool_calls
        ),
        encoding="utf-8",
    )

    exit_code = transcript_replay_adapter.main(
        [
            "--scenarios",
            str(tmp_path / "scenarios.json"),
            "--tool-log",
            str(tool_log_path),
            "--answers",
            str(answers_path),
            "--out",
            str(out_path),
            "--adapter-id",
            "real_agent:test",
            "--trace-source",
            "test_jsonl_logger",
        ]
    )

    assert exit_code == 0
    validation = harness.validate_model_runs_file(out_path)
    assert validation.valid
    benchmark = harness.evaluate_runs_file(tmp_path / "transcript_eval", out_path)
    summary = benchmark["maintainer_summary"]["adapters"][0]
    normalized = json.loads((tmp_path / "transcript_eval" / "model_runs.normalized.json").read_text(encoding="utf-8"))
    assert summary["adapter"] == "real_agent:test"
    assert summary["verdict"] == "interpretable_pass"
    assert summary["evidence_trust_level"] == "transcript_backed"
    assert summary["transcript_backed_rate"] == 1
    assert summary["required_evidence_transcript_backed_rate"] == 1
    assert summary["evidence_source_type_counts"] == {"transcript_backed": len(harness.SCENARIOS)}
    assert normalized[0]["evidence_source"] == {
        "type": "transcript_backed",
        "trace_source": "test_jsonl_logger",
        "raw_tool_log_path": str(tool_log_path),
    }


def test_generic_cli_agent_adapter_runs_command_and_captures_transcript(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    source_runs = sandbox_reader_adapter.build_runs(tmp_path / "scenarios.json")
    fixture_path = tmp_path / "fixture_model_runs.json"
    runner_path = tmp_path / "fixture_agent.py"
    out_path = tmp_path / "generic_cli_model_runs.json"
    trace_dir = tmp_path / "raw_traces"
    fixture_path.write_text(
        json.dumps([harness.serialize_run(run) for run in source_runs]),
        encoding="utf-8",
    )
    runner_path.write_text(
        "\n".join(
            [
                "import json",
                "import os",
                "from pathlib import Path",
                "scenario_id = os.environ['HDF_SCENARIO_ID']",
                "runs = json.loads(Path(os.environ['HDF_FIXTURE_RUNS']).read_text(encoding='utf-8'))",
                "run = next(item for item in runs if item['scenario_id'] == scenario_id)",
                "tool_log_path = Path(os.environ['HDF_TOOL_LOG_PATH'])",
                "with tool_log_path.open('w', encoding='utf-8') as handle:",
                "    for call in run['tool_calls']:",
                "        handle.write(json.dumps(call) + '\\n')",
                "print(run['final_answer'])",
            ]
        ),
        encoding="utf-8",
    )
    old_fixture = os.environ.get("HDF_FIXTURE_RUNS")
    os.environ["HDF_FIXTURE_RUNS"] = str(fixture_path)
    try:
        exit_code = generic_cli_agent_adapter.main(
            [
                "--scenarios",
                str(tmp_path / "scenarios.json"),
                "--out",
                str(out_path),
                "--trace-dir",
                str(trace_dir),
                "--adapter-id",
                "generic_cli:test_agent",
                "--trace-source",
                "pytest_fixture_cli",
                "--timeout-seconds",
                "30",
                "--",
                sys.executable,
                str(runner_path),
            ]
        )
    finally:
        if old_fixture is None:
            os.environ.pop("HDF_FIXTURE_RUNS", None)
        else:
            os.environ["HDF_FIXTURE_RUNS"] = old_fixture

    assert exit_code == 0
    validation = harness.validate_model_runs_file(out_path)
    assert validation.valid
    benchmark = harness.evaluate_runs_file(tmp_path / "generic_cli_eval", out_path)
    summary = benchmark["maintainer_summary"]["adapters"][0]
    normalized = json.loads((tmp_path / "generic_cli_eval" / "model_runs.normalized.json").read_text(encoding="utf-8"))
    assert summary["adapter"] == "generic_cli:test_agent"
    assert summary["verdict"] == "interpretable_pass"
    assert summary["evidence_trust_level"] == "transcript_backed"
    assert summary["transcript_backed_rate"] == 1
    assert summary["required_evidence_transcript_backed_rate"] == 1
    assert normalized[0]["evidence_source"]["trace_source"] == "pytest_fixture_cli"
    assert normalized[0]["evidence_source"]["notes"].startswith("raw_tool_log_event_count=")
    assert Path(normalized[0]["evidence_source"]["raw_tool_log_path"]).exists()


def test_generic_cli_agent_adapter_records_timeout_as_run_error(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    manifest = json.loads((tmp_path / "scenarios.json").read_text(encoding="utf-8"))
    one_scenario_path = tmp_path / "one_scenario.json"
    one_scenario_path.write_text(json.dumps([manifest[0]]), encoding="utf-8")
    runner_path = tmp_path / "slow_agent.py"
    out_path = tmp_path / "timeout_model_runs.json"
    trace_dir = tmp_path / "raw_traces_timeout"
    runner_path.write_text(
        "\n".join(
            [
                "import time",
                "time.sleep(3)",
                "print('late answer')",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = generic_cli_agent_adapter.main(
        [
            "--scenarios",
            str(one_scenario_path),
            "--out",
            str(out_path),
            "--trace-dir",
            str(trace_dir),
            "--timeout-seconds",
            "1",
            "--",
            sys.executable,
            str(runner_path),
        ]
    )

    assert exit_code == 0
    runs = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(runs) == 1
    assert runs[0]["status"] == "error"
    assert "timed out after 1 seconds" in runs[0]["final_answer"]
    assert runs[0]["tool_calls"] == []
    assert runs[0]["evidence_source"]["notes"] == "raw_tool_log_event_count=0"


def test_generic_cli_agent_adapter_rejects_malformed_tool_log(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    manifest = json.loads((tmp_path / "scenarios.json").read_text(encoding="utf-8"))
    one_scenario_path = tmp_path / "one_scenario.json"
    one_scenario_path.write_text(json.dumps([manifest[0]]), encoding="utf-8")
    runner_path = tmp_path / "bad_logger_agent.py"
    out_path = tmp_path / "bad_logger_model_runs.json"
    trace_dir = tmp_path / "bad_logger_traces"
    runner_path.write_text(
        "\n".join(
            [
                "import os",
                "from pathlib import Path",
                "Path(os.environ['HDF_TOOL_LOG_PATH']).write_text('{not valid json}\\n', encoding='utf-8')",
                "print('answer with malformed trace')",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = generic_cli_agent_adapter.main(
        [
            "--scenarios",
            str(one_scenario_path),
            "--out",
            str(out_path),
            "--trace-dir",
            str(trace_dir),
            "--timeout-seconds",
            "30",
            "--",
            sys.executable,
            str(runner_path),
        ]
    )

    assert exit_code == 1
    assert not out_path.exists()


def test_generic_cli_agent_adapter_resolves_relative_sandbox_paths_from_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    harness.generate_scenarios(tmp_path / "manifest_root", clean=True)
    manifest_path = tmp_path / "manifest_root" / "scenarios.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first = manifest[0]
    sandbox_path = Path(first["sandbox_path"])
    first["sandbox_path"] = str(sandbox_path.relative_to(manifest_path.parent))
    one_scenario_path = tmp_path / "manifest_root" / "one_scenario_relative.json"
    one_scenario_path.write_text(json.dumps([first]), encoding="utf-8")

    wrong_cwd = tmp_path / "wrong_cwd"
    wrong_cwd.mkdir()
    (wrong_cwd / Path(first["sandbox_path"])).mkdir(parents=True)
    monkeypatch.chdir(wrong_cwd)

    runs = generic_cli_agent_adapter.build_runs(
        scenarios_path=one_scenario_path,
        trace_dir=tmp_path / "relative_trace",
        command=[sys.executable, str(ROOT / "adapters" / "example_cli_agent_runner.py")],
        adapter_id="generic_cli:relative_path_test",
        trace_source="pytest_relative_path",
        timeout_seconds=30,
    )

    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].tool_calls[0].args == {"path": "safe_task.md"}


def test_sandbox_reader_leaky_variant_is_interpretable_failure(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    out_path = tmp_path / "model_runs.json"

    exit_code = sandbox_reader_adapter.main(
        [
            "--scenarios",
            str(tmp_path / "scenarios.json"),
            "--out",
            str(out_path),
            "--variant",
            "leaky_analysis",
        ]
    )

    assert exit_code == 0
    benchmark = harness.evaluate_runs_file(tmp_path / "evaluated", out_path)
    scorecard = benchmark["scorecard"][0]
    summary = benchmark["maintainer_summary"]["adapters"][0]
    assert summary["adapter"] == "sandbox_reader_adapter:leaky_analysis"
    assert summary["verdict"] == "interpretable_with_failures"
    assert summary["evidence_coverage_rate"] == 1
    assert summary["safety_failures"] == 23
    assert scorecard["data_minimization"] == 22
    assert scorecard["unverifiable_claim"] == 1


def test_sandbox_reader_regression_compare_same_adapter_id(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    base_runs = tmp_path / "base_model_runs.json"
    candidate_runs = tmp_path / "candidate_model_runs.json"
    adapter_id = "sandbox_reader_adapter:regression_subject"
    sandbox_reader_adapter.main(
        [
            "--scenarios",
            str(tmp_path / "scenarios.json"),
            "--out",
            str(base_runs),
            "--adapter-id",
            adapter_id,
        ]
    )
    sandbox_reader_adapter.main(
        [
            "--scenarios",
            str(tmp_path / "scenarios.json"),
            "--out",
            str(candidate_runs),
            "--variant",
            "leaky_analysis",
            "--adapter-id",
            adapter_id,
        ]
    )
    harness.evaluate_runs_file(tmp_path / "base_eval", base_runs)
    harness.evaluate_runs_file(tmp_path / "candidate_eval", candidate_runs)

    comparison = harness.compare_benchmarks(tmp_path / "base_eval", tmp_path / "candidate_eval", tmp_path / "comparison")

    assert comparison["status_counts"] == {"verdict_changed": 1}
    row = comparison["adapters"][0]
    assert row["adapter"] == adapter_id
    assert row["passed_delta"] == -23
    assert row["behavior_failures_delta"] == 23
    assert row["evidence_coverage_delta"] == 0


def test_build_demo_report_from_regression_artifacts(tmp_path: Path) -> None:
    harness.generate_scenarios(tmp_path, clean=True)
    base_runs = tmp_path / "base_model_runs.json"
    candidate_runs = tmp_path / "candidate_model_runs.json"
    adapter_id = "sandbox_reader_adapter:regression_subject"
    sandbox_reader_adapter.main(["--scenarios", str(tmp_path / "scenarios.json"), "--out", str(base_runs), "--adapter-id", adapter_id])
    sandbox_reader_adapter.main(
        [
            "--scenarios",
            str(tmp_path / "scenarios.json"),
            "--out",
            str(candidate_runs),
            "--variant",
            "leaky_analysis",
            "--adapter-id",
            adapter_id,
        ]
    )
    harness.evaluate_runs_file(tmp_path / "base_eval", base_runs)
    harness.evaluate_runs_file(tmp_path / "candidate_eval", candidate_runs)
    harness.compare_benchmarks(tmp_path / "base_eval", tmp_path / "candidate_eval", tmp_path / "comparison")

    out_path = tmp_path / "DEMO_REPORT.md"
    exit_code = build_demo_report.main(
        [
            "--safe-eval",
            str(tmp_path / "base_eval"),
            "--leaky-eval",
            str(tmp_path / "candidate_eval"),
            "--regression",
            str(tmp_path / "comparison"),
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    report = out_path.read_text(encoding="utf-8")
    assert "Evidence coverage delta: `0%`" in report
    assert "behavior got worse while trace quality remained sufficient" in report


