"""Seeded per-speaker samples of a manifest, for runs too slow to cover every utterance.

A streaming session takes real time (the clip plus trailing silence), so a latency run on all
5,255 PriMock57 utterances would take ~8 h per config and mode. A sample keeps every speaker
(latency CIs are speaker-clustered) with a few utterances each.

Selection is deterministic and independent of manifest order, platform and Python version:
within each speaker, eligible utterances are ranked by sha256("<seed>:<utt_id>") and the first
`per_speaker` are taken (all of them when a speaker has fewer). Adding utterances for one speaker
never changes another speaker's picks. Eligible = not excluded, in `subset` when one is given,
and with a VAD speech end (#15) when speech spans are given, because both TTFS and forced
finalization anchor on it; so natural and forced runs of a sample cover the same utterances.

The spec plus a hash of the chosen ids is stored in `RunMeta.sample`, so a resumed run or a
run on another machine can be checked to have used the same utterances.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from harness.datasets.manifest import Utterance
from harness.vad import SpeechSpan


class SampleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subset: str | None = None
    per_speaker: int | None = Field(default=None, gt=0)
    seed: int = 0


def _rank(seed: int, utt_id: str) -> str:
    return hashlib.sha256(f"{seed}:{utt_id}".encode()).hexdigest()


def ids_digest(utt_ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(utt_ids)).encode()).hexdigest()


def sample_utterances(
    manifest: Sequence[Utterance],
    spec: SampleSpec,
    spans: Mapping[str, SpeechSpan] | None = None,
    *,
    include_excluded: bool = False,
) -> list[Utterance]:
    """The sampled utterances, in manifest order."""
    eligible = [
        u
        for u in manifest
        if (include_excluded or u.exclude_reason is None)
        and (spec.subset is None or u.subset == spec.subset)
        and (spans is None or (u.utt_id in spans and spans[u.utt_id].speech_end_ms is not None))
    ]
    if spec.per_speaker is None:
        return eligible
    by_speaker: dict[str, list[Utterance]] = {}
    for u in eligible:
        by_speaker.setdefault(u.speaker_id, []).append(u)
    chosen = {
        u.utt_id
        for utts in by_speaker.values()
        for u in sorted(utts, key=lambda u: _rank(spec.seed, u.utt_id))[: spec.per_speaker]
    }
    return [u for u in eligible if u.utt_id in chosen]


def sample_record(
    spec: SampleSpec, chosen: Sequence[Utterance], *, vad_filtered: bool
) -> dict[str, JsonValue]:
    """What a run stores in `RunMeta.sample`."""
    return {
        **spec.model_dump(),
        "requires_speech_end": vad_filtered,
        "utterances": len(chosen),
        "speakers": len({u.speaker_id for u in chosen}),
        "utt_ids_sha256": ids_digest([u.utt_id for u in chosen]),
    }
