# Architecture

This project is organized as a small offline harness with a thin public CLI
module and focused helper modules.

## Core Flow

1. `hdf_generation.py` writes synthetic sandboxes and `scenarios.json`.
2. An adapter writes `model_runs.json`.
3. `hdf_model_runs.py` validates and loads adapter output.
4. `hdf_scoring.py` scores each run against synthetic safety and trace checks.
5. `hdf_run_reports.py` writes per-run artifacts.
6. `hdf_benchmark_reports.py` writes benchmark, maintainer, and regression
   comparison artifacts.
7. `hdf_trace_contracts.py` writes the scenario/surface/evidence matrix.

`agent_safety_eval_harness.py` keeps the public CLI and orchestration entry
points. It also re-exports key helpers for backward compatibility with the
adapters and tests.

## Module Map

- `hdf_contracts.py`: shared dataclasses.
- `hdf_scenarios.py`: static scenario catalog.
- `hdf_synthetic_data.py`: fake canaries, role-change fixture, and public/private synthetic labels.
- `hdf_surfaces.py`: scenario surface tags and differentiator labels.
- `hdf_evidence.py`: required evidence contracts and missing-evidence formatting.
- `hdf_scoring.py`: leakage, tool-boundary, data-minimization, and recusal detectors.
- `hdf_scoring_metadata.py`: severity weights and severity aggregation.
- `hdf_model_runs.py`: `model_runs.json` schema validation, serialization, and loading.
- `hdf_generation.py`: sandbox and manifest generation.
- `hdf_run_reports.py`: per-run markdown, score CSV, and tool-call JSONL writers.
- `hdf_benchmark_reports.py`: scorecards, harness quality, maintainer summaries, and benchmark comparison reports.
- `hdf_trace_contracts.py`: trace-contract matrix generation.
- `hdf_io.py`: filesystem writes and guarded clean behavior.

## Claim Boundary

The architecture intentionally keeps synthetic evidence contracts separate from
claims about real exploitability. Real-agent runs are comparison-ready only
when required evidence is transcript-backed or tied to a trusted trace
reference.
