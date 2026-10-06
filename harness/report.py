"""Offline accuracy report: provider runs + manifest (+ profile) -> Markdown.

    uv run python -m harness.report --results results/ --manifest data/manifests/x.jsonl \\
        [--profile configs/profiles/x.yaml] --out reports/generated/offline.md

Scoring rules (see docs/DECISIONS.md):
- Utterances with an `exclude_reason` are not scored. Within each group, only utterances that
  every run covers are scored, so all configs are compared on identical audio (paired).
- A failed request (row with `error`) is scored as an empty hypothesis: failures are errors.
- Dates are read per utterance language (`date_order_for`).
- Real and synthetic audio are reported in separate sections and never pooled together.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from harness.datasets.manifest import Utterance, read_manifest
from harness.metrics.entities import (
    CategorySummary,
    EntityOutcome,
    EntityTagger,
    keyterm_false_insertions,
    score_entities,
    summarize,
)
from harness.metrics.normalize import WHISPER_ID, DateOrder, date_order_for, normalizer_id
from harness.metrics.stats import Interval, holm, paired_bootstrap
from harness.metrics.wer import UttScore, mean_utt_wer, pooled_wer, score_utterance
from harness.results import ResultRow, Run, read_runs
from recommender.profile import Profile, load_profile

TEMPLATES = Path(__file__).resolve().parent.parent / "reports" / "templates"
ClusterBy = Literal["speaker", "none"]
WORST_N = 10
# Below this many resampled clusters (speakers, or utterances with --cluster-by none) the
# bootstrap has too few distinct resamples to support a "better" verdict.
MIN_CLUSTERS_FOR_VERDICT = 10


@dataclass(frozen=True)
class Scored:
    utt: Utterance
    row: ResultRow
    score: UttScore  # Whisper + equivalence layer (headline)
    score_whisper: UttScore  # Whisper only (leaderboard-comparable)
    entities: tuple[EntityOutcome, ...]
    keyterm_false: int


@dataclass(frozen=True)
class ConfigStats:
    config_id: str
    wer: Interval
    wer_whisper: float
    mean_utt_wer: float
    n_utts: int
    n_words: int
    failed: int
    entities: dict[str, CategorySummary]
    keyterm_false: int


@dataclass(frozen=True)
class PairStats:
    a: str
    b: str
    diff: Interval
    p_value: float
    p_holm: float
    distinguishable: bool
    verdict: str


@dataclass(frozen=True)
class Group:
    title: str
    synthetic: bool
    configs: list[ConfigStats]
    pairs: list[PairStats]
    n_clusters: int
    entity_categories: list[str]


@dataclass(frozen=True)
class WorstRow:
    utt_id: str
    subset: str
    errors: int
    n_ref: int
    diff: str


@dataclass
class ReportData:
    generated_at: str
    manifest_label: str
    runs: list[Run]
    profile_label: str | None
    normalizer_ids: list[str]
    whisper_id: str
    n_resamples: int
    seed: int
    cluster_by: ClusterBy
    n_manifest: int
    excluded: dict[str, int]
    not_covered: int
    groups: list[Group] = field(default_factory=list)
    worst: dict[str, list[WorstRow]] = field(default_factory=dict)
    worst_n: int = WORST_N
    min_clusters: int = MIN_CLUSTERS_FOR_VERDICT


def render_diff(score: UttScore) -> str:
    """Normalized alignment: correct words plain, `[ref→hyp]`, `[-ref]`, `[+hyp]`."""
    parts: list[str] = []
    for c in score.alignment:
        ref = score.ref_tokens[c.ref_start : c.ref_end]
        hyp = score.hyp_tokens[c.hyp_start : c.hyp_end]
        if c.op == "equal":
            parts.extend(ref)
        elif c.op == "substitute":
            parts.extend(f"[{r}→{h}]" for r, h in zip(ref, hyp, strict=True))
        elif c.op == "delete":
            parts.extend(f"[-{r}]" for r in ref)
        else:
            parts.extend(f"[+{h}]" for h in hyp)
    return " ".join(parts)


class _Taggers:
    def __init__(self, profile: Profile) -> None:
        self.profile = profile

    @cache  # noqa: B019 - one tagger per date order for the life of the report
    def get(self, date_order: DateOrder) -> EntityTagger:
        return EntityTagger.from_entities(
            self.profile.entities, self.profile.resolve_path, date_order=date_order
        )


def _score_one(
    utt: Utterance, row: ResultRow, taggers: _Taggers | None, keyterms: list[str]
) -> Scored:
    order = date_order_for(utt.language)
    hyp = "" if row.error is not None else row.hyp_text
    score = score_utterance(utt.ref_text, hyp, date_order=order)
    entities: tuple[EntityOutcome, ...] = ()
    false = 0
    if taggers is not None:
        entities = tuple(score_entities(taggers.get(order), score, raw_hyp=hyp))
        false = sum(keyterm_false_insertions(score, keyterms, date_order=order).values())
    return Scored(
        utt=utt,
        row=row,
        score=score,
        score_whisper=score_utterance(utt.ref_text, hyp, equivalences=False, date_order=order),
        entities=entities,
        keyterm_false=false,
    )


def _verdict(a: str, b: str, diff: Interval, distinguishable: bool, n_clusters: int) -> str:
    if n_clusters < MIN_CLUSTERS_FOR_VERDICT:
        return f"too few speakers ({n_clusters}) to call"
    if not distinguishable:
        return "tie"
    return f"{a if diff.estimate < 0 else b} better"


def _group_stats(
    title: str,
    synthetic: bool,
    utt_ids: Sequence[str],
    scored: dict[str, dict[str, Scored]],
    configs: Sequence[str],
    *,
    n_resamples: int,
    seed: int,
    cluster_by: ClusterBy,
    categories: Sequence[str],
) -> Group | None:
    first = scored[configs[0]]
    n_ref = [first[u].score.n_ref for u in utt_ids]
    if sum(n_ref) == 0:
        return None
    clusters = [first[u].utt.speaker_id for u in utt_ids] if cluster_by == "speaker" else None
    boot = paired_bootstrap(
        {c: [scored[c][u].score.errors for u in utt_ids] for c in configs},
        n_ref,
        seed=seed,
        n_resamples=n_resamples,
        cluster_ids=clusters,
    )
    stats = []
    for c in configs:
        items = [scored[c][u] for u in utt_ids]
        stats.append(
            ConfigStats(
                config_id=c,
                wer=boot.systems[c],
                wer_whisper=pooled_wer(s.score_whisper for s in items),
                mean_utt_wer=mean_utt_wer(s.score for s in items),
                n_utts=len(items),
                n_words=sum(n_ref),
                failed=sum(s.row.error is not None for s in items),
                entities=summarize(o for s in items for o in s.entities),
                keyterm_false=sum(s.keyterm_false for s in items),
            )
        )
    diffs = list(boot.differences.values())
    adjusted, _ = holm([d.p_value for d in diffs])
    pairs = [
        PairStats(
            d.a,
            d.b,
            d.interval,
            d.p_value,
            p_adj,
            d.distinguishable,
            _verdict(d.a, d.b, d.interval, d.distinguishable, boot.n_clusters),
        )
        for d, p_adj in zip(diffs, adjusted, strict=True)
    ]
    return Group(title, synthetic, stats, pairs, boot.n_clusters, list(categories))


def build_report(
    manifest: Sequence[Utterance],
    runs: Sequence[Run],
    *,
    manifest_label: str,
    profile: Profile | None = None,
    profile_label: str | None = None,
    n_resamples: int = 10_000,
    seed: int = 0,
    cluster_by: ClusterBy = "speaker",
    generated_at: str | None = None,
) -> ReportData:
    if not runs:
        raise ValueError("no runs to report on")
    configs = [r.meta.config_id for r in runs]
    rows = {r.meta.config_id: r.by_utt() for r in runs}
    scorable = [u for u in manifest if u.exclude_reason is None]
    covered = [u for u in scorable if all(u.utt_id in rows[c] for c in configs)]
    taggers = _Taggers(profile) if profile is not None and profile.entities else None
    keyterms = profile.keyterm_list() if profile is not None else []
    categories = [e.name for e in profile.entities] if profile is not None else []

    scored = {
        c: {u.utt_id: _score_one(u, rows[c][u.utt_id], taggers, keyterms) for u in covered}
        for c in configs
    }

    data = ReportData(
        generated_at=generated_at or datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        manifest_label=manifest_label,
        runs=list(runs),
        profile_label=profile_label,
        normalizer_ids=sorted(
            {normalizer_id(date_order=date_order_for(u.language)) for u in covered}
        ),
        whisper_id=WHISPER_ID,
        n_resamples=n_resamples,
        seed=seed,
        cluster_by=cluster_by,
        n_manifest=len(manifest),
        excluded=dict(
            sorted(Counter(u.exclude_reason for u in manifest if u.exclude_reason).items())
        ),
        not_covered=len(scorable) - len(covered),
    )

    for synthetic in (False, True):
        part = [u for u in covered if u.synthetic == synthetic]
        if not part:
            continue
        by_subset: dict[str, list[str]] = defaultdict(list)
        for u in part:
            by_subset[u.subset].append(u.utt_id)
        kind = "synthetic" if synthetic else "real"
        groups = [(f"All {kind} audio", sorted(u.utt_id for u in part))]
        if len(by_subset) > 1:
            groups += [(f"{s} ({kind})", sorted(ids)) for s, ids in sorted(by_subset.items())]
        for title, ids in groups:
            g = _group_stats(
                title,
                synthetic,
                ids,
                scored,
                configs,
                n_resamples=n_resamples,
                seed=seed,
                cluster_by=cluster_by,
                categories=categories,
            )
            if g is not None:
                data.groups.append(g)

    for c in configs:
        worst = sorted(scored[c].values(), key=lambda s: (-s.score.errors, s.utt.utt_id))
        data.worst[c] = [
            WorstRow(
                s.utt.utt_id, s.utt.subset, s.score.errors, s.score.n_ref, render_diff(s.score)
            )
            for s in worst[:WORST_N]
            if s.score.errors > 0
        ]
    return data


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _interval(iv: Interval) -> str:
    return f"{100 * iv.estimate:.1f}% [{100 * iv.low:.1f}, {100 * iv.high:.1f}]"


def _pp(iv: Interval) -> str:
    return f"{100 * iv.estimate:+.1f} pp [{100 * iv.low:+.1f}, {100 * iv.high:+.1f}]"


def _md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _settings(settings: dict[str, object]) -> str:
    return json.dumps(settings, sort_keys=True) if settings else "-"


def render(data: ReportData) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,  # noqa: S701 - Markdown output, not HTML
    )
    env.filters.update(pct=_pct, interval=_interval, pp=_pp, md=_md, settings=_settings)
    return env.get_template("offline.md.j2").render(d=data)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Offline STT accuracy report")
    parser.add_argument("--results", type=Path, required=True, help="directory of runs")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", type=Path, help="use-case profile for entity scoring")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--resamples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--cluster-by", choices=["speaker", "none"], default="speaker")
    parser.add_argument("--generated-at", help="override the timestamp (for reproducible output)")
    args = parser.parse_args(argv)

    data = build_report(
        read_manifest(args.manifest),
        read_runs(args.results),
        manifest_label=args.manifest.as_posix(),
        profile=load_profile(args.profile) if args.profile else None,
        profile_label=args.profile.as_posix() if args.profile else None,
        n_resamples=args.resamples,
        seed=args.seed,
        cluster_by=args.cluster_by,
        generated_at=args.generated_at,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(data), encoding="utf-8")
    print(f"report -> {args.out}")


if __name__ == "__main__":
    main()
