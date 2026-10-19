# Budget-Constrained Selective Runtime Monitoring

CS 6158 project by Shiyun Cheng and Gengkun Shao.

## Scope
This repository focuses on **real historical TraceMOP/Valg profiling data** and offline budget-constrained monitor-group selection. Earlier synthetic and Valgrind prototype experiments are intentionally excluded.

The five implemented strategies are random, frequency ranking, standalone trace utility/cost, redundancy-aware greedy marginal coverage/cost, and additive knapsack.

## Evaluation
Two Java workloads: javadbf (153 inferred location/spec groups; 278 historical distinct trace IDs) and jlemmagen (66 groups; 2,115 historical distinct trace IDs). Budgets are 10%, 20%, 30%, 50%, and 80% of the **event-check cost proxy**, not measured runtime. Random selection uses 30 trials.

At a 20% proxy budget, both utility/cost and redundancy-aware greedy achieve 97.84% historical unique-trace recall on javadbf and 99.67% on jlemmagen.

These results **do not** establish held-out violation recall, actual runtime savings, or superiority over Valg at matched realized cost.

## Files
- `src/run_experiments.py`: offline selection and evaluation
- `data/valg-algorithm-input.xlsx`: historical monitor-group data
- `data/valg-subset-dashboard.xlsx`: separate Valg baseline reproduction results
- `results/offline/`: generated metrics, selections, and plots
- `reports/`: midterm progress report and detailed real-trace experiment report

## Reproduce
```bash
python -m pip install -r requirements.txt
python src/run_experiments.py --input data/valg-algorithm-input.xlsx --output results/reproduced --random-trials 30
```

## Remaining work
Validate location attribution, collect per-location violations, implement selectively enabled monitors, measure actual runtime and memory, and compare with Valg at matched realized costs on held-out executions.

## Data rights
Keep this repository private unless the team has confirmed permission to redistribute the input workbooks.
