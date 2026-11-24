# Runtime integration validation

## Configuration

- Project: `albfernandez/javadbf`
- Revision: `395265f33bcf9080b02f2102c4b6284921cefae2`
- Policy: redundancy-aware greedy, 20% historical event-check proxy budget
- Exported policy: 149 location-by-specification rows
- Runtime key: normalized specification plus enclosing type and source file:line
- Repetitions: 5 fresh output directories and JVM executions

The policy came from historical profile data. Each runtime execution used the
project's full test suite. This separates policy construction from measurement
by execution, but it does not constitute a held-out-test evaluation.

## Observed results

| Metric | Result |
|---|---:|
| Tests per repetition | 154 run, 0 failures, 0 errors, 11 skipped |
| Mean elapsed time | 35.208 s |
| Sample SD elapsed time | 12.683 s |
| Mean peak container memory | 943,985 KiB (921.9 MiB) |
| Sample SD peak container memory | 25,254 KiB (24.7 MiB) |
| Monitor creations per repetition | 5,405 |
| Skipped creation attempts per repetition | 131,889 |

All five repetitions produced identical create/skip counts. This demonstrates
that the exported allowlist reaches the real monitor-creation path and applies
deterministically across fresh JVM executions.

## Claim boundary

This validation establishes executable switching and measurement collection.
It does not yet establish trace recall, violation recall, or superiority to
Valg at matched realized overhead. Those claims require full-monitoring and
ordinary-Valg runs on the same evaluation workload, plus a fresh or held-out
test split when claiming generalization.

Raw repeat-level timing, Docker memory samples, Maven logs, and decision logs
are stored in `results/runtime/validation/` with the prefix
`javadbf-b20-greedy-5runs`.
