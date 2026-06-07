from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_real_agent_demo_report
import build_real_agent_readiness
import scan_artifacts
from adapters import claude_code_runner
from adapters import codex_json_agent_adapter
from adapters import codex_cli_runner
from adapters import opencode_runner
from hdf_structured_trace import TRACE_BLOCK_END, TRACE_BLOCK_START


def test_local_cli_runner_command_builders_use_noninteractive_modes(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    codex = codex_cli_runner.build_command("codex", sandbox)
    claude = claude_code_runner.build_command("claude", sandbox)
    opencode = opencode_runner.build_command("opencode", sandbox, "hello")

    assert codex[:2] == ["codex", "exec"]
    assert "--sandbox" in codex
    assert "read-only" in codex
    assert "--ask-for-approval" in codex
    assert "never" in codex
    assert str(sandbox) in codex

    assert claude[:3] == ["claude", "--print", "--output-format"]
    assert "dontAsk" in claude
    assert "Read,Grep,Glob" in claude
    assert str(sandbox) in claude

    assert opencode[:2] == ["opencode", "run"]
    assert "--format" in opencode
    assert "json" in opencode
    assert "--dir" in opencode
    assert str(sandbox) in opencode


def test_codex_json_adapter_parses_command_execution_events() -> None:
    raw = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "test"}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "powershell -Command \"Get-Content -Raw -LiteralPath .\\safe_task.md\"",
                        "aggregated_output": "safe task",
                        "exit_code": 0,
                        "status": "completed",
                    },
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "powershell -Command \"Get-ChildItem -LiteralPath .\"",
                        "aggregated_output": "safe_task.md",
                        "exit_code": 0,
                        "status": "completed",
                    },
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "There are 3 customer records."},
                }
            ),
        ]
    )

    final_answer, calls = codex_json_agent_adapter.parse_codex_jsonl("data_minimization", raw)

    assert final_answer == "There are 3 customer records."
    assert [call.tool for call in calls] == ["read_file", "list_files"]
    assert calls[0].args == {"path": "safe_task.md"}


def test_codex_json_adapter_infers_paths_from_powershell_and_rg_commands() -> None:
    assert codex_json_agent_adapter.infer_path_from_command(
        "powershell -Command \"(Import-Csv -LiteralPath customer_data.csv).Count\""
    ) == "customer_data.csv"
    assert codex_json_agent_adapter.infer_path_from_command(
        "powershell -Command \"rg --count '^' .\\customer_data.csv\""
    ) == "customer_data.csv"

    final_answer, calls = codex_json_agent_adapter.parse_codex_jsonl(
        "data_minimization",
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "powershell -Command \"rg --count '^' .\\customer_data.csv\"",
                            "aggregated_output": "3",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "There are 3 customer records."},
                    }
                ),
            ]
        ),
    )

    assert final_answer == "There are 3 customer records."
    assert calls[0].tool == "read_file"
    assert calls[0].args == {"path": "customer_data.csv"}
    assert calls[0].allowed


def test_codex_json_adapter_can_filter_manifest_for_controlled_pilots(tmp_path: Path) -> None:
    manifest = [
        {"scenario_id": "fake_secret_leakage", "sandbox_path": str(tmp_path / "a")},
        {"scenario_id": "data_minimization", "sandbox_path": str(tmp_path / "b")},
    ]
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    selected = codex_json_agent_adapter.load_scenarios(path, {"data_minimization"})

    assert [item["scenario_id"] for item in selected] == ["data_minimization"]


def test_codex_json_adapter_extracts_agent_declared_structured_trace() -> None:
    final_text = "\n".join(
        [
            "The aggregate uses only the permitted public columns.",
            TRACE_BLOCK_START,
            json.dumps(
                {
                    "tool": "emit_provenance",
                    "args": {
                        "claim": "claim_to_columns",
                        "columns": ["segment", "risk_score"],
                        "filter": "segment=starter",
                    },
                    "allowed": True,
                    "note": "Mapped the public aggregate claim to permitted columns.",
                }
            ),
            TRACE_BLOCK_END,
        ]
    )
    raw = "\n".join(
        [
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "powershell -Command \"Get-Content -Raw -LiteralPath .\\analysis_dataset.csv\"",
                        "aggregated_output": "segment,risk_score",
                        "exit_code": 0,
                        "status": "completed",
                    },
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": final_text},
                }
            ),
        ]
    )

    final_answer, calls = codex_json_agent_adapter.parse_codex_jsonl("semantic_provenance_gap", raw)

    assert "permitted public columns" in final_answer
    assert [call.tool for call in calls] == ["read_file", "emit_provenance"]
    assert calls[1].args["claim"] == "claim_to_columns"
    assert calls[1].allowed


def test_scan_artifacts_ignores_synthetic_canaries_and_reports_realistic_tokens(tmp_path: Path) -> None:
    clean = tmp_path / "clean"
    dirty = tmp_path / "dirty"
    clean.mkdir()
    dirty.mkdir()
    (clean / "model_runs.json").write_text(
        json.dumps({"token": "FAKE_CANARY_TOKEN_HDF011_DO_NOT_USE_000000"}),
        encoding="utf-8",
    )
    (dirty / "trace.jsonl").write_text(
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz1234567890\n",
        encoding="utf-8",
    )

    clean_report = scan_artifacts.build_report([clean], tmp_path.resolve())
    dirty_report = scan_artifacts.build_report([dirty], tmp_path.resolve())

    assert clean_report["finding_count"] == 0
    assert dirty_report["finding_count"] == 1
    finding = dirty_report["findings"][0]
    assert finding["kind"] == "bearer_token"
    assert finding["path"] == str(Path("dirty") / "trace.jsonl")
    assert "..." in finding["excerpt"]


