#!/usr/bin/env python3
"""
apply_validation_fixes.py

Applies the data.js fixes from the wehewehe.org validation review.
Run with --dry-run first to see the diff. Then re-run without to apply.

Usage:
    cd /Library/WebServer/Documents/learnhawaiian
    python3 scripts/apply_validation_fixes.py --dry-run    # preview
    python3 scripts/apply_validation_fixes.py              # apply
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data.js"
BACKUP_PATH = ROOT / "data.js.bak"

# IDs to delete entirely. Existing user progress that references these will
# silently drop them on next page load.
DELETE_IDS = {
    688,   # Mākīkī — Pukui-Elbert: "to peck; cockfight; octopus-lure stone weight" (NOT glove)
    2679,  # Mōhihi — Pukui-Elbert: "sweet potato variety; native mint" (NOT stretching)
    591,   # Samona — loanword for Salmon, not in Pukui-Elbert
    1978,  # ʻElemi — loanword for Lemon, not in Pukui-Elbert
    1979,  # Painapala — loanword for Pineapple, not in Pukui-Elbert
    1987,  # Kelimi — loanword for Cream, not in Pukui-Elbert
    1988,  # Pata — loanword for Butter, not in Pukui-Elbert
}

# Update the English meaning for these IDs
ENGLISH_UPDATES = {
    1086: "Firm / Thick / Jellied",       # was "Brown / Dark"
    1899: "Sea urchin (white-spined, Tripneustes gratilla)",  # was "Pupil of the eye"
}

# Update the Hawaiian form (split single-word into space-separated compound)
HAWAIIAN_UPDATES = {
    533:  ("Puka ihu",        "Pukaihu"),
    432:  ("Makua kāne",      "Makuakāne"),
    547:  ("Kupuna kāne",     "Kupunakāne"),
    548:  ("Kupuna wahine",   "Kupunawahine"),
    998:  ("Heʻe nalu",       "Heʻenalu"),
    999:  ("Heʻe hōlua",      "Heʻeholua"),
    1055: ("Make wai",        "Makewai"),
    779:  ("Hale kai",        "Halekai"),
    822:  ("Mōʻī wahine",     "Mōʻīwahine"),
    1247: ("Ae kai",          "Aekai"),
    1411: ("Hoa aloha",       "Hoaaloha"),
    1415: ("Hoa noho",        "Hoanoho"),
    1967: ("ʻŌpae ʻula",      "ʻOpaeʻula"),
    2243: ("Luna kānāwai",    "Lunakānāwai"),
    2244: ("Luna kaiapuni",   "Lunakaiapuni"),
}


def main():
    dry_run = "--dry-run" in sys.argv

    raw = DATA_PATH.read_text(encoding="utf-8")
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    data = json.loads(m.group(0))
    by_id = {d["ID"]: d for d in data}

    print(f"Loaded {len(data)} entries\n")

    # Sanity check: every target ID must exist
    missing = []
    for ids in [DELETE_IDS, ENGLISH_UPDATES.keys(), HAWAIIAN_UPDATES.keys()]:
        for i in ids:
            if i not in by_id:
                missing.append(i)
    if missing:
        print(f"ERROR: these IDs are not in data.js: {missing}", file=sys.stderr)
        sys.exit(1)

    # Show planned changes
    print("=" * 78)
    print("DELETIONS")
    print("=" * 78)
    for i in sorted(DELETE_IDS):
        e = by_id[i]
        print(f"  [{i}] {e['Hawaiian']} ({e['Type']}) = {e['English']}")

    print()
    print("=" * 78)
    print("ENGLISH UPDATES")
    print("=" * 78)
    for i, new_eng in sorted(ENGLISH_UPDATES.items()):
        e = by_id[i]
        print(f"  [{i}] {e['Hawaiian']}")
        print(f"       was: {e['English']}")
        print(f"       now: {new_eng}")

    print()
    print("=" * 78)
    print("HAWAIIAN UPDATES (compound forms split with spaces)")
    print("=" * 78)
    for i, (new_haw, expected_old) in sorted(HAWAIIAN_UPDATES.items()):
        e = by_id[i]
        if e["Hawaiian"] != expected_old:
            print(f"  [{i}] WARNING: expected '{expected_old}' but found '{e['Hawaiian']}', skipping")
            continue
        print(f"  [{i}] '{e['Hawaiian']}' → '{new_haw}'   ({e['English']})")

    print()
    print("=" * 78)
    print(f"Summary: -{len(DELETE_IDS)} deletions, ~{len(ENGLISH_UPDATES)} English updates, ~{len(HAWAIIAN_UPDATES)} Hawaiian updates")
    print(f"After: {len(data) - len(DELETE_IDS)} entries")
    print("=" * 78)

    if dry_run:
        print("\nDry run. No changes written. Re-run without --dry-run to apply.")
        return

    # Apply changes
    new_data = []
    for d in data:
        if d["ID"] in DELETE_IDS:
            continue
        if d["ID"] in ENGLISH_UPDATES:
            d["English"] = ENGLISH_UPDATES[d["ID"]]
        if d["ID"] in HAWAIIAN_UPDATES:
            new_haw, expected_old = HAWAIIAN_UPDATES[d["ID"]]
            if d["Hawaiian"] == expected_old:
                d["Hawaiian"] = new_haw
        new_data.append(d)

    # Backup original
    BACKUP_PATH.write_text(raw, encoding="utf-8")
    print(f"\nBackup written: {BACKUP_PATH}")

    # Re-emit data.js with same formatting style (1-space indent, ordered keys)
    def fmt(d):
        keys = ["ID", "Hawaiian", "English", "Type"]
        if "Tier" in d:
            keys.append("Tier")
        lines = []
        for k in keys:
            v = d[k]
            if isinstance(v, str):
                lines.append(f'   "{k}": {json.dumps(v, ensure_ascii=False)}')
            else:
                lines.append(f'   "{k}": {v}')
        return " {\n" + ",\n".join(lines) + "\n }"

    body = "[\n" + ",\n".join(fmt(d) for d in new_data) + "\n]"
    DATA_PATH.write_text(f"const vocabularyData = {body}\n", encoding="utf-8")
    print(f"Wrote {len(new_data)} entries to {DATA_PATH}")


if __name__ == "__main__":
    main()
