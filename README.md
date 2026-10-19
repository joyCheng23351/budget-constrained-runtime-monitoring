# Budget-Constrained Selective Runtime Monitoring

CS 6158 midterm research code and reports (Shiyun Cheng and Gengkun Shao). This repository focuses on real historical TraceMOP/Valg data; early synthetic prototypes are excluded.

## What is measured

The `src/run_experiments.py` experiment selects groups using **historical TraceMOP trace-ID coverage** with `cost_proxy_event_checks` as an **event-check proxy budget**. It does NOT measure actual runtime/memory, violation recall, or deployment of policies within Valg. The candidate identifiers are inferred location-by-specification groups rather than verified switchable creation sites.

The separate `data/valg-subset-dashboard.xlsx` contains partner-generated Valg reproduction baselines. These are not matched-cost head-to-head experiments with the budget-selection algorithms.

## Reproduce

Python 3.10+ recommended. From the repository root:

```bash
python -m pip install -r requirements.txt
python src/run_experiments.py --input data/valg-algorithm-input.xlsx --output results/reproduced --random-trials 30
```

Saved outputs used for the report are in `results/offline/`. The selected-set algorithms are Random, Frequency, Utility/cost, Redundancy-aware Greedy, and Additive Knapsack.

## Main results

At the 20% **proxy** budget, unique historical trace recall: javadbf 97.84% for utility/cost and greedy; jlemmagen 99.67% for the same methods. These are offline observations, not prospective coverage guarantees.

## Files

- `reports/CS6158_midterm_report.pdf` — updated 2–3 page midterm submission.
- `reports/Valg_Offline_Experiment_Report.pdf` — supplemental experiment report.
- `src/run_experiments.py` — real-trace offline experiment runner.
- `data/` — original partner-provided workbooks (confirm permission before publishing).
- `results/offline/` — precomputed metrics, selections, and plots.

## Known gaps

No held-out executions, independently switchable creation locations, location-specific violation coverage, actual per-configuration overhead or matching against Valg at realized cost. These are remaining semester milestones.
