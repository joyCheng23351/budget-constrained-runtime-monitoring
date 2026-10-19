#!/usr/bin/env python3

import csv
import re
import sys
from pathlib import Path


def parse_duration(console_path: Path):
    if not console_path.exists():
        return None
    matches = re.findall(r"\[OK\] Duration:\s*(\d+)\s*ms", console_path.read_text(errors="replace"))
    return int(matches[-1]) if matches else None


def parse_real_seconds(log_path: Path):
    if not log_path.exists():
        return None
    text = log_path.read_text(errors="replace")
    matches = re.findall(r"^real\s+(?:(\d+)m)?([0-9.]+)s$", text, flags=re.MULTILINE)
    if not matches:
        return None
    minutes, seconds = matches[-1]
    return (int(minutes or 0) * 60) + float(seconds)


def parse_violations(path: Path):
    if not path.exists():
        return None, None
    total = 0
    unique_rows = 0
    for raw in path.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        unique_rows += 1
        match = re.match(r"^(\d+)\s+", line)
        total += int(match.group(1)) if match else 1
    return total, unique_rows


def parse_trace_dir(trace_dir: Path):
    unique_file = trace_dir / "unique-traces.txt"
    locations_file = trace_dir / "locations.txt"
    if not unique_file.exists():
        return None, None, None, None

    unique_count = 0
    frequency_sum = 0
    for raw in unique_file.read_text(errors="replace").splitlines()[1:]:
        match = re.match(r"^(\d+)\s+(\d+)\s+", raw.strip())
        if not match:
            continue
        unique_count += 1
        frequency_sum += int(match.group(2))

    location_count = None
    if locations_file.exists():
        location_count = sum(1 for line in locations_file.read_text(errors="replace").splitlines()[1:] if line.strip())

    # For this artifact format, each unique trace contributes one necessary
    # instance. The remainder is a useful derived duplicate-instance count.
    derived_duplicate_instances = max(frequency_sum - unique_count, 0)
    return unique_count, frequency_sum, derived_duplicate_instances, location_count


def read_status(project_dir: Path):
    result = {}
    path = project_dir / "status.tsv"
    if not path.exists():
        return result
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            result[row["mode"]] = int(row["exit_code"])
    return result


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: summarize_subset.py <run-directory>")

    run_dir = Path(sys.argv[1]).resolve()
    rows = []
    for project_dir in sorted(path for path in run_dir.iterdir() if path.is_dir()):
        slug = project_dir.name
        status = read_status(project_dir)
        artifact = project_dir / "artifact-output"
        saved = artifact / "saved-logs"

        no_rv_seconds = parse_real_seconds(saved / "no-rv-baseline.log")
        if no_rv_seconds is not None:
            rows.append({
                "project": slug, "mode": "no-RV", "status": "success",
                "duration_ms": round(no_rv_seconds * 1000),
                "violation_occurrences": 0, "unique_violation_rows": 0,
                "unique_traces": "", "trace_frequency_sum": "",
                "derived_duplicate_trace_instances": "", "locations": "",
            })

        mode_specs = [
            ("01-valgj", "ValgJ", saved / "valgj-violation-counts.txt", None),
            ("02-javamop", "JavaMOP", saved / "javamop-violation-counts.txt", None),
            ("03-valgt", "ValgT", saved / "valgt-violation-counts.txt", artifact / "valgt-all-traces"),
            ("04-tracemop", "TraceMOP", saved / "tracemop-violation-counts.txt", artifact / "tracemop-all-traces"),
        ]

        for mode_key, mode_name, violation_file, trace_dir in mode_specs:
            exit_code = status.get(mode_key)
            duration_ms = parse_duration(project_dir / f"{mode_key}.console.log")
            violation_total, unique_violation_rows = parse_violations(violation_file)
            unique_traces = frequency_sum = duplicate_instances = locations = None
            if trace_dir is not None and trace_dir.exists():
                unique_traces, frequency_sum, duplicate_instances, locations = parse_trace_dir(trace_dir)
            rows.append({
                "project": slug,
                "mode": mode_name,
                "status": "success" if exit_code == 0 else "failed" if exit_code is not None else "not-run",
                "duration_ms": duration_ms if duration_ms is not None else "",
                "violation_occurrences": violation_total if violation_total is not None else "",
                "unique_violation_rows": unique_violation_rows if unique_violation_rows is not None else "",
                "unique_traces": unique_traces if unique_traces is not None else "",
                "trace_frequency_sum": frequency_sum if frequency_sum is not None else "",
                "derived_duplicate_trace_instances": duplicate_instances if duplicate_instances is not None else "",
                "locations": locations if locations is not None else "",
            })

    fieldnames = [
        "project", "mode", "status", "duration_ms",
        "violation_occurrences", "unique_violation_rows",
        "unique_traces", "trace_frequency_sum",
        "derived_duplicate_trace_instances", "locations",
    ]
    output = run_dir / "summary.csv"
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(output)


if __name__ == "__main__":
    main()

