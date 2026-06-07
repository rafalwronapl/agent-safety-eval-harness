# Example Reports

These are small static snapshots of representative report outcomes. They are
not raw benchmark artifacts and do not include generated sandboxes, model runs,
or tool transcripts.

Use them to understand the reading model before running the harness locally:

- `safe-pass.md` - sufficient evidence and no synthetic behavior failures.
- `unsafe-fail.md` - sufficient evidence, but behavior failures are meaningful.
- `not-interpretable.md` - transcript-backed run with missing required evidence.

The full reports are generated under `reports/` when you run `QUICKSTART.md` or
`reproduce.ps1`. Generated reports remain ignored by git.
