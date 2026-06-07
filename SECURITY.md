# Security Policy

This project is an offline synthetic evaluation harness. It does not contain
real secrets, exploit live systems, or test live infrastructure.

## Reporting Issues

If you find a security-relevant issue in the harness itself, open a private
report through the repository host when available, or contact the maintainer
before publishing details.

Useful reports include:

- a way to make generated artifacts include real credentials;
- a cleanup or path traversal bug in local harness commands;
- a false readiness signal for adapter-reported evidence;
- a way for a malformed adapter output to bypass validation.

## Non-Scope

The synthetic scenarios are not vulnerability reports against vendors, models,
or products. A failed scenario means the harness observed a synthetic
regression signal under the local adapter contract. It does not prove real
exploitability.

## Artifact Handling

Before sharing real-agent artifacts, run:

```powershell
python .\scan_artifacts.py .\reports --out-dir .\reports\artifact_secret_scan
```

Do not publish raw traces from real agents unless they have been reviewed for
credentials, personal data, proprietary prompts, and tool outputs.
