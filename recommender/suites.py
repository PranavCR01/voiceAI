"""Built-in reference suites and the rule that matches a profile to one.

In no-audio mode the recommender measures on the closest reference suite instead of the
customer's audio. The match is deterministic and its reasons go into the memo.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from recommender.profile import Channel, Profile, ProfileError


class ReferenceSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    suite_id: str = Field(min_length=1)
    description: str
    channels: frozenset[Channel]
    languages: frozenset[str]  # primary subtags, e.g. "en"
    entity_signatures: frozenset[str]  # builtin types and named lexicon/regex categories


class SuiteMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    suite_id: str
    proxy: bool  # True when the suite does not cover everything the profile cares about
    reasons: list[str]


REFERENCE_SUITES: tuple[ReferenceSuite, ...] = (
    ReferenceSuite(
        suite_id="healthcare_intake",
        description="PriMock57 mock GP consultations + synthetic clinic intake scripts",
        channels=frozenset({Channel.TELEPHONY_8K, Channel.WIDEBAND_16K}),
        languages=frozenset({"en"}),
        entity_signatures=frozenset(
            {"medication", "dosage", "date", "phone", "duration", "number"}
        ),
    ),
)


def _primary(lang: str) -> str:
    return lang.split("-", 1)[0].lower()


def match_reference_suite(
    profile: Profile, suites: tuple[ReferenceSuite, ...] = REFERENCE_SUITES
) -> SuiteMatch:
    """Pick the suite that best fits the profile.

    Rule: rank by (channel supported, number of shared languages, number of covered entity
    signatures), highest first; ties go to the alphabetically first suite_id. The match is a
    proxy unless the suite supports the channel, every profile language and every profile
    entity.
    """
    if not suites:
        raise ProfileError("no reference suites registered")
    by_id = {s.suite_id: s for s in suites}
    profile_langs = {_primary(lang) for lang in profile.use_case.languages}
    wanted = {e.signature for e in profile.entities}

    if profile.reference_suite is not None:
        if profile.reference_suite not in by_id:
            raise ProfileError(
                f"reference_suite {profile.reference_suite!r} is not one of {sorted(by_id)}"
            )
        chosen = by_id[profile.reference_suite]
        reasons = ["set explicitly in profile"]
    else:

        def score(s: ReferenceSuite) -> tuple[bool, int, int]:
            return (
                profile.use_case.channel in s.channels,
                len(profile_langs & s.languages),
                len(wanted & s.entity_signatures),
            )

        chosen = sorted(suites, key=lambda s: (tuple(-int(x) for x in score(s)), s.suite_id))[0]
        reasons = [f"best of {len(suites)} suite(s) by channel, language, then entity coverage"]

    channel_ok = profile.use_case.channel in chosen.channels
    shared_langs = sorted(profile_langs & chosen.languages)
    missing_langs = sorted(profile_langs - chosen.languages)
    covered = sorted(wanted & chosen.entity_signatures)
    uncovered = sorted(wanted - chosen.entity_signatures)

    channel = profile.use_case.channel.value
    reasons.append(f"channel {channel} {'supported' if channel_ok else 'NOT supported'}")
    if shared_langs:
        reasons.append(f"languages shared: {', '.join(shared_langs)}")
    else:
        reasons.append(
            f"no shared language (profile: {sorted(profile_langs)}, "
            f"suite: {sorted(chosen.languages)})"
        )
    if shared_langs and missing_langs:
        reasons.append(f"languages NOT covered: {', '.join(missing_langs)}")
    if covered:
        reasons.append(f"entity categories covered: {', '.join(covered)}")
    if uncovered:
        reasons.append(f"entity categories NOT covered: {', '.join(uncovered)}")

    proxy = not channel_ok or bool(missing_langs) or bool(uncovered)
    if proxy:
        reasons.append(
            f"proxy match: {chosen.suite_id} audio stands in for this use case; "
            "results on it are lower confidence"
        )
    else:
        reasons.append(
            f"direct match: {chosen.suite_id} covers this use case's channel, language and entities"
        )
    return SuiteMatch(suite_id=chosen.suite_id, proxy=proxy, reasons=reasons)
