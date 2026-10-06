"""Fetch the most common generic drug names from openFDA (public domain) as lexicon candidates.

Run on a machine that can reach api.fda.gov (the cloud dev environment cannot):

    uv run python data/lexicons/fetch_openfda_generics.py > /tmp/openfda_generics.txt

Output is one lowercased candidate per line, prefixed by a header recording the fetch date.
Review it before merging into a lexicon: openFDA's NDC data includes non-drug products
(hand sanitizer, sunscreen) and combination products, filtered here only roughly.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import UTC, datetime

URL = "https://api.fda.gov/drug/ndc.json?count=generic_name.exact&limit=1000"
# Rough filters: combination products and obvious non-drug consumer products.
SKIP_SUBSTRINGS = (" and ", ",", "/", "sanitizer", "sunscreen", "spf", "antiseptic", "wipes")
MIN_LENGTH = 5


def main() -> None:
    with urllib.request.urlopen(URL, timeout=30) as resp:
        results = json.load(resp)["results"]
    terms = sorted(
        {
            r["term"].strip().lower()
            for r in results
            if len(r["term"].strip()) >= MIN_LENGTH
            and not any(s in r["term"].lower() for s in SKIP_SUBSTRINGS)
        }
    )
    print(f"# openFDA NDC top generic names, fetched {datetime.now(UTC).date()} from {URL}")
    print("# Public domain (openFDA). Review before merging into a lexicon.")
    sys.stdout.write("\n".join(terms) + "\n")


if __name__ == "__main__":
    main()
