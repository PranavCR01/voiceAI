"""Text normalization applied to both reference and hypothesis before WER.

Two layers, applied identically to both sides:

1. Whisper `EnglishTextNormalizer` (the `whisper-normalizer` package, a standalone port of
   OpenAI Whisper's normalizer). This alone is what public leaderboards use, so results keep a
   "whisper-only" WER column for comparability.
2. An equivalence layer (`EQUIVALENCE_VERSION`) for formatting differences Whisper leaves apart
   but a customer would call identical (unit abbreviations, numeric dates, ordinal suffixes,
   "O.K."/"ok", spoken day-month order, "ninth"), and works around Whisper's digit handling:
   it rewrites the digit 1 as "one" (breaking decimals and digit runs), drops leading zeros,
   and deletes parenthesized text such as a phone area code. Each rule has a fixture in
   tests/fixtures/normalization_cases.jsonl and a reason in docs/DECISIONS.md. Rules are
   domain-neutral: no healthcare terms here.

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
EQUIVALENCE_VERSION = "4"

# Transcriber markup such as <UNSURE>word</UNSURE> or <UNIN/>. Paired tags are unwrapped (the
# transcriber's best guess is kept); self-closing tags are dropped. Utterances that should not be
# scored at all (e.g. containing <UNIN/>) are excluded by the dataset loader, not here.
_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9_-]*\s*/?>")

# --- equivalence rules applied before Whisper (need the raw punctuation) ----------------------

_OK = re.compile(r"\bo\.\s?k\.?(?![a-z])", re.IGNORECASE)
# Whisper's ordinal table spells it "nineth", so "ninth" (and "twenty ninth") stay words.
_NINTH = re.compile(r"\bninth\b", re.IGNORECASE)
# Same separator twice, "/" or "-" only: dotted forms collide with version numbers (1.2.2026).
_NUMERIC_DATE = re.compile(r"\b(\d{1,2})([/-])(\d{1,2})\2(\d{4})\b")
# Digits in parentheses, e.g. a phone area code "(555)": Whisper deletes parenthesized text.
_PAREN_DIGITS = re.compile(r"\((\d[\d\s.-]*)\)")
# A number with a leading zero ("07700", "007"), not a decimal ("0.5"): Whisper parses it as an
# integer and drops the zero, but keeps zeros it builds from spelled digits.
_LEADING_ZERO = re.compile(r"(?<![\d.])0\d+(?![\d.])")
_DIGIT_WORDS = "zero one two three four five six seven eight nine".split()
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
# Words that are also months but common as other words: only read as a month when "of"
# precedes them ("2 of may") or a year follows ("2 may 1990"), never in "1 may be".
_AMBIGUOUS_MONTHS = frozenset({"may", "march"})
_YEAR = re.compile(r"^\d{4}$")
_ORDINAL = re.compile(r"^(\d+)(?:st|nd|rd|th)$")
_ONE_DECIMAL = re.compile(r"^one(\.\d+)$")  # Whisper: "1.5" -> "one.5"
_BARE_DECIMAL = re.compile(r"^(\.\d+)$")  # Whisper: "0 point 5" -> ".5"
_DIGITS = re.compile(r"^\d+$")
# Runs of digit groups this long are identifiers (phone, account numbers), so their grouping
# ("555 123 4567" vs "5551234567" vs "5 5 5 ...") is formatting, not content. Runs of single
# digits ("1 2 3") are digit-by-digit speech, which Whisper itself joins when spelled out.
_MIN_RUN_DIGITS = 7
_MIN_SINGLE_DIGIT_RUN = 3


# Equivalence rules by name, so diagnostics can switch each off (`normalize(disable=...)`).
# Scoring always uses all of them; `normalizer_id` does not cover disabled sets.
RULES = (
    "okay",  # O.K. / ok -> okay
    "ninth",  # ninth -> nineth, which Whisper turns into 9th
    "numeric_dates",  # 03/04/1980 -> march 4 1980
    "paren_digits",  # (555) -> 555
    "leading_zero",  # 07700 -> zero seven seven zero zero
    "units",  # milligrams -> mg
    "ordinals",  # 5th -> 5
    "decimals",  # one.5 -> 1.5, .5 -> 0.5
    "digit_one",  # "one" next to a digit group -> 1
    "digit_join",  # long digit-group runs -> one token
    "spoken_dates",  # 20 of april -> april 20
)


@cache
def _whisper() -> EnglishTextNormalizer:
    return EnglishTextNormalizer()


def normalizer_id(
    *,
    equivalences: bool = True,
    date_order: DateOrder = "mdy",
    hyp_date_order: DateOrder | None = None,
) -> str:
    """`date_order` is the reference's; `hyp_date_order` is recorded only when it differs."""
    if not equivalences:
        return WHISPER_ID
    base = f"{WHISPER_ID}+equiv-v{EQUIVALENCE_VERSION}/{date_order}"
    if hyp_date_order is not None and hyp_date_order != date_order:
        return f"{base},hyp-{hyp_date_order}"
    return base


# Regions that write numeric dates month-first. Everything else is read day-first.
_MDY_REGIONS = frozenset({"US", "PH", "FM", "MH", "PW"})


