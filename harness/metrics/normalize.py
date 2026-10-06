"""Text normalization applied to both reference and hypothesis before WER.

Two layers, applied identically to both sides:

1. Whisper `EnglishTextNormalizer` (the `whisper-normalizer` package, a standalone port of
   OpenAI Whisper's normalizer). This alone is what public leaderboards use, so results keep a
   "whisper-only" WER column for comparability.
2. An equivalence layer (`EQUIVALENCE_VERSION`) for formatting differences Whisper leaves apart
   but a customer would call identical: unit abbreviations, numeric dates, ordinal suffixes,
   "O.K."/"ok". Each rule has a fixture in tests/fixtures/normalization_cases.jsonl
   and a reason in docs/DECISIONS.md. Rules are domain-neutral: no healthcare terms here.

The normalizer id (`normalizer_id()`) goes into every result's metadata because changing any
of this changes WER.
"""

from __future__ import annotations

import re
import warnings
from functools import cache
from importlib.metadata import version
from typing import Literal

with warnings.catch_warnings():
    # The package ships a docstring with an invalid escape sequence; harmless.
    warnings.simplefilter("ignore", SyntaxWarning)
    from whisper_normalizer.english import EnglishTextNormalizer

DateOrder = Literal["mdy", "dmy"]

WHISPER_ID = f"whisper-normalizer=={version('whisper-normalizer')}/EnglishTextNormalizer"
EQUIVALENCE_VERSION = "1"

# Transcriber markup such as <UNSURE>word</UNSURE> or <UNIN/>. Paired tags are unwrapped (the
# transcriber's best guess is kept); self-closing tags are dropped. Utterances that should not be
# scored at all (e.g. containing <UNIN/>) are excluded by the dataset loader, not here.
_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9_-]*\s*/?>")

# --- equivalence rules applied before Whisper (need the raw punctuation) ----------------------

_OK = re.compile(r"\bo\.\s?k\.?(?![a-z])", re.IGNORECASE)
# Same separator twice, "/" or "-" only: dotted forms collide with version numbers (1.2.2026).
_NUMERIC_DATE = re.compile(r"\b(\d{1,2})([/-])(\d{1,2})\2(\d{4})\b")
_MONTHS = (
    "january february march april may june july august september october november december"
).split()

# --- equivalence rules applied after Whisper (on tokens) --------------------------------------

_UNITS = {
    "milligram": "mg",
    "milligrams": "mg",
    "microgram": "mcg",
    "micrograms": "mcg",
    "µg": "mcg",  # micro sign
    "μg": "mcg",  # Greek mu (Whisper's output for the micro sign)
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "mls": "ml",
    "kilogram": "kg",
    "kilograms": "kg",
    "kilometer": "km",
    "kilometers": "km",
    "kilometre": "km",
    "kilometres": "km",
}
_TOKEN_MAP = {**_UNITS, "ok": "okay"}
_ORDINAL = re.compile(r"^(\d+)(?:st|nd|rd|th)$")


@cache
def _whisper() -> EnglishTextNormalizer:
    return EnglishTextNormalizer()


def normalizer_id(*, equivalences: bool = True, date_order: DateOrder = "mdy") -> str:
    if not equivalences:
        return WHISPER_ID
    return f"{WHISPER_ID}+equiv-v{EQUIVALENCE_VERSION}/{date_order}"


def strip_markup(text: str) -> str:
    return _TAG.sub(" ", text)


def _spell_date(m: re.Match[str], date_order: DateOrder) -> str:
    a, b, year = int(m.group(1)), int(m.group(3)), m.group(4)
    month, day = (a, b) if date_order == "mdy" else (b, a)
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return m.group(0)
    return f"{_MONTHS[month - 1]} {day} {year}"


def _pre(text: str, date_order: DateOrder) -> str:
    text = _OK.sub("okay", text)
    return _NUMERIC_DATE.sub(lambda m: _spell_date(m, date_order), text)


def _post_token(token: str) -> str:
    token = _TOKEN_MAP.get(token, token)
    m = _ORDINAL.match(token)
    return m.group(1) if m else token


def normalize(text: str, *, equivalences: bool = True, date_order: DateOrder = "mdy") -> str:
    """Markup-stripped, normalized text with single spaces.

    `equivalences=False` gives plain Whisper normalization. `date_order` says how to read
    numeric dates like 03/04/1980 ("mdy" = US, "dmy" = UK and most other locales).
    """
    text = strip_markup(text)
    if equivalences:
        text = _pre(text, date_order)
    tokens = str(_whisper()(text)).split()
    if equivalences:
        tokens = [_post_token(t) for t in tokens]
    return " ".join(tokens)
