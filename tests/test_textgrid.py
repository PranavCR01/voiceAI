from pathlib import Path

import pytest

from harness.datasets.textgrid import Interval, TextGridError, parse_textgrid, read_textgrid

HEADER = 'File type = "ooTextFile"\nObject class = "TextGrid"\n\nxmin = 0\nxmax = 3\n'


def grid(*items: str) -> str:
    body = "".join(f"    item [{i}]:\n{item}" for i, item in enumerate(items, start=1))
    return f"{HEADER}tiers? <exists>\nsize = {len(items)}\nitem []:\n{body}"


INTERVAL_TIER = (
    '        class = "IntervalTier"\n        name = "A ""quoted"" tier"\n'
    "        xmin = 0\n        xmax = 3\n        intervals: size = 2\n"
    "        intervals [1]:\n            xmin = 0\n            xmax = 1.5e0\n"
    '            text = "say ""hi""\nthen go"\n'
    '        intervals [2]:\n            xmin = 1.5\n            xmax = 3\n            text = ""\n'
)
POINT_TIER = (
    '        class = "TextTier"\n        name = "points"\n        xmin = 0\n        xmax = 3\n'
    "        points: size = 1\n        points [1]:\n"
    '            number = 1\n            mark = "x"\n'
)


def test_parses_intervals_escapes_and_multiline_text() -> None:
    [tier] = parse_textgrid(grid(INTERVAL_TIER))
    assert tier.name == 'A "quoted" tier'
    assert tier.intervals == (
        Interval(1, 0.0, 1.5, 'say "hi"\nthen go'),
        Interval(2, 1.5, 3.0, ""),
    )


def test_skips_point_tiers() -> None:
    tiers = parse_textgrid(grid(POINT_TIER, INTERVAL_TIER))
    assert [t.name for t in tiers] == ['A "quoted" tier']


@pytest.mark.parametrize(("encoding", "bom"), [("utf-8", b""), ("utf-8", b"\xef\xbb\xbf")])
def test_reads_utf8_with_or_without_bom(tmp_path: Path, encoding: str, bom: bytes) -> None:
    path = tmp_path / "x.TextGrid"
    path.write_bytes(bom + grid(INTERVAL_TIER).replace("\n", "\r\n").encode(encoding))
    assert read_textgrid(path)[0].intervals[0].xmax == 1.5


def test_reads_utf16(tmp_path: Path) -> None:
    path = tmp_path / "x.TextGrid"
    path.write_bytes(grid(INTERVAL_TIER).encode("utf-16"))
    assert len(read_textgrid(path)[0].intervals) == 2


def test_rejects_non_textgrid_and_short_format(tmp_path: Path) -> None:
    with pytest.raises(TextGridError, match="not a TextGrid"):
        parse_textgrid("hello")
    with pytest.raises(TextGridError, match="long TextGrid format"):
        parse_textgrid(HEADER + "<exists>\n1\n")
    bad = tmp_path / "bad.TextGrid"
    bad.write_text("nope")
    with pytest.raises(TextGridError, match="bad.TextGrid"):
        read_textgrid(bad)
