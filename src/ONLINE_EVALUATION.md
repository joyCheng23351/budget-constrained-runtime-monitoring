# Online selection and evaluation handoff

## Generate configurations (selection owner)

From repository root:

```bash
python -m pip install -r requirements.txt
python src/generate_online_manifests.py --history data/valg_profiles/monitor_profile.csv --random-trials 5
```

The five existing algorithms are reused at 10, 20, 30, 50 and 80 percent of historical event-check proxy cost. Each random seed has its own configuration; deterministic algorithms have one configuration per budget. Full and none are additional controls. Each JSON contains selected_ids and selected_candidates, including exact historical location/specification strings. IDs are stable hashes of the project/location/specification tuple, not the row-number IDs in the old offline results. The assumed location ID is not a verified runtime key. No runtime overhead guarantee follows from the proxy budget.

## Runtime owner interface

Verify a one-to-one mapping from the registry to independently switchable runtime creation sites; do not silently drop or merge unmatched candidates. Record the actual enabled candidate IDs, not simply a copy of the request. Run fresh workloads not used to construct the historical profile; ideally use held-out tests, or independently collected executions with the distinction documented. Freeze manifests before evaluation. A full configuration must represent genuinely complete monitoring; if the historical registry does not cover all runtime sites, resolve this before treating it as full. Run none, full, Valg and selected configurations with matched workload, revision, JVM, instrumentation/trace mode and measurement boundaries; use five independent repeats, randomized order, and consistent process-tree peak RSS measurement. Compare ValgT with trace collection and ValgJ with violation monitoring only when measurement modes are comparable; use separate input files for different modes.

Return a CSV with these columns:

```csv
project,workload,repeat,config_id,status,wall_seconds,peak_rss_bytes,enabled_ids,trace_ids,violation_ids
```

Use config_id from manifest_index.csv (or valg for the comparator). status must be ok for a successful measurement. Array fields are JSON arrays encoded as CSV cells. Use [] for a measured empty set; blank violation_ids means unavailable, never zero violations. Trace IDs must be canonical trace signatures consistent across paired executions, not independently numbered trace IDs. Violation IDs should be stable, reliably attributable signatures (e.g. specification + reported site, optionally test identity if available); this measures unique signatures, not occurrence recall. A mode with no comparable trace collection is not suitable for trace recall; do not encode unavailable traces as an empty set for a supposedly comparable trace experiment. Record logs and failures separately; do not treat failed runs as empty observations.

## Evaluate (selection owner)

```bash
python src/evaluate_online.py --input results/online/runtime_runs.csv
```

For each paired project/workload/repeat, recall is the intersection with full monitoring divided by the full set size. Empty reference sets produce undefined recall. Time and memory overhead are relative to no monitoring, not the proxy. Report mean and sample SD across repeats separately for each configuration (random selection seeds remain separate). Plots show realized overhead and recall, including Valg where available. Compare at similar realized cost, not equal nominal budget; report when no comparable point exists. Unexpected IDs are flagged in raw metrics for investigation. Check five repeats per configuration, matching provenance, and coverage completeness before drawing conclusions.

## Current limitations

Historical profiles do not establish true switchability or per-location violation labels. No fresh runtime data is included here. The final results and report conclusions are pending measured logs; do not substitute historical recall for prospective recall.
