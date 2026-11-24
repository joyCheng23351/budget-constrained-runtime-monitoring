# Final presentation result figures

## 1. Repeated runtime and memory

![Five-run runtime and memory](figures/figure1_runtime_memory_repetitions.png)

The 20% proxy-budget redundancy-aware greedy policy completed all five fresh
`javadbf` JVM executions. Mean elapsed time was 35.21 seconds with a sample
standard deviation of 12.68 seconds. Mean peak Docker-container memory was
921.9 MiB with a sample standard deviation of 24.7 MiB. The second repetition
was slower than the other four, which is why the performance claim must report
the distribution rather than only its best run.

## 2. Monitor-creation decisions

![Monitor creation decisions](figures/figure2_monitor_creation_decisions.png)

Every repetition created 5,405 monitors and skipped 131,889 creation attempts.
The identical counts demonstrate deterministic policy enforcement across fresh
JVM executions. The policy skipped 96.06% of observed creation attempts. This
figure validates the runtime gate; it does not by itself show trace or violation
recall.

## 3. Valg artifact baseline

![ValgJ and JavaMOP runtime comparison](figures/figure3_valgj_javamop_runtime_comparison.png)

The earlier artifact reproduction completed no-RV, ValgJ, and JavaMOP on four
projects. ValgJ was faster than JavaMOP on `jlemmagen`, `route53-infima`, and
`xeger`, but slower on `javadbf`. These are single-run baseline measurements,
so they establish successful artifact execution rather than stable performance.

## 4. Historical offline trace recall

![Offline trace recall](figures/figure4_offline_trace_recall_20pct.png)

At a 20% historical event-check proxy budget, utility/cost and
redundancy-aware greedy preserved 97.84% of observed `javadbf` traces and 99.67%
of observed `jlemmagen` traces. These values come from historical replay, not a
fresh held-out execution. They justify which policy to deploy, while the runtime
figures above validate that the selected policy can control real monitor
creation.
