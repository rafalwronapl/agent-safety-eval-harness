# Quickstart

This is the 10-minute path for understanding what the harness does.

To preview the output without running code, open `examples/reports/` first.
Those static snapshots show a safe pass, an interpretable failure, and a
not-interpretable missing-evidence run.

## 1. Install Test Dependencies

```powershell
python -m pip install -e .[test]
```

## 2. Run A Safe Baseline

```powershell
python .\agent_safety_eval_harness.py all --clean --mode safe --out-dir .\reports\quickstart_safe
```

Open:

- `reports/quickstart_safe/report.md`
- `reports/quickstart_safe/verdict.json`

Expected shape: all scenarios should pass because the built-in safe stub emits
the expected evidence.

## 3. Run A Leaky Baseline

```powershell
python .\agent_safety_eval_harness.py all --clean --mode unsafe --out-dir .\reports\quickstart_unsafe
```

Open:

- `reports/quickstart_unsafe/report.md`
- `reports/quickstart_unsafe/scores.csv`

Expected shape: failures should cluster around unsafe actions, secret exposure,
data minimization, access denial, and unsupported claims.

## 4. Run The Main Demo

```powershell
.\reproduce.ps1
```

Then open:

- `reports/DEMO_REPORT.md`
- `reports/sandbox_reader_regression/benchmark_comparison.md`
- `reports/sandbox_reader_eval/maintainer_summary.md`
- `reports/sandbox_reader_leaky_eval/maintainer_summary.md`

The demo compares a safe sandbox reader with a leaky variant. The important
property is that evidence coverage stays sufficient while behavior gets worse,
so the regression is interpretable.

## 5. Read A Result

Use `maintainer_summary.md` first. The key fields are:

- `verdict`: whether the run is interpretable;
- `evidence coverage`: whether required evidence was present;
- `evidence trust`: whether evidence was transcript-backed or adapter-reported;
- `behavior failures`: model/agent behavior issues after evidence quality is
  accounted for;
- `severity total`: weighted impact across failed scenarios.

See `RESULT_INTERPRETATION.md` for the full reading guide.

## 6. Real-Agent Runs

For real agents, do not start with the full suite. Start with one scenario:

```powershell
python .\agent_safety_eval_harness.py generate --clean --out-dir .\reports\real_agent_pilot
python .\adapters\codex_json_agent_adapter.py `
  --scenarios .\reports\real_agent_pilot\scenarios.json `
  --out .\reports\real_agent_pilot\model_runs.codex.json `
  --raw-trace-dir .\reports\real_agent_pilot\raw_codex `
  --scenario-id data_minimization
```

A real-agent comparison is not ready just because it produced safe-looking
answers. It is ready only when `evaluate-runs` passes, evidence is sufficiently
transcript-backed, and generated artifacts have been reviewed or scanned.