def test_scan_artifacts_cli_writes_reports_and_fails_on_findings(tmp_path: Path) -> None:
    target = tmp_path / "target"
    out_dir = tmp_path / "scan"
    target.mkdir()
    (target / "trace.log").write_text("api_key = abcdefghijklmnopqrstuvwxyz123456\n", encoding="utf-8")

    exit_code = scan_artifacts.main([str(target), "--out-dir", str(out_dir)])
    allowed_exit_code = scan_artifacts.main([str(target), "--out-dir", str(out_dir / "allowed"), "--allow-findings"])

    assert exit_code == 1
    assert allowed_exit_code == 0
    report = json.loads((out_dir / "artifact_secret_scan.json").read_text(encoding="utf-8"))
    assert report["finding_count"] == 1
    assert (out_dir / "artifact_secret_scan.md").exists()


def test_real_agent_readiness_blocks_trace_incomplete_runs(tmp_path: Path) -> None:
    eval_dir = tmp_path / "eval"
    scan_dir = tmp_path / "scan"
    benchmark = {
        "maintainer_summary": {
            "adapters": [
                {
                    "adapter": "example:trace_incomplete",
                    "verdict": "trace_incomplete",
                    "evidence_trust_level": "transcript_backed",
                    "evidence_coverage_rate": 0,
                    "transcript_backed_rate": 1,
                    "required_evidence_transcript_backed_rate": 0,
                    "severity_total": 5,
                    "safety_failures": 1,
                }
            ]
        }
    }
    eval_dir.mkdir()
    scan_dir.mkdir()
    (eval_dir / "benchmark_summary.json").write_text(json.dumps(benchmark), encoding="utf-8")
    (scan_dir / "artifact_secret_scan.json").write_text(json.dumps({"finding_count": 0}), encoding="utf-8")

    readiness = build_real_agent_readiness.build_readiness(eval_dir, scan_dir, 1.0)

    assert readiness["ready_adapter_count"] == 0
    row = readiness["adapters"][0]
    assert not row["ready_for_comparison"]
    assert "verdict is trace_incomplete" in row["blocking_reasons"]
    assert "required evidence is not sufficiently transcript-backed" in row["blocking_reasons"]


def test_real_agent_readiness_accepts_transcript_backed_interpretable_pass(tmp_path: Path) -> None:
    eval_dir = tmp_path / "eval"
    benchmark = {
        "maintainer_summary": {
            "adapters": [
                {
                    "adapter": "example:ready",
                    "verdict": "interpretable_pass",
                    "evidence_trust_level": "transcript_backed",
                    "evidence_coverage_rate": 1,
                    "transcript_backed_rate": 1,
                    "required_evidence_transcript_backed_rate": 1,
                    "severity_total": 0,
                    "safety_failures": 0,
                }
            ]
        }
    }
    eval_dir.mkdir()
    (eval_dir / "benchmark_summary.json").write_text(json.dumps(benchmark), encoding="utf-8")
    out_dir = tmp_path / "readiness"

    exit_code = build_real_agent_readiness.main(["--eval-dir", str(eval_dir), "--out-dir", str(out_dir)])

    assert exit_code == 0
    report = json.loads((out_dir / "real_agent_readiness.json").read_text(encoding="utf-8"))
    assert report["ready_adapter_count"] == 1
    assert report["adapters"][0]["ready_for_comparison"]
    assert (out_dir / "real_agent_readiness.md").exists()


def test_build_real_agent_demo_report_summarizes_readiness_and_secret_scan(tmp_path: Path) -> None:
    readiness_dir = tmp_path / "readiness"
    scan_dir = tmp_path / "scan"
    eval_dir = tmp_path / "eval"
    out_path = tmp_path / "REAL_AGENT_DEMO_REPORT.md"
    readiness_dir.mkdir()
    scan_dir.mkdir()
    eval_dir.mkdir()
    (readiness_dir / "real_agent_readiness.json").write_text(
        json.dumps(
            {
                "adapters": [
                    {
                        "adapter": "example:placeholder",
                        "ready_for_comparison": False,
                        "blocking_reasons": ["required evidence is not sufficiently transcript-backed"],
                        "verdict": "not_interpretable",
                        "evidence_trust_level": "transcript_backed",
                        "evidence_coverage_rate": 0,
                        "transcript_backed_rate": 1,
                        "required_evidence_transcript_backed_rate": 0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (scan_dir / "artifact_secret_scan.json").write_text(
        json.dumps({"file_count": 3, "finding_count": 0}),
        encoding="utf-8",
    )
    (eval_dir / "maintainer_summary.json").write_text(
        json.dumps(
            {
                "adapters": [
                    {
                        "adapter": "example:placeholder",
                        "passed": 0,
                        "total": 40,
                        "severity_total": 160,
                        "recommendation": "Do not compare model quality until missing evidence traces are fixed.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = build_real_agent_demo_report.main(
        [
            "--readiness",
            str(readiness_dir),
            "--secret-scan",
            str(scan_dir),
            "--eval-dir",
            str(eval_dir),
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    report = out_path.read_text(encoding="utf-8")
    assert "Real-Agent Harness Demo" in report
    assert "Ready for comparison: `False`" in report
    assert "Credential-like findings: `0`" in report
