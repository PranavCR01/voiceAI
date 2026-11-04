"""Per-rule diagnostic for the equivalence layer: does any rule over-match?

    uv run python -m harness.metrics.equivalence_breakdown --results results/ \\
        --manifest data/manifests/primock57.jsonl --out reports/generated/equivalence_breakdown.md

For each rule in `normalize.RULES` and each config, on the same utterances the report scores:
- pooled WER with that rule switched off (all others on), and the change vs the full layer;
- how many utterances the rule changes, split into errors removed and errors added;
- the changed utterances with the most errors removed, normalized with and without the rule,
  so a reader can check each match is a real equivalence and not an over-match.

A WER drop alone can't show a rule is right (an over-matching rule also lowers WER), which is
why the examples are part of the output. Diagnostic only: scoring always uses every rule.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from harness.datasets.manifest import Utterance, read_manifest
from harness.metrics.normalize import RULES, DateOrder, date_order_for, normalize
from harness.metrics.wer import score_utterance
from harness.results import Run, read_runs

N_EXAMPLES = 8


@dataclass(frozen=True)
class Example:
    utt_id: str
    errors_with: int
    errors_without: int
    ref_with: str
    hyp_with: str
    ref_without: str
    hyp_without: str


@dataclass(frozen=True)
class RuleEffect:
    rule: str
    config_id: str
    wer_without: float
    utts_helped: int  # fewer errors with the rule
    utts_hurt: int  # more errors with the rule
    errors_removed: int
    errors_added: int
    examples: tuple[Example, ...]


@dataclass(frozen=True)
class Breakdown:
    configs: tuple[str, ...]
    n_utts: int
    wer_full: dict[str, float]
    wer_whisper: dict[str, float]
    effects: tuple[RuleEffect, ...]


def _covered(manifest: Sequence[Utterance], runs: Sequence[Run]) -> list[Utterance]:
    rows = [r.by_utt() for r in runs]
    return [u for u in manifest if u.exclude_reason is None and all(u.utt_id in r for r in rows)]


def _norm_all(
    texts: Sequence[str], orders: Sequence[DateOrder], *, off: frozenset[str] | None
) -> list[str]:
    if off is None:  # Whisper only
        return [normalize(t, equivalences=False) for t in texts]
    return [normalize(t, date_order=o, disable=off) for t, o in zip(texts, orders, strict=True)]


def breakdown(
    manifest: Sequence[Utterance],
    runs: Sequence[Run],
    *,
    hyp_date_orders: Mapping[str, DateOrder | None] | None = None,
    rules: Sequence[str] = RULES,
    n_examples: int = N_EXAMPLES,
) -> Breakdown:
    utts = _covered(manifest, runs)
    if not utts:
        raise ValueError("no utterance is covered by every run")
    ref_orders = [date_order_for(u.language) for u in utts]
    refs = [u.ref_text for u in utts]
    variants: list[frozenset[str] | None] = [None, frozenset(), *(frozenset({r}) for r in rules)]
    ref_norm = {v: _norm_all(refs, ref_orders, off=v) for v in variants}
    n_words = sum(len(t.split()) for t in ref_norm[frozenset()])

    configs = tuple(r.meta.config_id for r in runs)
    wer_full: dict[str, float] = {}
    wer_whisper: dict[str, float] = {}
    effects: list[RuleEffect] = []
    for run in runs:
        c = run.meta.config_id
        by_utt = run.by_utt()
        hyps = [
            "" if by_utt[u.utt_id].error is not None else by_utt[u.utt_id].hyp_text for u in utts
        ]
        hyp_order = (hyp_date_orders or {}).get(c)
        hyp_orders = [hyp_order or o for o in ref_orders]

        def errors(v: frozenset[str] | None, hyp_norm: list[str]) -> list[int]:
            return [
                score_utterance(r, h, normalized=True).errors
                for r, h in zip(ref_norm[v], hyp_norm, strict=True)
            ]

        hyp_full = _norm_all(hyps, hyp_orders, off=frozenset())
        err_full = errors(frozenset(), hyp_full)
        wer_full[c] = sum(err_full) / n_words
        whisper_refs = ref_norm[None]
        wer_whisper[c] = sum(errors(None, _norm_all(hyps, hyp_orders, off=None))) / sum(
            len(t.split()) for t in whisper_refs
        )
        for rule in rules:
            v = frozenset({rule})
            hyp_off = _norm_all(hyps, hyp_orders, off=v)
            err_off = errors(v, hyp_off)
            n_off = sum(len(t.split()) for t in ref_norm[v])
            deltas = [off - full for off, full in zip(err_off, err_full, strict=True)]
            changed = sorted(
                (i for i, d in enumerate(deltas) if d != 0), key=lambda i: (-deltas[i], i)
            )
            examples = tuple(
                Example(
                    utts[i].utt_id,
                    err_full[i],
                    err_off[i],
                    ref_norm[frozenset()][i],
                    hyp_full[i],
                    ref_norm[v][i],
                    hyp_off[i],
                )
                for i in changed[:n_examples]
            )
            effects.append(
                RuleEffect(
                    rule=rule,
                    config_id=c,
                    wer_without=sum(err_off) / n_off,
                    utts_helped=sum(d > 0 for d in deltas),
                    utts_hurt=sum(d < 0 for d in deltas),
                    errors_removed=sum(d for d in deltas if d > 0),
                    errors_added=-sum(d for d in deltas if d < 0),
                    examples=examples,
                )
            )
    return Breakdown(configs, len(utts), wer_full, wer_whisper, tuple(effects))


def _pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def render(b: Breakdown, *, label: str) -> str:
    lines = [
        "# Equivalence layer: per-rule breakdown",
        "",
        f"- **Data:** `{label}`, {b.n_utts} utterances scored by every run.",
        '- **Diagnostic only.** Scoring always applies every rule. "Without" = that one rule '
        "off, all others on. Helped/hurt = utterances with fewer/more errors *because of* the "
        "rule. A WER drop doesn't prove a rule right (an over-match also lowers WER): read the "
        "examples.",
        "",
        "| Config | Whisper only | Full layer |",
        "|---|---|---|",
    ]
    lines += [f"| {c} | {_pct(b.wer_whisper[c])} | {_pct(b.wer_full[c])} |" for c in b.configs]
    lines += [
        "",
        "| Rule | Config | WER without | Change from rule | Utts helped / hurt | "
        "Errors removed / added |",
        "|---|---|---|---|---|---|",
    ]
    for e in b.effects:
        change = 100 * (b.wer_full[e.config_id] - e.wer_without)
        lines.append(
            f"| `{e.rule}` | {e.config_id} | {_pct(e.wer_without)} | {change:+.2f} pp | "
            f"{e.utts_helped} / {e.utts_hurt} | {e.errors_removed} / {e.errors_added} |"
        )
    first = b.configs[0]
    lines += ["", f"## Examples ({first}; most errors removed first)", ""]
    for e in b.effects:
        if e.config_id != first:
            continue
        lines += [f"### `{e.rule}`", ""]
        if not e.examples:
            lines += ["No utterance changes.", ""]
            continue
        lines += [
            "| Utterance | Errors with / without | Ref (with rule) | Hyp (with rule) | "
            "Ref (without) | Hyp (without) |",
            "|---|---|---|---|---|---|",
        ]
        lines += [
            f"| `{x.utt_id}` | {x.errors_with} / {x.errors_without} | {_cell(x.ref_with)} | "
            f"{_cell(x.hyp_with)} | {_cell(x.ref_without)} | {_cell(x.hyp_without)} |"
            for x in e.examples
        ]
        lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    # Imported here so the module stays importable without the report's dependencies.
    from harness.report import DEFAULT_REGISTRY, registry_hyp_date_orders

    parser = argparse.ArgumentParser(description="Per-rule equivalence-layer diagnostic")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    runs = read_runs(args.results)
    b = breakdown(
        read_manifest(args.manifest),
        runs,
        hyp_date_orders=registry_hyp_date_orders(args.registry, runs),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(b, label=args.manifest.as_posix()) + "\n", encoding="utf-8")
    print(f"breakdown -> {args.out}")


if __name__ == "__main__":
    main()
