"""Minimal reader for Praat TextGrid files (long "ooTextFile" format, interval tiers only).

Handles CRLF line endings, UTF-8 / UTF-8-BOM / UTF-16 files and Praat's doubled-quote escape
(`""` inside a string means one `"`). Point tiers are skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class TextGridError(ValueError):
    """The file is not a TextGrid this reader understands."""


@dataclass(frozen=True)
class Interval:
    index: int  # 1-based, as numbered in the file
    xmin: float
    xmax: float
    text: str


@dataclass(frozen=True)
class Tier:
    name: str
    intervals: tuple[Interval, ...]


_NUM = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
_STR = r'"((?:[^"]|"")*)"'
_ITEM = re.compile(r"item \[\d+\]:(.*?)(?=item \[\d+\]:|\Z)", re.S)
_TIER_CLASS = re.compile(r'class = "(\w+)"')
_TIER_NAME = re.compile(rf"name = {_STR}", re.S)
_INTERVAL = re.compile(
    rf"intervals \[(\d+)\]:\s*xmin = {_NUM}\s*xmax = {_NUM}\s*text = {_STR}", re.S
)


def _decode(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


def parse_textgrid(text: str) -> list[Tier]:
    if 'Object class = "TextGrid"' not in text:
        raise TextGridError("not a TextGrid (missing 'Object class = \"TextGrid\"')")
    if "item [" not in text:
        raise TextGridError("only the long TextGrid format is supported")
    tiers = []
    for item in _ITEM.finditer(text):
        body = item.group(1)
        cls = _TIER_CLASS.search(body)
        if cls is None or cls.group(1) != "IntervalTier":
            continue
        name = _TIER_NAME.search(body)
        intervals = tuple(
            Interval(
                index=int(m.group(1)),
                xmin=float(m.group(2)),
                xmax=float(m.group(3)),
                text=m.group(4).replace('""', '"'),
            )
            for m in _INTERVAL.finditer(body)
        )
        tiers.append(Tier(name.group(1).replace('""', '"') if name else "", intervals))
    return tiers


def read_textgrid(path: Path) -> list[Tier]:
    try:
        return parse_textgrid(_decode(path.read_bytes()))
    except TextGridError as e:
        raise TextGridError(f"{path}: {e}") from e
