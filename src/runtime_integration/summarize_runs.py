#!/usr/bin/env python3
"""Summarize repeat-level runtime integration measurements."""

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="repeat-level CSV")
    parser.add_argument("output", type=Path, help="summary CSV")
    args = parser.parse_args()
    with args.input.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    grouped = defaultdict(list)
    for row in rows:
        grouped[(
            row["project"],
            row["configuration"],
            row.get("budget_pct", ""),
            row.get("algorithm", ""),
        )].append(row)

    output = []
    for key, group in sorted(grouped.items()):
        elapsed = [float(row["elapsed_seconds"]) for row in group]
        memory = [
            float(row.get("peak_container_memory_kb", row.get("peak_rss_kb", "")))
            for row in group
            if row.get("peak_container_memory_kb", row.get("peak_rss_kb", ""))
        ]
        output.append(
            {
                "project": key[0],
                "configuration": key[1],
                "budget_pct": key[2],
                "algorithm": key[3],
                "repetitions": len(group),
                "mean_elapsed_seconds": statistics.mean(elapsed),
                "sd_elapsed_seconds": statistics.stdev(elapsed) if len(elapsed) > 1 else 0.0,
                "mean_peak_container_memory_kb": statistics.mean(memory) if memory else "",
                "sd_peak_container_memory_kb": statistics.stdev(memory) if len(memory) > 1 else 0.0,
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)


if __name__ == "__main__":
    main()
