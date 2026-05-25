#!/usr/bin/env python3
"""Generate ReportLatex/fig_latency.png from plans/data/latency.csv"""

from __future__ import annotations

import os
import sys

import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(REPO, "plans", "data", "latency.csv")
OUT = os.path.join(REPO, "ReportLatex", "fig_latency.png")


def main():
    if not os.path.isfile(CSV):
        print(f"Missing {CSV} — run: python3 turret/measure_results.py", file=sys.stderr)
        return 1

    trials, values = [], []
    with open(CSV, encoding="utf-8") as f:
        header = f.readline()
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) < 2 or not parts[1].strip():
                continue
            trials.append(int(parts[0]))
            values.append(float(parts[1]))

    if not values:
        print("latency.csv has no data rows — complete Faz 3 measurements first.", file=sys.stderr)
        return 1

    mean_v = sum(values) / len(values)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(trials, values, color="#4a90d9", edgecolor="#2a5f8f")
    ax.axhline(mean_v, color="#c0392b", linestyle="--", linewidth=1.5,
               label=f"mean = {mean_v:.0f} ms")
    ax.set_xlabel("Trial")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Detection to first corrective servo command")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
