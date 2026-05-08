#!/usr/bin/env python3
"""Write a review CSV containing only the rows that need human eyes."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "validation_report.csv"
DST = ROOT / "review.csv"

KEEP_VERDICTS = {"no_overlap", "error", "not_in_dict"}

with SRC.open(encoding="utf-8") as fin, DST.open("w", newline="", encoding="utf-8") as fout:
    reader = csv.DictReader(fin)
    writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
    writer.writeheader()
    counts = {v: 0 for v in KEEP_VERDICTS}
    total = 0
    for row in reader:
        total += 1
        if row["Verdict"] in KEEP_VERDICTS:
            writer.writerow(row)
            counts[row["Verdict"]] += 1

print(f"Total rows scanned: {total}")
for v, c in counts.items():
    print(f"  {v}: {c}")
print(f"Wrote: {DST}")
