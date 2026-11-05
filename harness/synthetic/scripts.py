"""Seeded synthetic caller scripts with controlled entities (#17).

    uv run python -m harness.synthetic.scripts --profile configs/profiles/healthcare_intake.yaml \\
        --out data/manifests/synthetic_healthcare_intake.jsonl

Profile-driven: carrier sentences come from the profile's `synthetic_templates` file, and each
`{placeholder}` is either an entity category from the profile or a free slot from that file.
Entities are rendered by *kind*, never by domain: a lexicon category draws a lexicon term, a
builtin draws a spoken date/dosage/phone/number/duration, and a regex category is supported
when its pattern is a fixed-length digit string (spoken digit by digit).

Everything is written in its *spoken* form ("five hundred milligrams", "oh seven seven double
oh ...", "the third of March nineteen eighty"), and the reference text is exactly what the TTS
reads, so the normalizer, not this script, decides equivalence with a provider's output.

Outputs, both sorted by utt_id so the same seed gives identical bytes:
- `<out>.jsonl`: a manifest of `synthetic: true` utterances. `speaker_id` is the TTS voice and
  `audio_path` is where `synthesize.py` (owner's machine) will write the 16 kHz WAV.
- `<out>.entities.jsonl`: the entities inserted in each utterance (category, spoken text, the
  normalized text the tagger should find), so misses can be listed.

Phone numbers come from ranges reserved for fiction (UK Ofcom 07700 900xxx and 020 7946 0xxx;
US 555-01xx), so no real number is ever spoken.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from harness.datasets.manifest import Utterance, write_manifest
from harness.metrics.entities import EntityTagger
from harness.metrics.normalize import date_order_for, normalize
from recommender.profile import Builtin, EntityCategory, EntityKind, Profile, load_profile
from recommender.profile import read_lexicon as _read_lexicon

DEFAULT_TARGET = 300  # per category; the issue asks for >= 250 after tagging
DISFLUENCY_RATE = 0.3
SAMPLE_RATE = 16000
LICENSE = "CC0-1.0"  # the script text; synthesized audio adds the TTS vendor's terms
_PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)\}")
_FIXED_DIGITS = re.compile(r"^(?:\\b)?\\d\{(\d+)\}(?:\\b)?$")
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

# --- spoken numbers --------------------------------------------------------------------------

_ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen"
).split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
_ORDINAL_WORDS = {
    "one": "first",
    "two": "second",
    "three": "third",
    "five": "fifth",
    "eight": "eighth",
    "nine": "ninth",
    "twelve": "twelfth",
}
_MONTHS = (
    "January February March April May June July August September October November December"
).split()
_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def words(n: int) -> str:
    """Cardinal number in words, 0..999999 ("one hundred and twelve" style kept out: US-neutral
    "one hundred twelve")."""
    if not 0 <= n < 1_000_000:
        raise ValueError(f"out of range: {n}")
    if n < 20:
        return _ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _TENS[tens] + (f" {_ONES[ones]}" if ones else "")
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        return f"{_ONES[hundreds]} hundred" + (f" {words(rest)}" if rest else "")
    thousands, rest = divmod(n, 1000)
    return f"{words(thousands)} thousand" + (f" {words(rest)}" if rest else "")


def ordinal_words(n: int) -> str:
    """1 -> "first", 21 -> "twenty first", 30 -> "thirtieth"."""
    cardinal = words(n).split()
    last = cardinal[-1]
    if last in _ORDINAL_WORDS:
        cardinal[-1] = _ORDINAL_WORDS[last]
    elif last.endswith("y"):
        cardinal[-1] = last[:-1] + "ieth"
    else:
        cardinal[-1] = last + "th"
    return " ".join(cardinal)


def year_words(year: int) -> str:
    """1982 -> "nineteen eighty two", 2005 -> "two thousand and five", 2000 -> "two thousand"."""
    if 2000 <= year < 2010:
        return "two thousand" + (f" and {_ONES[year - 2000]}" if year > 2000 else "")
    century, rest = divmod(year, 100)
    if rest == 0:
        return f"{words(century)} hundred"
    if rest < 10:
        return f"{words(century)} oh {_ONES[rest]}"
    return f"{words(century)} {words(rest)}"


def spoken_digits(digits: str, rng: random.Random, *, groups: Sequence[int] = ()) -> str:
    """Digit by digit, with "oh" or "zero" for 0 and sometimes "double" for a repeated pair."""
    zero = rng.choice(["oh", "zero"])
    use_double = rng.random() < 0.5
    out: list[str] = []
    i = 0
    while i < len(digits):
        d = digits[i]
        word = zero if d == "0" else _ONES[int(d)]
        if use_double and i + 1 < len(digits) and digits[i + 1] == d and (i + 1) not in groups:
            out.append(f"double {word}")
            i += 2
        else:
            out.append(word)
            i += 1
        if i in groups:
            out[-1] += ","
    return " ".join(out)


# --- entity renderers (by kind, never by domain) -----------------------------------------------


@dataclass(frozen=True)
class Rendered:
    category: str
    spoken: str  # exactly what the TTS reads
    expected: str  # normalized entity text the tagger should find


def _expected(spoken: str, language: str | None) -> str:
    text = normalize(spoken, date_order=date_order_for(language))
    return text.removeprefix("the ")


def _date(rng: random.Random, years: tuple[int, int], with_year: float) -> str:
    month = rng.randrange(12)
    day = rng.randint(1, _DAYS_IN_MONTH[month])
    m = _MONTHS[month]
    if rng.random() >= with_year:
        return rng.choice([f"the {ordinal_words(day)} of {m}", f"{m} {ordinal_words(day)}"])
    y = year_words(rng.randint(*years))
    return rng.choice(
        [
            f"the {ordinal_words(day)} of {m} {y}",
            f"{m} {ordinal_words(day)}, {y}",
            f"{ordinal_words(day)} {m} {y}",
        ]
    )


_DOSES: tuple[tuple[str, tuple[float, ...]], ...] = (
    ("milligrams", (5, 10, 20, 25, 40, 50, 75, 100, 150, 200, 250, 400, 500, 1000, 2.5)),
    ("micrograms", (25, 50, 75, 100, 125)),
    ("milliliters", (5, 10, 15, 20)),
    ("units", (4, 6, 8, 10, 12, 20, 30)),
    ("puffs", (1, 2, 4)),
    ("tablets", (1, 2)),
    ("capsules", (1, 2)),
    ("drops", (1, 2, 3)),
)


def _number_words(x: float) -> str:
    if x == int(x):
        return words(int(x))
    whole, frac = str(x).split(".")
    return f"{words(int(whole))} point " + " ".join(_ONES[int(d)] for d in frac)


def _dosage(rng: random.Random) -> str:
    unit, amounts = rng.choice(_DOSES)
    amount = rng.choice(amounts)
    if amount == 1:
        unit = unit.removesuffix("s")
    return f"{_number_words(amount)} {unit}"


def _phone(rng: random.Random, language: str | None) -> str:
    groups: tuple[int, ...]
    if language and language.upper().endswith("-GB"):
        if rng.random() < 0.5:
            digits, groups = f"07700900{rng.randrange(1000):03d}", (5,)
        else:
            digits, groups = f"0207946{rng.randrange(1000):04d}", (3, 7)
    else:
        area = rng.choice(["202", "312", "415", "512", "617", "713"])
        digits, groups = f"{area}55501{rng.randrange(100):02d}", (3, 6)
    return spoken_digits(digits, rng, groups=groups)


def _amount(rng: random.Random, language: str | None) -> str:
    currency = (
        ("pounds", "pence")
        if language and language.upper().endswith("-GB")
        else (
            "dollars",
            "cents",
        )
    )
    whole = rng.randint(2, 480)
    if rng.random() < 0.5:
        return f"{words(whole)} {currency[0]}"
    return f"{words(whole)} {currency[0]} and {words(rng.randint(1, 99))} {currency[1]}"


def _duration(rng: random.Random) -> str:
    n = rng.randint(2, 12)
    return f"{words(n)} {rng.choice(['days', 'weeks', 'months'])}"


class Renderer:
    """Spoken entities for one profile category."""

    def __init__(self, category: EntityCategory, profile: Profile, language: str | None) -> None:
        self.category = category
        self.language = language
        self.terms: list[str] = []
        self.digits = 0
        if category.kind is EntityKind.LEXICON:
            assert category.lexicon_path is not None
            self.terms = sorted(set(_read_lexicon(profile.resolve_path(category.lexicon_path))))
        elif category.kind is EntityKind.REGEX:
            m = _FIXED_DIGITS.match(category.pattern or "")
            if m is None:
                raise ValueError(
                    f"{category.name}: no generator for regex {category.pattern!r} "
                    "(only fixed-length digit patterns like \\b\\d{10}\\b are supported)"
                )
            self.digits = int(m.group(1))

    def render(self, rng: random.Random) -> Rendered:
        c = self.category
        if c.kind is EntityKind.LEXICON:
            spoken = rng.choice(self.terms)
        elif c.kind is EntityKind.REGEX:
            first = str(rng.randint(1, 9))
            rest = "".join(str(rng.randrange(10)) for _ in range(self.digits - 1))
            spoken = spoken_digits(first + rest, rng)
        elif c.builtin is Builtin.DATE:
            spoken = _date(rng, (1935, 2008), with_year=0.85)
        elif c.builtin is Builtin.DOSAGE:
            spoken = _dosage(rng)
        elif c.builtin is Builtin.PHONE:
            spoken = _phone(rng, self.language)
        elif c.builtin is Builtin.NUMBER:
            spoken = _amount(rng, self.language)
        elif c.builtin is Builtin.DURATION:
            spoken = _duration(rng)
        else:  # pragma: no cover - every Builtin is handled above
            raise ValueError(f"{c.name}: unsupported builtin {c.builtin}")
        return Rendered(c.name, spoken, _expected(spoken, self.language))


# --- templates and disfluencies ----------------------------------------------------------


class TemplateSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    templates: list[str] = Field(min_length=1)
    slots: dict[str, list[str]] = Field(default_factory=dict)


def load_templates(profile: Profile) -> TemplateSet:
    if profile.synthetic_templates is None:
        raise ValueError("the profile has no `synthetic_templates` file")
    data = yaml.safe_load(profile.resolve_path(profile.synthetic_templates).read_text("utf-8"))
    tset = TemplateSet.model_validate(data)
    names = {e.name for e in profile.entities} | set(tset.slots)
    for t in tset.templates:
        unknown = set(_PLACEHOLDER.findall(t)) - names
        if unknown:
            raise ValueError(f"template {t!r}: unknown placeholders {sorted(unknown)}")
    empty = sorted(k for k, v in tset.slots.items() if not v)
    if empty:
        raise ValueError(f"empty slots: {empty}")
    return tset


_FILLERS = ("um", "uh", "er")


def _disfluent(
    pieces: list[tuple[str, bool]], rng: random.Random
) -> tuple[list[tuple[str, bool]], str]:
    """Add one disfluency outside entity pieces: a leading filler, a mid-sentence filler, or a
    restart repeating the first words ("I take, I take ...")."""
    kind = rng.choice(["lead", "mid", "restart"])
    first_text = pieces[0][0].split() if pieces and not pieces[0][1] else []
    if kind == "restart" and len(first_text) >= 2:
        n = min(len(first_text), rng.choice([1, 2]))
        return [(" ".join(first_text[:n]) + ",", False), *pieces], "restart"
    if kind == "mid":
        # A filler goes before a literal piece that starts a word, never before ", I owe".
        literal = [
            i
            for i, (text, is_entity) in enumerate(pieces)
            if not is_entity and text and text[0].isalnum()
        ]
        if literal and literal[-1] > 0:
            i = rng.choice([j for j in literal if j > 0] or literal)
            return [*pieces[:i], (f"{rng.choice(_FILLERS)},", False), *pieces[i:]], "mid"
    return [(f"{rng.choice(_FILLERS).capitalize()},", False), *pieces], "lead"


# --- generation --------------------------------------------------------------------------


@dataclass(frozen=True)
class Voice:
    vendor: str
    voice_id: str
    language: str

    @classmethod
    def parse(cls, spec: str) -> Voice:
        try:
            vendor, voice_id, language = spec.split(":")
        except ValueError as e:
            raise ValueError(f"voice {spec!r}: expected vendor:voice_id:language") from e
        return cls(vendor, voice_id, language)

    @property
    def label(self) -> str:
        return _SAFE.sub("-", f"{self.vendor}.{self.voice_id}")


def default_voices(language: str) -> list[str]:
    """2 vendors x 5 voices. The report resamples whole speakers (= voices) and calls no winner
    under 10 clusters, so the issue's minimum of 2 x 2 voices would leave synthetic tables
    unrankable."""
    return [f"tts_{v}:voice{n}:{language}" for v in "ab" for n in range(1, 6)]


@dataclass
class Script:
    utterances: list[Utterance]
    entities: dict[str, list[Rendered]]  # utt_id -> inserted entities
    disfluency: dict[str, str | None]  # utt_id -> "lead" / "mid" / "restart" / None
    counts: Counter[str] = field(default_factory=Counter)


def generate(
    profile: Profile,
    *,
    name: str,
    voices: Sequence[Voice],
    seed: int = 0,
    target: int = DEFAULT_TARGET,
    disfluency_rate: float = DISFLUENCY_RATE,
) -> Script:
    """Utterances until every renderable category has >= `target` inserted entities.

    Voices are assigned round robin, so each script line is spoken once (no duplicated text
    across voices). Templates are chosen among those containing the least-filled category.
    """
    if not voices:
        raise ValueError("need at least one voice")
    tset = load_templates(profile)
    rng = random.Random(seed)
    renderers = {
        e.name: Renderer(e, profile, voices[0].language)
        for e in profile.entities
        if any(f"{{{e.name}}}" in t for t in tset.templates)
    }
    renderers_by_lang: dict[tuple[str, str], Renderer] = {}
    if not renderers:
        raise ValueError("no template uses any entity category")
    counts: Counter[str] = Counter({c: 0 for c in renderers})
    utts: list[Utterance] = []
    entities: dict[str, list[Rendered]] = {}
    disfluency: dict[str, str | None] = {}
    i = 0
    while min(counts.values()) < target:
        need = min(counts, key=lambda c: (counts[c], c))
        candidates = [t for t in tset.templates if f"{{{need}}}" in t]
        template = rng.choice(candidates)
        voice = voices[i % len(voices)]
        pieces: list[tuple[str, bool]] = []
        inserted: list[Rendered] = []
        pos = 0
        for m in _PLACEHOLDER.finditer(template):
            pieces.append((template[pos : m.start()], False))
            key = m.group(1)
            if key in renderers:
                r = renderers_by_lang.setdefault(
                    (key, voice.language),
                    Renderer(renderers[key].category, profile, voice.language),
                ).render(rng)
                inserted.append(r)
                counts[key] += 1
                pieces.append((r.spoken, True))
            else:
                pieces.append((rng.choice(tset.slots[key]), False))
            pos = m.end()
        pieces.append((template[pos:], False))
        pieces = [(t.strip(), e) for t, e in pieces if t.strip()]
        kind: str | None = None
        if rng.random() < disfluency_rate:
            pieces, kind = _disfluent(pieces, rng)
        text = re.sub(r",(\s*,)+", ",", " ".join(t for t, _ in pieces).replace(" ,", ","))
        text = text[0].upper() + text[1:] + ("" if text.endswith((".", "?")) else ".")
        utt_id = f"synth:{name}:{voice.label}:{i:04d}"
        utts.append(
            Utterance(
                utt_id=utt_id,
                dataset=f"synthetic_{name}",
                subset=_SAFE.sub("-", voice.vendor),
                speaker_id=voice.label,
                audio_path=f"synthetic/{name}/{voice.label}/{i:04d}.wav",
                ref_text=text,
                sample_rate=SAMPLE_RATE,
                license=LICENSE,
                synthetic=True,
                language=voice.language,
            )
        )
        entities[utt_id] = inserted
        disfluency[utt_id] = kind
        i += 1
    return Script(utts, entities, disfluency, counts)


# --- verification ------------------------------------------------------------------------


@dataclass(frozen=True)
class Miss:
    utt_id: str
    category: str
    expected: str
    tagged: tuple[tuple[str, str], ...]  # what the tagger found instead: (category, text)


def check(script: Script, profile: Profile) -> tuple[Counter[str], list[Miss]]:
    """Run the entity tagger over the references; count found entities and list misses."""
    taggers: dict[str, EntityTagger] = {}
    found: Counter[str] = Counter()
    misses: list[Miss] = []
    for u in script.utterances:
        order = date_order_for(u.language)
        tagger = taggers.setdefault(
            order,
            EntityTagger.from_entities(profile.entities, profile.resolve_path, date_order=order),
        )
        spans = tagger.tag(normalize(u.ref_text, date_order=order))
        available = [(s.category, s.text) for s in spans]
        for r in script.entities[u.utt_id]:
            if (r.category, r.expected) in available:
                available.remove((r.category, r.expected))
                found[r.category] += 1
            else:
                misses.append(
                    Miss(
                        u.utt_id, r.category, r.expected, tuple((s.category, s.text) for s in spans)
                    )
                )
    return found, misses


def write_script(out: Path, script: Script) -> Path:
    write_manifest(out, script.utterances)
    side = out.with_name(out.name.removesuffix(".jsonl") + ".entities.jsonl")
    lines = [
        json.dumps(
            {
                "utt_id": utt_id,
                "disfluency": script.disfluency[utt_id],
                "entities": [
                    {"category": r.category, "spoken": r.spoken, "expected": r.expected}
                    for r in script.entities[utt_id]
                ],
            },
            ensure_ascii=False,
        )
        for utt_id in sorted(script.entities)
    ]
    side.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    return side


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Seeded synthetic caller scripts (#17)")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--name", help="dataset name; default: the profile file's stem")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET)
    parser.add_argument(
        "--voice",
        action="append",
        dest="voices",
        help="vendor:voice_id:language, repeatable (default: 2 vendors x 5 placeholder voices "
        "in the profile's first language; the owner regenerates with real voice ids)",
    )
    args = parser.parse_args(argv)
    profile = load_profile(args.profile)
    name = args.name or args.profile.stem
    lang = profile.use_case.languages[0] if profile.use_case.languages else "en-US"
    specs = args.voices or default_voices(lang)
    script = generate(
        profile,
        name=name,
        voices=[Voice.parse(s) for s in specs],
        seed=args.seed,
        target=args.target,
    )
    found, misses = check(script, profile)
    side = write_script(args.out, script)
    total = sum(script.counts.values())
    print(
        json.dumps(
            {
                "manifest": args.out.as_posix(),
                "entities_sidecar": side.as_posix(),
                "utterances": len(script.utterances),
                "inserted": dict(sorted(script.counts.items())),
                "tagged": dict(sorted(found.items())),
                "found_rate": round(sum(found.values()) / total, 4),
                "disfluent_rate": round(
                    sum(k is not None for k in script.disfluency.values()) / len(script.utterances),
                    4,
                ),
                "misses": [m.__dict__ for m in misses],
            },
            indent=2,
            default=list,
        )
    )


if __name__ == "__main__":
    main()
