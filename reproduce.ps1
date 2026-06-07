$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$File,
        [string[]]$ArgsList
    )
    & $File @ArgsList
    if ($LASTEXITCODE -ne 0) {
        throw "$File failed with exit code $LASTEXITCODE"
    }
}

Invoke-Checked python @(".\agent_safety_eval_harness.py", "all", "--clean", "--mode", "safe")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "validate-runs", "--runs", ".\reports\eval_run\model_runs.json", "--out-dir", ".\reports\eval_run")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "generate", "--clean", "--out-dir", ".\reports\template_adapter_run")
Invoke-Checked python @(".\adapters\template_adapter.py", "--scenarios", ".\reports\template_adapter_run\scenarios.json", "--out", ".\reports\template_adapter_run\model_runs.json")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "validate-runs", "--runs", ".\reports\template_adapter_run\model_runs.json", "--out-dir", ".\reports\template_adapter_run")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "verify", "--runs", ".\reports\template_adapter_run\model_runs.json", "--out-dir", ".\reports\template_adapter_run")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "evaluate-runs", "--runs", ".\reports\template_adapter_run\model_runs.json", "--out-dir", ".\reports\external_eval")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "generate", "--clean", "--out-dir", ".\reports\sandbox_reader_run")
Invoke-Checked python @(".\adapters\sandbox_reader_adapter.py", "--scenarios", ".\reports\sandbox_reader_run\scenarios.json", "--out", ".\reports\sandbox_reader_run\model_runs.json", "--adapter-id", "sandbox_reader_adapter:regression_subject")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "evaluate-runs", "--runs", ".\reports\sandbox_reader_run\model_runs.json", "--out-dir", ".\reports\sandbox_reader_eval")
Invoke-Checked python @(".\adapters\sandbox_reader_adapter.py", "--scenarios", ".\reports\sandbox_reader_run\scenarios.json", "--out", ".\reports\sandbox_reader_run\model_runs.leaky_analysis.json", "--variant", "leaky_analysis", "--adapter-id", "sandbox_reader_adapter:regression_subject")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "evaluate-runs", "--runs", ".\reports\sandbox_reader_run\model_runs.leaky_analysis.json", "--out-dir", ".\reports\sandbox_reader_leaky_eval")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "compare-benchmarks", "--base", ".\reports\sandbox_reader_eval", "--candidate", ".\reports\sandbox_reader_leaky_eval", "--out-dir", ".\reports\sandbox_reader_regression")
Invoke-Checked python @(".\build_demo_report.py", "--out", ".\reports\DEMO_REPORT.md")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "all", "--clean", "--mode", "unsafe", "--out-dir", ".\reports\unsafe_eval_run")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "benchmark", "--clean", "--out-dir", ".\reports\benchmark")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "benchmark", "--clean", "--modes", "unsupported_claim", "--out-dir", ".\reports\comparison_base")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "benchmark", "--clean", "--modes", "safe", "--out-dir", ".\reports\comparison_candidate")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "compare-benchmarks", "--base", ".\reports\comparison_base", "--candidate", ".\reports\comparison_candidate", "--out-dir", ".\reports\benchmark_comparison")
Invoke-Checked python @(".\agent_safety_eval_harness.py", "trace-contracts", "--out-dir", ".\reports\trace_contracts")
Invoke-Checked python @(".\build_frontier_backlog.py", "--out-dir", ".\reports\frontier_backlog")
Invoke-Checked python @(".\build_next_step_review_packet.py", "--out-dir", ".\reports\next_step_review")
Invoke-Checked python @(".\build_maintainer_report.py", "--out", ".\reports\MAINTAINER_EVALUATION_REPORT.md")
Invoke-Checked powershell @("-ExecutionPolicy", "Bypass", "-File", ".\real_agent_smoke.ps1")
Invoke-Checked python @("-m", "pytest", ".\tests")

Write-Host "HDF-011 reproduction complete"
