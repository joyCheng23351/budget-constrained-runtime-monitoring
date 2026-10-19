"""Offline subset selection on recorded trace IDs (not runtime instrumentation)."""
import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from artifact_tool import Blob, SpreadsheetFile

METHODS = ["random", "frequency", "utility_cost", "redundancy_greedy", "knapsack_additive"]
BUDGETS = [10, 20, 30, 50, 80]

def load(path):
    wb = SpreadsheetFile.import_xlsx(Blob.load(str(path)))
    sh = wb.worksheets.get_item("Monitor profile")
    rows = sh.get_range("A1:P220").values
    names = rows[0]
    out = defaultdict(list)
    for row in rows[1:]:
        if not row[0]:
            continue
        d = dict(zip(names, row))
        p = str(d["project"])
        traces = frozenset(x.strip() for x in str(d["trace_ids"] or "").split("|") if x.strip())
        out[p].append(dict(id=f"{p}:{len(out[p]):04d}", location=str(d["source_location"]),
                           spec=str(d["monitor_specification"]), frequency=int(d["monitor_frequency"]),
                           cost=int(d["cost_proxy_event_checks"]), traces=traces))
    return out

def cover(selected):
    result = set()
    for monitor in selected:
        result.update(monitor["traces"])
    return result

def select(rows, budget, method, seed=42, scale=1000):
    remaining = list(rows)
    chosen = []
    used = 0
    if method == "random":
        random.Random(seed).shuffle(remaining)
    elif method == "frequency":
        remaining.sort(key=lambda x: (-x["frequency"], x["id"]))
    elif method == "utility_cost":
        remaining.sort(key=lambda x: (-len(x["traces"])/x["cost"], -len(x["traces"]), x["id"]))
    elif method == "knapsack_additive":
        unit = max(1, math.ceil(sum(x["cost"] for x in rows)/scale))
        capacity = int(budget//unit)
        dp = [(0, ()) for _ in range(capacity+1)]
        for j, x in enumerate(rows):
            c = math.ceil(x["cost"]/unit)
            if c > capacity:
                continue
            for b in range(capacity, c-1, -1):
                score = dp[b-c][0] + len(x["traces"])
                if score > dp[b][0]:
                    dp[b] = (score, dp[b-c][1]+(j,))
        return [rows[i] for i in max(dp, key=lambda x:x[0])[1]]
    elif method == "redundancy_greedy":
        covered = set()
        while True:
            feasible = [x for x in remaining if used+x["cost"] <= budget and x["traces"]-covered]
            if not feasible:
                break
            x = max(feasible, key=lambda y:(len(y["traces"]-covered)/y["cost"],
                                           len(y["traces"]-covered), -y["cost"]))
            chosen.append(x)
            remaining.remove(x)
            used += x["cost"]
            covered.update(x["traces"])
        return chosen
    for x in remaining:
        if used+x["cost"] <= budget:
            chosen.append(x)
            used += x["cost"]
    return chosen

def write_csv(path, rows):
    if rows:
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/valg-algorithm-input.xlsx")
    parser.add_argument("--output", default="results/offline")
    parser.add_argument("--random-trials", type=int, default=30)
    args = parser.parse_args()
    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=True)
    data = load(Path(args.input))
    records, selections, summary = [], [], []
    for project, monitors in data.items():
        assert all(m["cost"] > 0 for m in monitors)
        universe = cover(monitors)
        total = sum(m["cost"] for m in monitors)
        summary.append(dict(project=project, groups=len(monitors), trace_universe=len(universe),
                            total_proxy_cost=total, violations_attributed=False))
        for percent in BUDGETS:
            budget = total*percent/100
            for algorithm in METHODS:
                repeats = args.random_trials if algorithm == "random" else 1
                for trial in range(repeats):
                    chosen = select(monitors, budget, algorithm, seed=42+trial)
                    observed = cover(chosen)
                    cost = sum(m["cost"] for m in chosen)
                    assert cost <= budget+1e-6
                    assert observed <= universe
                    records.append(dict(project=project, budget_pct=percent, algorithm=algorithm,
                                        trial=trial, trace_recall=len(observed)/len(universe),
                                        trace_count=len(observed), monitor_count=len(chosen),
                                        proxy_cost=cost, proxy_budget=budget,
                                        proxy_cost_pct=100*cost/total))
                    selections.append(dict(project=project, budget_pct=percent, algorithm=algorithm,
                                           trial=trial, selected_ids="|".join(m["id"] for m in chosen)))
    write_csv(destination/"metrics_raw.csv", records)
    write_csv(destination/"selections.csv", selections)
    aggregates = []
    for project in data:
        for percent in BUDGETS:
            for algorithm in METHODS:
                subset = [r for r in records if (r["project"],r["budget_pct"],r["algorithm"]) ==
                          (project, percent, algorithm)]
                recalls = [r["trace_recall"] for r in subset]
                aggregates.append(dict(project=project, budget_pct=percent, algorithm=algorithm,
                    mean_trace_recall=mean(recalls),
                    sd_trace_recall=stdev(recalls) if len(recalls)>1 else 0,
                    mean_proxy_cost=mean(r["proxy_cost"] for r in subset),
                    mean_selected_groups=mean(r["monitor_count"] for r in subset), trials=len(subset)))
    write_csv(destination/"metrics_summary.csv", aggregates)
    (destination/"dataset_summary.json").write_text(json.dumps(summary, indent=2))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        for project in data:
            fig, ax = plt.subplots(figsize=(8, 5))
            for algorithm in METHODS:
                subset = [r for r in aggregates if r["project"]==project and r["algorithm"]==algorithm]
                ax.plot([r["budget_pct"] for r in subset],
                        [100*r["mean_trace_recall"] for r in subset], marker="o", label=algorithm)
            ax.set(title=f"{project}: unique trace recall under proxy budgets",
                   xlabel="Event-check proxy budget (% of full proxy)", ylabel="Unique trace recall (%)",
                   ylim=(0, 102))
            ax.grid(alpha=.25)
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(destination/f"{project}_trace_recall.png",dpi=180)
            plt.close(fig)
    except ImportError:
        pass
    for r in aggregates:
        print(f"{r['project']:11} {r['budget_pct']:2}% {r['algorithm']:20} "
              f"recall={r['mean_trace_recall']:.3f} sd={r['sd_trace_recall']:.3f}")

if __name__ == "__main__":
    main()
