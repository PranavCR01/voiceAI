"""Provider run results: what every adapter (batch or streaming) must write.

One run = one configuration (provider + model + settings) over a manifest. On disk:

    <results_dir>/<run_id>/run.json         RunMeta (date, git SHA, config, settings)
    <results_dir>/<run_id>/results.parquet  one ResultRow per utterance
    <results_dir>/<run_id>/raw/...          raw provider responses (paths referenced per row)

Rows hold the raw (unnormalized) hypothesis. Normalization happens at scoring time, so the
normalizer id belongs to the report, not to the run.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from harness.datasets.manifest import UTT_ID_PATTERN

RUN_META = "run.json"
RESULTS = "results.parquet"
_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"


class ResultsError(ValueError):
    """A results directory is malformed or inconsistent."""


class RunMeta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(pattern=_ID)
    config_id: str = Field(pattern=_ID)
    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)  # exact, pinned model identifier
    mode: str = Field(pattern=r"^(batch|streaming)$")
    settings: dict[str, JsonValue] = Field(default_factory=dict)
    created_at: datetime
    git_sha: str = Field(min_length=7)
    manifest: str  # path or name of the manifest the run used


class ResultRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    utt_id: str = Field(pattern=UTT_ID_PATTERN)
    hyp_text: str  # raw provider output; "" when the request failed
    raw_response_path: str | None = None  # relative to the run directory
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None  # set when the request failed; hyp_text is then ""

    @model_validator(mode="after")
    def _check(self) -> ResultRow:
        if self.error is not None and self.hyp_text:
            raise ValueError("a failed request (error set) must have an empty hyp_text")
        if self.started_at and self.finished_at and self.finished_at < self.started_at:
            raise ValueError("finished_at is before started_at")
        return self


class Run(BaseModel):
    model_config = ConfigDict(frozen=True)

    meta: RunMeta
    rows: tuple[ResultRow, ...]

    def by_utt(self) -> dict[str, ResultRow]:
        return {r.utt_id: r for r in self.rows}


_FIELDS: list[pa.Field[Any]] = [
    pa.field("run_id", pa.string()),
    pa.field("config_id", pa.string()),
    pa.field("utt_id", pa.string()),
    pa.field("hyp_text", pa.string()),
    pa.field("raw_response_path", pa.string()),
    pa.field("started_at", pa.timestamp("us", tz="UTC")),
    pa.field("finished_at", pa.timestamp("us", tz="UTC")),
    pa.field("error", pa.string()),
]
_SCHEMA = pa.schema(_FIELDS)


def write_run(results_dir: Path, meta: RunMeta, rows: Iterable[ResultRow]) -> Path:
    ordered = sorted(rows, key=lambda r: r.utt_id)
    ids = [r.utt_id for r in ordered]
    if len(set(ids)) != len(ids):
        raise ResultsError(f"run {meta.run_id}: duplicate utt_id rows")
    run_dir = results_dir / meta.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / RUN_META).write_text(meta.model_dump_json(indent=2) + "\n", encoding="utf-8")
    records: list[dict[str, Any]] = [
        {"run_id": meta.run_id, "config_id": meta.config_id, **r.model_dump()} for r in ordered
    ]
    pq.write_table(pa.Table.from_pylist(records, schema=_SCHEMA), run_dir / RESULTS)
    return run_dir


def read_run(run_dir: Path) -> Run:
    try:
        meta = RunMeta.model_validate_json((run_dir / RUN_META).read_text(encoding="utf-8"))
        table = pq.read_table(run_dir / RESULTS)
    except (OSError, ValueError) as e:
        raise ResultsError(f"{run_dir}: {e}") from e
    rows = []
    for rec in table.to_pylist():
        if rec.pop("run_id") != meta.run_id or rec.pop("config_id") != meta.config_id:
            raise ResultsError(f"{run_dir}: rows disagree with run.json run_id/config_id")
        rows.append(ResultRow.model_validate(rec))
    return Run(meta=meta, rows=tuple(rows))


def read_runs(results_dir: Path) -> list[Run]:
    """Every run under `results_dir`, sorted by config_id; config_ids must be unique."""
    dirs = sorted(p.parent for p in results_dir.glob(f"*/{RUN_META}"))
    if not dirs:
        raise ResultsError(f"no runs (*/{RUN_META}) under {results_dir}")
    runs = sorted((read_run(d) for d in dirs), key=lambda r: r.meta.config_id)
    configs = [r.meta.config_id for r in runs]
    if len(set(configs)) != len(configs):
        raise ResultsError(f"more than one run per config_id under {results_dir}: {configs}")
    return runs
