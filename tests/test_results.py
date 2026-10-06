import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from harness.results import ResultRow, ResultsError, RunMeta, read_run, read_runs, write_run

RUNS = Path(__file__).parent / "fixtures" / "report" / "runs"


def load_fixture(name: str) -> tuple[RunMeta, list[ResultRow]]:
    data: dict[str, Any] = json.loads((RUNS / f"{name}.json").read_text())
    return RunMeta.model_validate(data["meta"]), [ResultRow.model_validate(r) for r in data["rows"]]


def test_round_trip(tmp_path: Path) -> None:
    meta, rows = load_fixture("fake_b")
    run = read_run(write_run(tmp_path, meta, reversed(rows)))
    assert run.meta == meta
    assert list(run.rows) == sorted(rows, key=lambda r: r.utt_id)
    assert run.by_utt()["fixture:p4"].error == "timeout after 30s"


def test_timestamps_survive_round_trip(tmp_path: Path) -> None:
    meta, _ = load_fixture("fake_a")
    t0 = datetime(2026, 10, 6, 12, 0, 0, 123000, tzinfo=UTC)
    t1 = datetime(2026, 10, 6, 12, 0, 1, tzinfo=UTC)
    row = ResultRow(utt_id="x:1", hyp_text="hi", started_at=t0, finished_at=t1)
    [back] = read_run(write_run(tmp_path, meta, [row])).rows
    assert (back.started_at, back.finished_at) == (t0, t1)


def test_read_runs_sorted_and_unique(tmp_path: Path) -> None:
    for name in ("fake_b", "fake_a"):
        write_run(tmp_path, *load_fixture(name))
    assert [r.meta.config_id for r in read_runs(tmp_path)] == ["fake_a", "fake_b"]
    meta, rows = load_fixture("fake_a")
    write_run(tmp_path, meta.model_copy(update={"run_id": "run-a2"}), rows)
    with pytest.raises(ResultsError, match="more than one run per config_id"):
        read_runs(tmp_path)


def test_empty_results_dir(tmp_path: Path) -> None:
    with pytest.raises(ResultsError, match="no runs"):
        read_runs(tmp_path)


def test_duplicate_rows_rejected(tmp_path: Path) -> None:
    meta, rows = load_fixture("fake_a")
    with pytest.raises(ResultsError, match="duplicate"):
        write_run(tmp_path, meta, [rows[0], rows[0]])


def test_failed_row_must_have_empty_hypothesis() -> None:
    with pytest.raises(ValidationError, match="empty hyp_text"):
        ResultRow(utt_id="x:1", hyp_text="partial", error="boom")


def test_time_order_checked() -> None:
    t = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValidationError, match="before started_at"):
        ResultRow(utt_id="x:1", hyp_text="", started_at=t, finished_at=t.replace(year=2025))


def test_corrupt_run_dir(tmp_path: Path) -> None:
    (tmp_path / "r").mkdir()
    (tmp_path / "r" / "run.json").write_text("{}")
    with pytest.raises(ResultsError):
        read_run(tmp_path / "r")
