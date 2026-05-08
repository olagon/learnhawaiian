#!/usr/bin/env python3
"""
validate_against_wehewehe.py

Validates entries in data.js against wehewehe.org by fetching the search
page for each Hawaiian word and comparing definitions.

Outputs a CSV report with five verdict categories so you can triage.

Usage:
    cd /Library/WebServer/Documents/learnhawaiian
    python3 -m venv .venv && source .venv/bin/activate     # if needed
    pip install requests beautifulsoup4
    python3 scripts/validate_against_wehewehe.py

Be polite. Run this once for validation, not on a schedule.
Wehewehe.org is run by Ulukau, a community nonprofit. If you find this
useful, consider donating at https://ulukau.org/donate.html
"""

import csv
import json
import re
import sys
import time
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Run:\n  pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)

# -------- Configuration --------

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data.js"
OUTPUT_PATH = ROOT / "validation_report.csv"

# Wehewehe is built on Greenstone. The real search endpoint is /gsdl2.85/cgi-bin/hdict
# with a fixed soup of arguments and `q=WORD` substituted per query. This was found by
# inspecting the network tab on a real search.
SEARCH_URL = "https://wehewehe.org/gsdl2.85/cgi-bin/hdict"
# These params filter to Pukui-Elbert + Māmaka Kaiao dictionaries. Don't change unless
# you want a different combination.
SEARCH_PARAMS = {
    "a": "q",
    "r": "1",
    "hs": "1",
    "m": "-1",
    "o": "-1",
    "qto": "4",
    "e": "p-11000-00---off-0hdict--00-1----0-10-0---0---0direct-10-ED--4--textpukuielbert%2ctextmamaka-----0-1l--11-haw-Zz-1---Zz-1-home---00-3-1-00-0--4----0-0-11-00-0utfZz-8-00",
    "fqv": "textpukuielbert%2ctextmamaka",
    "af": "1",
    "fqf": "ED",
    # 'q' is added per request below
}

DELAY_SECONDS = 2.0           # Be polite. 2-3 seconds between requests.
TIMEOUT_SECONDS = 15
MAX_RETRIES = 2
USER_AGENT = "olelodaily-validation/1.0 (one-time vocabulary validation)"

# Skip these types — they aren't single-word lookups
SKIP_TYPES = {"Phrase", "ʻŌlelo Noʻeau", "Idiom", "Slang"}

# Pattern for Pukui-Elbert part-of-speech tags. If a wehewehe response is missing
# all of these, the parser likely got only the headword without the definition.
import re as _re_pos
POS_PATTERN = _re_pos.compile(
    r'\b(num|nvi|nvt|nvs|vt|vs|vi|n|adj|adv|prep|conj|interj|art|cf|caus|pas|abbr|loc|red|spec)\.\s',
    _re_pos.IGNORECASE
)


def should_skip_compound(entry):
    """Predictable compounds aren't in Pukui-Elbert as standalone entries.
    Skip them up front so we don't waste lookups or fill the report with noise.
    """
    haw = entry.get("Hawaiian", "").strip()
    typ = entry.get("Type", "")
    # Multi-word compounds: Pukui-Elbert lists roots, not compound forms
    if " " in haw:
        return True
    # Compound numbers built with the kūmā connector (ʻUmikūmākahi, Iwakāluakūmākahi, etc.)
    if typ == "Helu (Number)":
        low = haw.lower()
        if "kūmā" in low or "kumama" in low:
            return True
    return False

# How many entries to process. Set to None for all 2,710. Useful to start small.
LIMIT = None

# -------- Helpers --------

STOP = set("""a an the of in on at to for from with by as about and or but if than then so
is are was were be been being am have has had do does did will would could should may might
must shall can cant i you he she it we they me him her us them my your his its our their
this that these those not no""".split())


def normalize(s):
    """Lowercase, strip diacritics and ʻokina, drop punctuation."""
    s = s.lower()
    for ch in "ʻ'`’ʼ‘‛":
        s = s.replace(ch, "")
    s = re.sub(r"[̀-ͯ]", "", _strip_combining(s))
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_combining(s):
    import unicodedata
    return unicodedata.normalize("NFD", s)


def content_words(s):
    return [w for w in normalize(s).split() if w and w not in STOP and len(w) > 2]


def load_data():
    raw = DATA_PATH.read_text(encoding="utf-8")
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    return json.loads(m.group(0))


def fetch_definition(session, hawaiian):
    """Fetch the wehewehe.org page for a Hawaiian word and return text content.
    Returns (status, definition_text). status is 'ok', 'not_found', or 'error'.
    """
    params = dict(SEARCH_PARAMS)
    params["q"] = hawaiian
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = session.get(SEARCH_URL, params=params, timeout=TIMEOUT_SECONDS)
            if r.status_code == 200:
                return parse_definition_html(r.text)
            last_err = f"http_{r.status_code}"
        except Exception as e:
            last_err = str(e).split("\n")[0][:100]
        time.sleep(1.5)
    return ("error", last_err or "fetch_failed")


