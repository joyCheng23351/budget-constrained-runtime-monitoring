#!/usr/bin/env python3
"""Return peak used memory in KiB from repeated `docker stats` MemUsage lines."""

import re
import sys
from pathlib import Path


SCALE = {"B": 1 / 1024, "KiB": 1, "MiB": 1024, "GiB": 1024 * 1024}


def peak_kib(lines):
    values = []
    for line in lines:
        used = line.split("/", 1)[0].strip()
        match = re.fullmatch(r"([0-9.]+)(B|KiB|MiB|GiB)", used)
        if match:
            values.append(float(match.group(1)) * SCALE[match.group(2)])
    return round(max(values)) if values else 0


if __name__ == "__main__":
    print(peak_kib(Path(sys.argv[1]).read_text().splitlines()))
