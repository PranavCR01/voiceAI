from pathlib import Path

from harness.charts import read_csv, tradeoff_svg
from harness.providers.sweep import FIELDS, write_csv


def rows() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for cid, knob, vals in (
        ("deepgram_nova3_stream", "endpointing", [100, 300, 800]),
        ("deepgram_flux_stream", "eot_threshold", [0.5, 0.7, 0.9]),
        ("elevenlabs_scribe_v2_rt_stream", "vad_silence_threshold_secs", [0.3, 1.0, 1.5]),
    ):
        for i, v in enumerate(vals):
            prem, p95 = 0.3 - 0.1 * i, 400 + 500 * i
            out.append(
                dict(zip(FIELDS, [cid, f"{cid}-{i}", knob, v, 50, 0, prem, prem - 0.05, prem + 0.06,
                                  0.02, 0.0, 0.05, p95 - 200, p95 - 260, p95 - 150, p95, p95 - 90,
                                  p95 + 120], strict=True))
            )  # fmt: skip
    return out


def test_tradeoff_chart_is_byte_identical_for_the_same_input(tmp_path: Path) -> None:
    csv_path = tmp_path / "sweep.csv"
    write_csv(csv_path, rows())  # type: ignore[arg-type]
    a, b = tmp_path / "a.svg", tmp_path / "b.svg"
    tradeoff_svg(read_csv(csv_path), a)
    tradeoff_svg(read_csv(csv_path), b)
    assert a.read_bytes() == b.read_bytes()
    svg = a.read_text()
    assert "deepgram_flux_stream" in svg and "p95 endpoint delay (ms)" in svg  # text kept as text
    assert "<dc:date>" not in svg


def test_tradeoff_chart_changes_with_the_data(tmp_path: Path) -> None:
    r = rows()
    tradeoff_svg(r, tmp_path / "a.svg")  # type: ignore[arg-type]
    r[0] = {**r[0], "premature_rate": 0.9}
    tradeoff_svg(r, tmp_path / "b.svg")  # type: ignore[arg-type]
    assert (tmp_path / "a.svg").read_bytes() != (tmp_path / "b.svg").read_bytes()
