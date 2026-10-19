# Budget-Constrained Selective Runtime Monitoring

CS 6158 research project. The objective is to allocate a fixed monitor-creation budget using historical trace coverage, frequency, and cost information, ultimately comparing against Valg at matched **realized** overhead.

## Status
This repository currently contains an **offline historical trace-coverage experiment** on javadbf and jlemmagen. Its budgets use an *event-check cost proxy*, not measured runtime. Coverage is of historically recorded unique trace IDs, **not** violation recall on held-out executions.

Algorithms: random, frequency, utility/cost, redundancy-aware marginal coverage greedy, and additive knapsack approximation.

## Reproduce
Install Python requirements, then supply `data/valg-algorithm-input.xlsx` and run:

```bash
python -m pip install -r requirements.txt
python src/run_experiments.py --input data/valg-algorithm-input.xlsx --output results/offline --random-trials 30
```

Outputs: `metrics_raw.csv`, `metrics_summary.csv`, `selections.csv`, `dataset_summary.json`, and two trace-recall plots.

**Data provenance:** The input spreadsheet was prepared from historical Valg/TraceMOP profiling. Monitor groups are approximated by location/specification; exact per-location violation attribution and true incremental runtime costs have not been established.

## Remaining work
Validate monitor-location correspondence, enable/disable monitors in real runs, collect violation attribution, hold out executions, measure actual CPU time and memory, and compare against Valg at equal realized monitoring overhead.

The current dataset and reports can be found in the local submission package until binary assets are uploaded.
