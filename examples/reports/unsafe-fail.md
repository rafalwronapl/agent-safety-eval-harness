# Example: Interpretable Fail

This snapshot shows a useful failure: evidence is sufficient, so behavior
regressions are meaningful synthetic findings.

Source shape: leaky sandbox-reader regression subject.

| adapter | verdict | pass rate | evidence coverage | evidence trust | behavior failures | safety failures | evidence failures |
|---|---|---:|---:|---|---:|---:|---:|
| `sandbox_reader_adapter:regression_subject` | `interpretable_with_failures` | 42% | 100% | `adapter_reported` | 23 | 23 | 0 |

How to read it:

- `interpretable_with_failures` means the trace/evidence is good enough to inspect behavior.
- Evidence did not disappear; the adapter actually hit the scenario contracts.
- The failure is therefore not just a harness logging problem.

Common failure classes in this shape:

- data minimization failures;
- unsupported or unverifiable claims;
- access-boundary failures;
- private trace/detail leakage.

Reproduce locally:

```powershell
.\reproduce.ps1
```

Then open:

- `reports/sandbox_reader_leaky_eval/maintainer_summary.md`
- `reports/sandbox_reader_regression/benchmark_comparison.md`
