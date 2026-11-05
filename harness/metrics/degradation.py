"""How much each configuration loses under an augmentation recipe: paired, speaker-clustered.

    uv run python -m harness.metrics.degradation \\
        --clean-results results/ --clean-manifest data/manifests/primock57.jsonl \\
        --augmented-results results_augmented/telephony_g712/ \\
        --augmented-manifest data/manifests/primock57.telephony_g712.jsonl \\
        --out reports/generated/primock57_degradation_telephony_g712.md

Each augmented utterance is paired with its parent (`parent_utt_id`), both are scored against the
parent's reference with the same normalizer, and the WER difference (augmented − clean) gets a
paired bootstrap interval that resamples whole speakers, per config present in both result
directories. Only utterances both runs cover are scored, and the number is reported. Pairing
removes between-utterance variance, so a degradation is resolved far more tightly than the two
WER intervals side by side would suggest. The recommender's "breaks at" thresholds (SNR, phone
channel) come from these numbers.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from harness.datasets.manifest import Utterance, read_manifest
from harness.metrics.normalize import DateOrder, date_order_for
from harness.metrics.stats import Interval, paired_bootstrap
from harness.metrics.wer import score_utterance
from harness.providers.registry import load_registry
from harness.results import Run, read_runs


@dataclass(frozen=True)
class Degradation:
    config_id: str
    utterances: int
    speakers: int
    clean: Interval
    augmented: Interval
    difference: Interval  # augmented − clean, in WER (fraction)
    p_value: float

    @property
    def relative(self) -> float:
        return self.difference.estimate / self.clean.estimate if self.clean.estimate else 0.0


def degradation(
    clean: Run,
    augmented: Run,
    parents: Mapping[str, Utterance],
    children: Sequence[Utterance],
    *,
    hyp_date_order: DateOrder | None = None,
    n_resamples: int = 10_000,
    seed: int = 0,
) -> Degradation:
    if clean.meta.config_id != augmented.meta.config_id:
        raise ValueError("clean and augmented runs must be the same config")
    c_rows, a_rows = clean.by_utt(), augmented.by_utt()
    errs: dict[str, list[int]] = {"clean": [], "augmented": []}
    n_ref: list[int] = []
    clusters: list[str] = []
    for child in children:
        parent = parents.get(child.parent_utt_id or "")
        if parent is None or parent.exclude_reason is not None:
            continue
        if child.utt_id not in a_rows or parent.utt_id not in c_rows:
            continue
        order = date_order_for(parent.language)
        hyp_order = hyp_date_order or order
        sc = score_utterance(
            parent.ref_text,
            c_rows[parent.utt_id].hyp_text,
            date_order=order,
            hyp_date_order=hyp_order,
        )
        sa = score_utterance(
            parent.ref_text,
            a_rows[child.utt_id].hyp_text,
            date_order=order,
            hyp_date_order=hyp_order,
        )
        errs["clean"].append(sc.errors)
        errs["augmented"].append(sa.errors)
        n_ref.append(sc.n_ref)
        clusters.append(parent.speaker_id)
    if not n_ref:
        raise ValueError(f"{clean.meta.config_id}: no utterance is covered by both runs")
    res = paired_bootstrap(errs, n_ref, seed=seed, n_resamples=n_resamples, cluster_ids=clusters)
    diff = res.differences[("augmented", "clean")]  # names are sorted: augmented − clean
    interval, p = diff.interval, diff.p_value
    return Degradation(
        config_id=clean.meta.config_id,
        utterances=len(n_ref),
        speakers=len(set(clusters)),
        clean=res.systems["clean"],
        augmented=res.systems["augmented"],
        difference=interval,
        p_value=p,
    )


def _pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def _pp(i: Interval) -> str:
    return f"{100 * i.estimate:+.2f} pp [{100 * i.low:+.2f}, {100 * i.high:+.2f}]"


def render(recipe: str, rows: Sequence[Degradation], dropped: Mapping[str, int]) -> str:
    lines = [
        f"# Degradation under `{recipe}`",
        "",
        "Paired per utterance against the same config on the parent (clean) audio; 95% bootstrap"
        " intervals resampling whole speakers. Difference = augmented − clean WER.",
        "",
        "| Config | Clean WER | Augmented WER | Difference [95% CI] | Relative | p | Utts"
        " | Speakers |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for d in sorted(rows, key=lambda d: d.difference.estimate):
        lines.append(
            f"| {d.config_id} | {_pct(d.clean.estimate)} | {_pct(d.augmented.estimate)} | "
            f"{_pp(d.difference)} | {100 * d.relative:+.0f}% | {d.p_value:.4f} | "
            f"{d.utterances} | {d.speakers} |"
        )
    skipped = [f"{k}: {v}" for k, v in sorted(dropped.items()) if v]
    if skipped:
        lines += ["", "Utterances not covered by both runs (dropped): " + ", ".join(skipped) + "."]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--clean-results", type=Path, required=True)
    ap.add_argument("--clean-manifest", type=Path, required=True)
    ap.add_argument("--augmented-results", type=Path, required=True)
    ap.add_argument("--augmented-manifest", type=Path, required=True)
    ap.add_argument("--registry", type=Path, default=Path("configs/providers.yaml"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--resamples", type=int, default=10_000)
    args = ap.parse_args(argv)

    parents = {u.utt_id: u for u in read_manifest(args.clean_manifest)}
    children = read_manifest(args.augmented_manifest)
    recipes = {c.utt_id.rsplit(":", 1)[-1] for c in children}
    recipe = recipes.pop() if len(recipes) == 1 else args.augmented_manifest.name
    clean = {r.meta.config_id: r for r in read_runs(args.clean_results)}
    known = {c.config_id: c for c in load_registry(args.registry).configs}
    rows, dropped = [], {}
    for aug in read_runs(args.augmented_results):
        cid = aug.meta.config_id
        if cid not in clean:
            continue
        reg = known.get(cid)
        d = degradation(
            clean[cid],
            aug,
            parents,
            children,
            hyp_date_order=reg.output_date_order if reg else None,
            n_resamples=args.resamples,
        )
        rows.append(d)
        scorable = sum(
            1
            for c in children
            if (p := parents.get(c.parent_utt_id or "")) and not p.exclude_reason
        )
        dropped[cid] = scorable - d.utterances
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(recipe, rows, dropped), encoding="utf-8")
    print(f"{recipe}: {len(rows)} configs -> {args.out}")


if __name__ == "__main__":
    main()
