$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExampleRunner = Join-Path $ScriptDir "adapters\example_cli_agent_runner.py"

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

Invoke-Checked python @(".\agent_safety_eval_harness.py", "generate", "--clean", "--out-dir", ".\reports\real_agent_smoke")
Invoke-Checked python @(
    ".\adapters\generic_cli_agent_adapter.py",
    "--scenarios",
    ".\reports\real_agent_smoke\scenarios.json",
    "--out",
    ".\reports\real_agent_smoke\model_runs.example.json",
    "--trace-dir",
    ".\reports\real_agent_smoke\raw_traces",
    "--adapter-id",
    "example_cli_agent:placeholder",
    "--trace-source",
    "example_cli_jsonl",
    "--",
    "python",
    $ExampleRunner
)
Invoke-Checked python @(
    ".\agent_safety_eval_harness.py",
    "evaluate-runs",
    "--runs",
    ".\reports\real_agent_smoke\model_runs.example.json",
    "--out-dir",
    ".\reports\real_agent_smoke_eval"
)
Invoke-Checked python @(
    ".\scan_artifacts.py",
    ".\reports\real_agent_smoke",
    ".\reports\real_agent_smoke_eval",
    "--out-dir",
    ".\reports\real_agent_smoke_secret_scan"
)
python ".\build_real_agent_readiness.py" `
    --eval-dir ".\reports\real_agent_smoke_eval" `
    --secret-scan-dir ".\reports\real_agent_smoke_secret_scan" `
    --out-dir ".\reports\real_agent_smoke_readiness"
if ($LASTEXITCODE -ne 1) {
    throw "example real-agent readiness smoke should return 1 because placeholder runner is intentionally not ready"
}
Invoke-Checked python @(
    ".\build_real_agent_demo_report.py",
    "--readiness",
    ".\reports\real_agent_smoke_readiness",
    "--secret-scan",
    ".\reports\real_agent_smoke_secret_scan",
    "--eval-dir",
    ".\reports\real_agent_smoke_eval",
    "--out",
    ".\reports\REAL_AGENT_DEMO_REPORT.md"
)

$TraceEvents = Get-ChildItem ".\reports\real_agent_smoke\raw_traces" -Filter "*.jsonl" |
    ForEach-Object { Get-Content $_.FullName } |
    Where-Object { $_.Trim() }
if (-not $TraceEvents) {
    throw "real-agent smoke produced no raw tool-log events"
}

$Runs = Get-Content ".\reports\real_agent_smoke\model_runs.example.json" -Raw | ConvertFrom-Json
if (-not $Runs) {
    throw "real-agent smoke produced no model runs"
}
foreach ($Run in $Runs) {
    if ($Run.evidence_source.type -ne "transcript_backed") {
        throw "run $($Run.scenario_id) is not transcript-backed"
    }
    if (-not (Test-Path $Run.evidence_source.raw_tool_log_path)) {
        throw "run $($Run.scenario_id) raw tool log does not exist: $($Run.evidence_source.raw_tool_log_path)"
    }
    $RunEvents = Get-Content $Run.evidence_source.raw_tool_log_path | Where-Object { $_.Trim() }
    if (-not $RunEvents) {
        throw "run $($Run.scenario_id) produced an empty raw tool log"
    }
}

$MaintainerSummary = Get-Content ".\reports\real_agent_smoke_eval\maintainer_summary.json" -Raw | ConvertFrom-Json
$AdapterSummary = $MaintainerSummary.adapters[0]
if ($AdapterSummary.evidence_trust_level -ne "transcript_backed") {
    throw "maintainer summary did not report transcript-backed evidence trust"
}
if ($AdapterSummary.transcript_backed_rate -ne 1) {
    throw "maintainer summary transcript-backed rate was $($AdapterSummary.transcript_backed_rate), expected 1"
}

Write-Host "Real-agent CLI smoke complete"
