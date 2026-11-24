# Raw runtime validation artifacts

This directory contains the raw artifacts behind the five-run `javadbf`
runtime-integration pilot described in `results/runtime/VALIDATION.md`.

## Files

- `javadbf-b20-greedy-5runs-metrics.csv` is the repeat-level measurement
  table. It records elapsed wall time and sampled peak Docker-container memory
  for each fresh JVM execution.
- `javadbf-b20-greedy-5runs-summary.csv` is derived from the repeat-level CSV
  with `src/runtime_integration/summarize_runs.py`.
- `*.selection-decisions.tsv` is the shutdown summary written by the patched
  Valg runtime. Each row is one normalized specification/location key and its
  monitor-creation `created` and `skipped` counts. The `__TOTAL__` row is a
  runtime-produced total, not a post-hoc estimate.
- `*.console.log` contains the host-side completion and duration lines.
- `*.docker-memory.log` contains the raw `docker stats` memory samples used to
  calculate the peak memory column.
- `*.mop.log.gz` is the compressed Maven/JavaMOP log copied from the
  corresponding run output.

## Provenance and limits

All five runs used project `albfernandez/javadbf` at revision
`395265f33bcf9080b02f2102c4b6284921cefae2`, the full test suite, and the
policy in `results/runtime/policies/javadbf-b20-redundancy-greedy.tsv`.
The runs validate that the allowlist reaches the real monitor-creation path.
They do not contain comparable TraceMOP trace signatures or stable violation
signatures, so they must not be used to claim trace or violation recall.

Reproduce the run with:

```bash
bash src/runtime_integration/run_javadbf_policy.sh \
  valg-repro \
  results/runtime/policies/javadbf-b20-redundancy-greedy.tsv \
  javadbf-b20-greedy-5runs \
  5
```