def date_order_for(language: str | None) -> DateOrder:
    """Day/month order for a BCP-47 tag: month-first for US-style regions and for a bare or
    missing tag (the US default), day-first for every other region (en-GB, en-IN, ...)."""
    if not language:
        return "mdy"
    region = next((p.upper() for p in language.split("-")[1:] if len(p) == 2), None)
    return "mdy" if region is None or region in _MDY_REGIONS else "dmy"


def strip_markup(text: str) -> str:
    return _TAG.sub(" ", text)


def _spell_date(m: re.Match[str], date_order: DateOrder) -> str:
    a, b, year = int(m.group(1)), int(m.group(3)), m.group(4)
    month, day = (a, b) if date_order == "mdy" else (b, a)
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return m.group(0)
    return f"{_MONTHS[month - 1]} {day} {year}"


def _spell_digits(m: re.Match[str]) -> str:
    return " ".join(_DIGIT_WORDS[int(d)] for d in m.group(0))


def _pre(text: str, date_order: DateOrder, off: frozenset[str] = frozenset()) -> str:
    if "okay" not in off:
        text = _OK.sub("okay", text)
    if "ninth" not in off:
        text = _NINTH.sub("nineth", text)
    if "numeric_dates" not in off:
        text = _NUMERIC_DATE.sub(lambda m: _spell_date(m, date_order), text)
    if "paren_digits" not in off:
        text = _PAREN_DIGITS.sub(r" \1 ", text)
    if "leading_zero" not in off:
        text = _LEADING_ZERO.sub(_spell_digits, text)
    return text


def _post_token(token: str, off: frozenset[str] = frozenset()) -> str:
    if token in _UNITS:
        return token if "units" in off else _UNITS[token]
    if token == "ok" and "okay" not in off:
        return "okay"
    rules = (("ordinals", _ORDINAL, "{}"), ("decimals", _ONE_DECIMAL, "1{}"))
    for name, pattern, fmt in (*rules, ("decimals", _BARE_DECIMAL, "0{}")):
        m = pattern.match(token)
        if m and name not in off:
            return fmt.format(m.group(1))
    return token


def _fix_digit_runs(tokens: list[str], off: frozenset[str] = frozenset()) -> list[str]:
    # Whisper rewrites a lone digit 1 as "one"; restore it when it sits next to a digit group.
    out = [
        "1"
        if t == "one"
        and "digit_one" not in off
        and (
            (i > 0 and _DIGITS.match(tokens[i - 1]))
            or (i + 1 < len(tokens) and _DIGITS.match(tokens[i + 1]))
        )
        else t
        for i, t in enumerate(tokens)
    ]
    # Join long runs of digit groups into one token.
    merged: list[str] = []
    run: list[str] = []
    for t in [*out, ""]:
        if _DIGITS.match(t):
            run.append(t)
            continue
        long_run = len(run) > 1 and sum(map(len, run)) >= _MIN_RUN_DIGITS
        spelled_run = len(run) >= _MIN_SINGLE_DIGIT_RUN and all(len(d) == 1 for d in run)
        if (long_run or spelled_run) and "digit_join" not in off:
            merged.append("".join(run))
        else:
            merged.extend(run)
        run = []
        if t:
            merged.append(t)
    return merged


def _day(token: str) -> str | None:
    """A day-of-month token as digits ("one" counts: Whisper spells a lone digit 1)."""
    if token == "one":
        return "1"
    if _DIGITS.match(token) and not token.startswith("0") and 1 <= int(token) <= 31:
        return token
    return None


def _canonical_dates(tokens: list[str]) -> list[str]:
    """Spoken day-month order to month-day: "20 of april" / "20 april" -> "april 20".

    Formatters write "April 20, 1980" while people say "the twentieth of April", so the same
    date otherwise costs two errors. "MONTH one" becomes "MONTH 1" for the same reason.
    """
    out: list[str] = []
    i = 0
    while i < len(tokens):
        day = _day(tokens[i])
        if day is not None:
            has_of = i + 2 < len(tokens) and tokens[i + 1] == "of"
            j = i + 2 if has_of else i + 1
            month = tokens[j] if j < len(tokens) else ""
            year_follows = j + 1 < len(tokens) and bool(_YEAR.match(tokens[j + 1]))
            if month in _MONTHS and (month not in _AMBIGUOUS_MONTHS or has_of or year_follows):
                out += [month, day]
                i = j + 1
                continue
        if tokens[i] == "one" and out and out[-1] in _MONTHS:
            out.append("1")
        else:
            out.append(tokens[i])
        i += 1
    return out


def normalize(
    text: str,
    *,
    equivalences: bool = True,
    date_order: DateOrder = "mdy",
    disable: frozenset[str] = frozenset(),
) -> str:
    """Markup-stripped, normalized text with single spaces.

    `equivalences=False` gives plain Whisper normalization. `date_order` says how to read
    numeric dates like 03/04/1980 ("mdy" = US, "dmy" = UK and most other locales).
    `disable` switches off named `RULES` (diagnostics only).
    """
    unknown = disable - set(RULES)
    if unknown:
        raise ValueError(f"unknown equivalence rules: {sorted(unknown)}")
    text = strip_markup(text)
    if equivalences:
        text = _pre(text, date_order, disable)
    tokens = str(_whisper()(text)).split()
    if equivalences:
        tokens = _fix_digit_runs([_post_token(t, disable) for t in tokens], disable)
        if "spoken_dates" not in disable:
            tokens = _canonical_dates(tokens)
    return " ".join(tokens)
