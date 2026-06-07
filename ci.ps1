$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ScriptDir
try {
    python -m pip install -e ".[test]"
    python -m agent_safety_eval_harness --help > $null
    .\reproduce.ps1
}
finally {
    Pop-Location
}
