#!/usr/bin/env python3
"""Convert offline selected row IDs into a stable Valg runtime allowlist."""

import argparse
import csv
import json
import re
from pathlib import Path


HISTORICAL_LOCATION = re.compile(r"^(?P<prefix>.+)\((?P<file>[^():]+\.java):(?P<line>\d+)\)\d*$")


def stable_location(value: str) -> str:
    value = value.strip()
    match = HISTORICAL_LOCATION.match(value)
    if not match:
        return re.sub(r"\)\d+$", ")", value)
    prefix = match.group("prefix")
    file_base = Path(match.group("file")).stem
    last_segment = prefix.rsplit(".", 1)[-1]
    owner = prefix.rsplit(".", 1)[0] if last_segment != file_base else prefix
    return f'{owner}({match.group("file")}:{match.group("line")})'


def load_profile(path: Path, project: str):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["project"] == project]
    return {f"{project}:{index:04d}": row for index, row in enumerate(rows)}


def load_selection(path: Path, project: str, budget: int, algorithm: str, trial: int):
    with path.open(newline="", encoding="utf-8") as handle:
        matches = [
            row
            for row in csv.DictReader(handle)
            if row["project"] == project
            and int(row["budget_pct"]) == budget
            and row["algorithm"] == algorithm
            and int(row["trial"]) == trial
        ]
    if len(matches) != 1:
        raise ValueError(f"expected one selection row, found {len(matches)}")
    return [item for item in matches[0]["selected_ids"].split("|") if item]


def export_policy(profile_path, selections_path, output_path, project, budget, algorithm, trial):
    profile = load_profile(profile_path, project)
    selected_ids = load_selection(selections_path, project, budget, algorithm, trial)
    missing = [item for item in selected_ids if item not in profile]
    if missing:
        raise ValueError(f"selection contains unknown IDs: {missing[:5]}")

    pairs = sorted(
        {
            (
                profile[item]["monitor_specification"],
                stable_location(profile[item]["source_location"]),
            )
            for item in selected_ids
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        handle.write("# specification\tstable_creation_location\n")
        for specification, location in pairs:
            handle.write(f"{specification}\t{location}\n")

    manifest = {
        "project": project,
        "budget_pct": budget,
        "algorithm": algorithm,
        "trial": trial,
        "selected_profile_rows": len(selected_ids),
        "unique_runtime_keys": len(pairs),
        "policy_file": str(output_path),
    }
    output_path.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=Path("data/valg_profiles/monitor_profile.csv"))
    parser.add_argument("--selections", type=Path, default=Path("results/offline/selections.csv"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--algorithm", required=True)
    parser.add_argument("--trial", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = export_policy(
        args.profile,
        args.selections,
        args.output,
        args.project,
        args.budget,
        args.algorithm,
        args.trial,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
