#!/usr/bin/env python3
"""
resume_validation.py

Picks up where validate_against_wehewehe.py left off. Reads the existing
validation_report.csv, figures out which entries were never processed (or
errored out), and re-runs ONLY those. Appends to the existing CSV.

Usage:
    cd /Library/WebServer/Documents/learnhawaiian
    source .venv/bin/activate
    python3 scripts/resume_validation.py
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

# Reuse all the helpers and config from the main validation script
import importlib.util
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "validate_main", ROOT / "scripts" / "validate_against_wehewehe.py"
)
vmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vmod)

import requests
import csv as csvmod

DATA_PATH = ROOT / "data.js"
OUTPUT_PATH = ROOT / "validation_report.csv"

# Re-process these verdict types when found in the CSV
RETRY_VERDICTS = {"error"}  # Set to {} to never retry. Add "parser_short" to redo those too.

def main():
    if not OUTPUT_PATH.exists():
        print(f"No existing CSV at {OUTPUT_PATH}. Run validate_against_wehewehe.py first.", file=sys.stderr)
        sys.exit(1)

    # Load full vocabulary
    raw = DATA_PATH.read_text(encoding="utf-8")
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    data = json.loads(m.group(0))
    by_id = {d["ID"]: d for d in data}

    # Load existing CSV
    existing_rows = []
    processed_ids = set()
    retry_ids = set()
    with OUTPUT_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            existing_rows.append(r)
            try:
                rid = int(r["ID"])
            except ValueError:
                continue
            processed_ids.add(rid)
            if r["Verdict"] in RETRY_VERDICTS:
                retry_ids.add(rid)

    # Figure out what to process: missing entries + retry entries
    all_relevant = [
        d for d in data
        if d.get("Type") not in vmod.SKIP_TYPES and not vmod.should_skip_compound(d)
    ]
    missing = [d for d in all_relevant if d["ID"] not in processed_ids]
    retries = [by_id[i] for i in retry_ids if i in by_id]
    todo = missing + retries

    print(f"Existing CSV rows: {len(existing_rows)}")
    print(f"Missing entries: {len(missing)}")
    print(f"Entries to retry ({RETRY_VERDICTS}): {len(retries)}")
    print(f"Total to fetch: {len(todo)}")
    print(f"Estimated time: {len(todo) * vmod.DELAY_SECONDS / 60:.1f} minutes")
    print()

    if not todo:
        print("Nothing to do. CSV is complete.")
        return

    # Drop retried rows from existing list (we'll write fresh ones)
    existing_rows = [r for r in existing_rows if r.get("Verdict") not in RETRY_VERDICTS]

    session = requests.Session()
    session.headers.update({
        "User-Agent": vmod.USER_AGENT,
        "Accept-Language": "en",
    })

    # Write a fresh combined CSV
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csvmod.writer(f)
        w.writerow(["ID", "Hawaiian", "Type", "Tier", "Our_English", "Wehewehe_Text", "Verdict"])
        # Existing rows first
        for r in existing_rows:
            w.writerow([r["ID"], r["Hawaiian"], r["Type"], r["Tier"], r["Our_English"], r["Wehewehe_Text"], r["Verdict"]])
        f.flush()

        for i, d in enumerate(todo, 1):
            haw = d["Hawaiian"]
            status, text = vmod.fetch_definition(session, haw)
            if status == "error":
                verdict = "error"
                wehe_text = text
            elif status == "not_found":
                verdict = "not_in_dict"
                wehe_text = ""
            else:
                verdict = vmod.compute_verdict(d["English"], text)
                wehe_text = text

            w.writerow([
                d["ID"], haw, d.get("Type", ""), d.get("Tier", ""),
                d["English"], wehe_text, verdict,
            ])
            f.flush()

            if i % 25 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] {haw}: {verdict}")

            time.sleep(vmod.DELAY_SECONDS)

    print("\nDone. New verdict distribution:")
    from collections import Counter
    with OUTPUT_PATH.open(encoding="utf-8") as f:
        verdicts = Counter(r["Verdict"] for r in csv.DictReader(f))
    for v, c in verdicts.most_common():
        print(f"  {v}: {c}")


if __name__ == "__main__":
    main()
