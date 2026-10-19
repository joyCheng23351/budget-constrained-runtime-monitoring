# Offline experiment results (historical traces)

These numbers are **offline trace coverage under event-check proxy budgets**, not live violation recall or measured runtime overhead.

At the 20% proxy budget:

| Algorithm | javadbf trace recall | jlemmagen trace recall |
|---|---:|---:|
| Random (mean, 30 trials) | 86.51% | 65.56% |
| Frequency | 44.96% | 88.84% |
| Utility/cost | 97.84% | 99.67% |
| Redundancy-aware greedy | 97.84% | 99.67% |
| Additive knapsack | 89.57% | 99.57% |

The historical datasets have 153 monitor location/specification groups and 278 observed unique traces (javadbf), and 66 groups and 2,115 observed unique traces (jlemmagen). Random selection has substantial variability, especially for jlemmagen. Fixed-order frequency selection can be nonmonotone when budgets change because a costly monitor admitted earlier displaces cheaper monitors. Additive knapsack double-counts coverage overlap in its optimization objective.

The full precomputed CSV tables, binary source workbooks, and report PDFs are distributed separately in the prepared submission ZIP until uploaded to this repository.

Do **not** interpret proxy-cost percentages as runtime speedups; these are not held-out execution measurements. 
