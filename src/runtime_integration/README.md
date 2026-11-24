# Runtime integration for budget-constrained monitoring

This directory connects the existing offline selection algorithms to an actual
Valg/JavaMOP monitor-creation decision. The runtime key is the pair
`(monitor specification, enclosing type + source file:line)`. The AspectJ
object identity suffix is removed because it is not stable across JVM
executions. The event method name is also excluded because the historical
first-event method and runtime API join-point method can differ at the same
creation site.

## What is implemented

1. `export_policy.py` converts one row from `results/offline/selections.csv`
   into an explicit two-column allowlist.
2. `valg_patch/selective-location-policy.patch` adds an optional runtime gate
   to the official Valg artifact. With no policy variable, original Valg
   behavior is preserved. With a policy, a monitor is created only when its
   specification/location pair is selected.
3. The patched runtime writes per-key `created` and `skipped` counts at JVM
   shutdown. This provides direct evidence that candidate groups can be
   independently enabled or disabled.
4. `run_javadbf_policy.sh` runs a real evaluation project repeatedly and saves
   the Maven log, decision counts, elapsed time, and peak Docker-container
   memory for every repetition.
5. `summarize_runs.py` aggregates repeat-level time and peak-RSS measurements.

## One complete example

Run commands from the repository root.

```bash
python3 src/runtime_integration/export_policy.py \
  --project javadbf --budget 20 --algorithm redundancy_greedy --trial 0 \
  --output results/runtime/policies/javadbf-b20-redundancy-greedy.tsv

bash src/runtime_integration/apply_valg_patch.sh /absolute/path/to/Valg
```

Rebuild both policy-aware agents inside the official Valg Docker environment:

```bash
cd /home/Valg/Valg/scripts
bash install.sh false false
cp no-track-no-stats-agent.jar valgj-policy-agent.jar
bash install.sh true false
cp track-no-stats-agent.jar valgt-policy-agent.jar
```

Then run five Java-mode repetitions from the host:

```bash
bash src/runtime_integration/run_javadbf_policy.sh \
  valg-repro results/runtime/policies/javadbf-b20-redundancy-greedy.tsv \
  javadbf-b20-redundancy-greedy 5
```

## Policy format and runtime options

The policy is tab-separated, one allowed key per line:

```text
# specification    stable_creation_location
Collections_SortBeforeBinarySearchMonitor    com.example.A(A.java:42)
```

The patched agent recognizes:

- system property `valg.selection.file` or environment variable
  `VALG_SELECTION_FILE`;
- system property `valg.selection.log` or environment variable
  `VALG_SELECTION_LOG`.

An absent policy means ordinary Valg. An existing empty policy intentionally
rejects every candidate. This makes full/Valg/selected/deny-all sanity checks
possible without rebuilding between policies.

## Evaluation discipline

Historical profile data is used only to produce the allowlist. Runtime outcome
metrics must come from a separate execution. Repeating the same test suite in a
fresh JVM validates execution separation but is not a held-out-test evaluation;
use a distinct test selector or workload if the claim specifically requires
generalization to unseen tests.

For each configuration, preserve raw logs and record at least five repetitions
of elapsed time and peak RSS. Compute trace recall against full TraceMOP and
violation recall against full JavaMOP on the same project revision and test
workload. Valg must be run on the same revision and repetitions for the fair
overhead-versus-coverage comparison.