def parse_definition_html(html):
    """Extract the definition text from a wehewehe.org Greenstone response.
    Greenstone wraps each result in a <table> with class 'tableHits' or similar,
    and Pukui-Elbert entries appear in <p> blocks within result divs.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Strip site chrome so we don't end up with the same nav text every time
    for tag in soup(["script", "style", "nav", "header", "footer", "aside",
                     "form", "select", "option", "button"]):
        tag.decompose()

    # Look for explicit "no entries" first
    body_text = soup.get_text(" ", strip=True).lower()
    if any(p in body_text for p in [
        "no entries found", "no results", "nothing matched", "no documents matched",
        "your query produced no", "0 documents", "matching documents 0",
    ]):
        return ("not_found", "")

    # Greenstone result rows. Try multiple selectors that have appeared
    # across different Greenstone deployments.
    candidates = []
    for sel in [
        "table.tableHits tr",          # Greenstone classic results
        "table[class*=Hits] tr",
        "div.documenttext",
        "div.docDisplay",
        "p.dictionary-entry",
        "div.entry",
        "div.definition",
        "td.resultline",
    ]:
        for el in soup.select(sel):
            text = el.get_text(" ", strip=True)
            # Filter out boilerplate/short rows
            if text and len(text) > 25 and not is_boilerplate(text):
                candidates.append(text)

    # Fallback: grab any <p> that's substantial and not boilerplate
    if not candidates:
        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text and len(text) > 40 and not is_boilerplate(text):
                candidates.append(text)

    # Last resort: any <td> that looks like a result
    if not candidates:
        for td in soup.find_all("td"):
            text = td.get_text(" ", strip=True)
            if text and 40 < len(text) < 1500 and not is_boilerplate(text):
                candidates.append(text)

    if not candidates:
        return ("not_found", "")

    # De-duplicate, keep order
    seen = set()
    unique = []
    for c in candidates:
        key = c[:120]
        if key not in seen:
            seen.add(key)
            unique.append(c)

    full = " | ".join(unique[:5])  # cap at 5 result blocks
    return ("ok", full[:1500])


# Site chrome we don't want to confuse with actual definitions
BOILERPLATE_PATTERNS = [
    "hawaiian dictionaries", "skip to main content", "explore ulukau",
    "look it up", "customize search", "dictionary selection",
    "diacritic and glottal stop sensitivity", "modern spelling",
    "traditional spelling", "exact word match", "look up any word",
    "all dictionaries on this site", "about us", "our partners",
    "terms of use", "privacy", "contact us", "copyrights",
    "andrews", "emerson", "hitchcock", "parker", "judd",
    "place names of hawai", "hawaiian legal land",
    "biblical words", "combined hawaiian dictionary",
]
def is_boilerplate(text):
    t = text.lower()
    hits = sum(1 for p in BOILERPLATE_PATTERNS if p in t)
    return hits >= 3   # If 3+ boilerplate phrases appear, it's the chrome


def compute_verdict(our_english, wehewehe_text):
    """Decide how the entry compares. Returns one of:
    match | partial | no_overlap | parser_short | not_in_dict
    """
    if not wehewehe_text:
        return "not_in_dict"
    # Check for Pukui-Elbert part-of-speech tags. Without any, the parser
    # almost certainly captured only the headword and dictionary tag.
    if not POS_PATTERN.search(wehewehe_text):
        return "parser_short"
    our_tokens = set(content_words(our_english))
    wehe_tokens = set(content_words(wehewehe_text))
    if not our_tokens:
        return "no_overlap"
    overlap = our_tokens & wehe_tokens
    if len(overlap) == len(our_tokens):
        return "match"
    if overlap:
        return "partial"
    return "no_overlap"


# -------- Main --------

def main():
    data = load_data()
    print(f"Loaded {len(data)} entries from data.js")

    raw_entries = [d for d in data if d.get("Type") not in SKIP_TYPES]
    skipped_compound = [d for d in raw_entries if should_skip_compound(d)]
    entries = [d for d in raw_entries if not should_skip_compound(d)]
    if LIMIT:
        entries = entries[:LIMIT]
    print(f"Total non-phrase entries: {len(raw_entries)}")
    print(f"Auto-skipping predictable compounds: {len(skipped_compound)}")
    print(f"Will validate via wehewehe: {len(entries)}")
    print(f"Estimated time: {len(entries) * DELAY_SECONDS / 60:.0f} minutes at {DELAY_SECONDS}s/request")
    print(f"Output: {OUTPUT_PATH}")
    print()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Hawaiian", "Type", "Tier", "Our_English", "Wehewehe_Text", "Verdict"])

        # Write skipped compounds first so they appear in the report (no fetch needed)
        for d in skipped_compound:
            w.writerow([
                d["ID"], d["Hawaiian"], d.get("Type", ""), d.get("Tier", ""),
                d["English"], "", "compound_skipped",
            ])
        f.flush()

        for i, d in enumerate(entries, 1):
            haw = d["Hawaiian"]
            status, text = fetch_definition(session, haw)
            if status == "error":
                verdict = "error"
                wehe_text = text
            elif status == "not_found":
                verdict = "not_in_dict"
                wehe_text = ""
            else:
                verdict = compute_verdict(d["English"], text)
                wehe_text = text

            w.writerow([
                d["ID"], haw, d.get("Type", ""), d.get("Tier", ""),
                d["English"], wehe_text, verdict,
            ])
            f.flush()

            if i % 25 == 0 or i == len(entries):
                print(f"  [{i}/{len(entries)}] {haw}: {verdict}")

            time.sleep(DELAY_SECONDS)

    # Summary
    print("\nDone. Run a quick summary:\n")
    print(f"  awk -F',' 'NR>1{{print $7}}' {OUTPUT_PATH} | sort | uniq -c | sort -rn")
    print()
    print("Then open the CSV in Excel or Numbers, sort by Verdict, and review:")
    print("  - 'no_overlap' first  (English doesn't match wehewehe at all)")
    print("  - 'not_in_dict' next  (word not found — likely compound or modern)")
    print("  - 'partial' as time allows")
    print("  - 'match' is fine, no review needed")


if __name__ == "__main__":
    main()
