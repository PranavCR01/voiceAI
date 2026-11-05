"""Build the keyterm boost list from openFDA (public domain), ranked by US product listings.

    uv run python data/lexicons/fetch_openfda_generics.py --fetch      # refresh the snapshot
    uv run python data/lexicons/fetch_openfda_generics.py > data/lexicons/openfda_rx_generics.txt

`--fetch` downloads openFDA's NDC directory counts of prescription products per generic name and
saves them to SNAPSHOT (committed, so the list rebuilds offline and a test pins it). Without it,
the list is built from the snapshot. Rules, all deterministic:

- Prescription products only (`product_type:"HUMAN PRESCRIPTION DRUG"`).
- Combination products dropped (" and ", ",", "/", " with ").
- Salt and form words stripped ("Atorvastatin Calcium" -> "atorvastatin"), then names merged
  case-insensitively and their counts summed.
- Non-drugs and things a caller doesn't name as a medicine dropped (NOT_MEDICATIONS).
- Ranked by summed count (ties alphabetical). Each drug contributes its US name and, where the UK
  name differs, the UK name right after it (US_TO_UK), until MAX_TERMS terms.

What the rank measures: how many US labeler/package listings a generic has, i.e. how widely it is
manufactured and repackaged in the US. That correlates with use but is not prescribing volume, and
it is US-only. NHSBSA and OpenPrescribing (UK prescribing volumes) were unreachable when this was
built. See docs/DECISIONS.md 2026-11-05.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

URL = (
    "https://api.fda.gov/drug/ndc.json"
    '?search=product_type:"HUMAN+PRESCRIPTION+DRUG"&count=generic_name.exact&limit=1000'
)
SNAPSHOT = Path(__file__).with_name("openfda_ndc_rx_counts.json")
# ElevenLabs bills every request for at least 20 s once a request carries more than 100 keyterms.
MAX_TERMS = 100

COMBINATION = re.compile(r" and |,|/| with ")
SALT_WORDS = frozenset(
    """
    hydrochloride hcl dihydrochloride hydrobromide sodium potassium calcium magnesium besylate
    besilate mesylate maleate succinate tartrate bitartrate citrate fumarate sulfate sulphate
    phosphate acetate bromide chloride carbonate monohydrate dihydrate trihydrate hyclate hydrate
    propionate dipropionate furoate valerate xinafoate acetonide tromethamine disodium dimesylate
    extended release er xr sr dr delayed oral tablets capsules injection usp
    """.split()
)
# Not medicines, or not something a caller names as one.
NOT_MEDICATIONS = frozenset(
    {"oxygen", "nitrogen", "air", "water", "fluoride", "dextrose", "glucose", "saline", "helium"}
    | {"nitrous oxide", "carbon dioxide", "lidocaine"}
)
# USAN -> UK (BAN/rINN) where they differ. Hand-written, applied mechanically.
US_TO_UK = {
    "acetaminophen": "paracetamol",
    "albuterol": "salbutamol",
    "cephalexin": "cefalexin",
    "cefuroxime axetil": "cefuroxime",
    "glyburide": "glibenclamide",
    "epinephrine": "adrenaline",
    "norepinephrine": "noradrenaline",
    "cyclosporine": "ciclosporin",
    "rifampin": "rifampicin",
    "meperidine": "pethidine",
    "norethindrone": "norethisterone",
    "dicyclomine": "dicycloverine",
    "levothyroxine": "thyroxine",  # UK patients usually say "thyroxine"
    "valproic acid": "sodium valproate",
    "divalproex": "sodium valproate",
    "sulfasalazine": "sulphasalazine",
    "trihexyphenidyl": "benzhexol",
    "amphetamine": "amfetamine",
    "dextroamphetamine": "dexamfetamine",
    "methimazole": "thiamazole",
    "estradiol": "oestradiol",
}


def base_name(term: str) -> str | None:
    name = term.strip().lower()
    if COMBINATION.search(name):
        return None
    words = [w for w in re.split(r"\s+", name) if w and w not in SALT_WORDS]
    return " ".join(words) or None


def rank(results: list[dict[str, object]]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for r in results:
        name = base_name(str(r["term"]))
        if name and name not in NOT_MEDICATIONS:
            counts[name] += int(str(r["count"]))
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def terms(ranked: list[tuple[str, int]], limit: int = MAX_TERMS) -> list[str]:
    out: list[str] = []
    for name, _ in ranked:
        for term in (name, US_TO_UK.get(name)):
            if term and term not in out and len(out) < limit:
                out.append(term)
        if len(out) >= limit:
            break
    return out


def fetch() -> None:
    with urllib.request.urlopen(URL, timeout=60) as resp:
        body = json.load(resp)
    snapshot = {
        "url": URL,
        "fetched": str(datetime.now(UTC).date()),
        "last_updated": body.get("meta", {}).get("last_updated"),
        "license": "openFDA, public domain (CC0)",
        "results": body["results"],
    }
    SNAPSHOT.write_text(json.dumps(snapshot, indent=0) + "\n")


def render(snapshot: dict[str, object]) -> str:
    results = snapshot["results"]
    assert isinstance(results, list)
    ranked = rank(results)
    lines = [
        "# Keyterm BOOST list: most widely listed US prescription generics, from openFDA (CC0).",
        f"# Built by data/lexicons/fetch_openfda_generics.py from {SNAPSHOT.name}",
        f"# (fetched {snapshot['fetched']}, openFDA data updated {snapshot['last_updated']}).",
        "# Ranked by US NDC product listings (manufacturing breadth, not prescribing volume);",
        "# where the UK name differs it follows the US one. Not derived from any test set;",
        "# scoring uses medications.txt. See docs/DECISIONS.md 2026-11-05.",
        "",
        *terms(ranked),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fetch", action="store_true", help="refresh the snapshot from openFDA")
    args = parser.parse_args()
    if args.fetch:
        fetch()
        return
    sys.stdout.write(render(json.loads(SNAPSHOT.read_text())))


if __name__ == "__main__":
    main()
