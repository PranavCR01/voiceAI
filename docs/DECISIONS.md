# Decisions

Newest first. Each entry: date, decision, reason, what it replaced (if anything).

## 2026-10-06 — Equivalence layer v2: work around Whisper's digit handling
Found while designing entity tagging: Whisper's normalizer rewrites the digit 1 as "one" (`1.5` → `one.5`, `5 1 5` → `5 one 5`, `2.1` → `2 one`), drops leading zeros (`07700` → `7700`, while spoken "oh seven seven…" keeps them), turns "zero point five" into `.5`, and deletes parenthesized text (the `(555)` area code). Each would corrupt dosage and phone-number scoring. v2 adds, each with a fixture:
- Before Whisper: digits in parentheses are unwrapped; numbers with a leading zero are spelled digit by digit so Whisper rebuilds them with the zero.
- After Whisper: `one.N` → `1.N`, `.N` → `0.N`, `one` next to a digit group → `1`; runs of digit groups totalling ≥7 digits, or ≥3 single digits, are joined into one token (grouping of phone/account numbers is formatting). Two-token runs under 7 digits are not joined (`10 1` could be "10, 1").
Known remaining: `2.1` loses its decimal point inside Whisper (`2 1`) identically on both sides, so it is still equal; "half a" is not 0.5.
Replaces: equivalence layer v1 (entry below); normalizer id changes from `equiv-v1` to `equiv-v2`.

## 2026-10-06 — Statistics conventions
- Pooled-WER intervals: paired percentile bootstrap (default 10,000 resamples, 95%). All systems share the same resample weights, so differences are paired. With `cluster_ids` (speakers), whole clusters are resampled; use it whenever a speaker contributes many utterances, since iid resampling understates uncertainty when difficulty clusters by speaker (a test shows the clustered interval is >1.5x wider on such data).
- Bootstrap p-value: two-sided, 2 x min(share of resampled differences <= 0, share >= 0), with the +1 correction ((count + 1)/(B + 1)) so it is never reported as 0; capped at 1. Identical systems give p = 1.
- Resamples that draw only empty references (possible only when some references are empty) are dropped and counted in `dropped_resamples`.
- "Distinguishable" means the difference interval strictly excludes 0; touching 0 is a tie.
- Proportions use the Wilson score interval; the normal quantile comes from the stdlib (`statistics.NormalDist`), so no SciPy dependency.
- Holm step-down adjusts p-values when many pairwise claims are made at once.

## 2026-10-06 — Equivalence layer on top of Whisper normalization
Headline WER uses Whisper normalization **plus** a small, versioned equivalence layer (`EQUIVALENCE_VERSION`, id from `normalizer_id()`); plain-Whisper WER is kept as a second column for comparability with public leaderboards. Reason: a provider that formats "10 mg" should not lose to one that writes "ten milligrams" against a spoken reference. Rules (all domain-neutral, each with a fixture):
- Unit abbreviations ↔ spelled units (mg, mcg/µg, ml, kg, km; US and UK spellings).
- Numeric dates (`03/04/1980`, `03-04-1980`; same separator twice, `/` or `-` only) → month name. Day/month order is a parameter (`mdy` default, `dmy` for UK-style references); it is part of the normalizer id. The runner should derive it from the profile/dataset locale.
- Ordinal suffixes dropped (`3rd` → `3`), so "march 3rd" equals "03/03".
- `O.K.` / `ok` → `okay` (Whisper alone turns `O.K.` into `0 k`).
Rejected: joining hyphenated words to equate `co-pay`/`copay`. It broke the more common hyphen-vs-space case (`follow-up`/`follow up`), which Whisper already equates. A test enforces that the layer never separates a pair Whisper equates.
Still not equated (recorded as KNOWN MISMATCH): hyphenated vs closed compounds, day-first dates under `mdy`, word-order differences (correctly), synonyms (correctly). Digit-by-digit speech collapsing to one token (`one two three four` → `1234`) is handled in entity scoring (#7) with a character-level rate, not here.

## 2026-10-06 — WER normalization and empty references
- Normalizer: `whisper-normalizer` (standalone port of OpenAI Whisper's `EnglishTextNormalizer`; avoids pulling in torch). Version pinned in `uv.lock`; exposed as `WHISPER_ID`, and the full id including the equivalence layer comes from `normalizer_id()`. Being a third-party port, it could diverge from OpenAI's; the fixture table pins its behavior.
- Transcriber markup (`<TAG>…</TAG>`, `<TAG/>`) is stripped generically before normalization: paired tags keep their inner text, self-closing tags are dropped. Utterances that shouldn't be scored at all are excluded by the loader (`exclude_reason`), not by the normalizer.
- Empty reference: excluded from mean per-utterance WER (undefined), but its insertions count in pooled WER (hallucinated speech on silence is a real error). Pooled/mean raise if nothing is scorable.

## 2026-10-06 — Profile schema and reference-suite matching
- Relative paths in a profile resolve against the profile file's directory (portable: a customer profile folder can carry its own lexicons and manifests).
- Entity categories are compared by **signature**: builtin type for builtins, name for lexicon/regex. So `date_of_birth` and `due_date` both count as `date`.
- Matching rule: rank suites by (channel supported, languages shared, entity signatures covered), highest first; ties go to the alphabetically first `suite_id`. A match is a proxy unless the suite supports the channel, *every* profile language and *every* entity signature — partial language coverage (e.g. en-US + es-US against an English-only suite) is a proxy.
- `min_entity_recall` keys must name defined entities (catches typos that would silently drop a constraint). `min_check_pass_rate` keys are not checked yet; they're validated against conversation scripts in M3.
- Seed lexicons (`data/lexicons/*.txt`) are placeholders so the example profiles load; #7 builds the real medication lexicon.

## 2026-10-06 — Manifest schema is strict
`Utterance` rejects unknown fields and is immutable; `start_s`/`end_s` are both set or both None; `parent_utt_id` is required exactly when `augmentation` is non-empty; `audio_path` must be relative to the data root. Reason: every loader, augmenter and provider adapter shares this format, so silent shape drift would corrupt comparisons; failing at load time is cheaper than a wrong WER table. Schema doc: `harness/datasets/README.md`.

## 2026-10-06 — Recommend the whole cascaded stack, in a single version
The tool recommends STT, turn detection, LLM and TTS (plus settings), and the assembled stack is re-checked end to end. There is no v1/v2 split; previously deferred items become "stretch, after M7". LLM is scored by deterministic rule checks on scripted conversations (the LLM is tested, never the judge); TTS by TTFB, round-trip WER through a fixed different-vendor STT, entity pronunciation and UTMOS, with a small human listening test used only to validate UTMOS. Speech-to-speech models are excluded (a third architecture). Reason: owner wants a full-stack recommendation. Cost: estimate grows from ~5 to ~8–10 weeks; mitigated by milestones that each end in a demo.
Replaces: "v1 recommends STT/turn detection only" (in the entry below) and the "v1 scope cut" deferral list.

## 2026-10-06 — Commit directly to main
Solo project, one session at a time: a PR adds a click without adding review. CI runs on push to `main`; checks are run locally before every push. Branch + PR only when sessions run in parallel. Cloud sessions are assigned their own branch, so start each with "push to main when done".
Replaces: "Branch per issue, squash-merge to main" (below).

## 2026-10-06 — Branch per issue, squash-merge to main *(superseded above)*
Owner is the only contributor, but parallel Claude Code sessions, CI-before-merge and a reviewable diff per issue justify one branch + PR per issue. Owner merges (squash) and deletes the branch. `main` is the default branch.

## 2026-10-06 — The tool is a general recommender; healthcare is the first reference use case
Input is a use-case profile (use case, constraints, domain terms, optional customer audio); output is a recommended STT model + settings + turn-detection policy with intervals and "breaks at" thresholds. Two modes: customer audio (high confidence) and no audio (falls back to the closest built-in reference suite, labeled as proxy). Healthcare intake is the first reference suite and the demo agent. Reason: the owner's intent is a tool any FDE can point at any use case. A constraints-only recommender without measurement is just a filtered leaderboard, which already exists, so measurement on the customer's audio stays central.
v1 recommends STT model/settings/turn detection only; LLM and TTS are measured as latency/cost contributors but not recommended (v2: needs task evals and listening tests).
Replaces: "Scenario is healthcare patient intake" (below), which framed the whole tool as healthcare-specific.

## 2026-10-06 — Scenario is healthcare patient intake *(superseded above: healthcare is now the first reference use case, not the scope)*
Fictional clinic intake/appointment line. Reason: PriMock57 gives openly licensed (CC BY 4.0, verified on the repo LICENSE.md) medical conversation audio with timed utterance transcripts; medication/dosage entity scoring is the most persuasive metric in the research. Replaced: loan-servicing / collections agent.
Known weakness: PriMock57 is mock GP consultations with UK accents, not intake phone calls. It's a proxy; the memo says so.

## 2026-10-06 — Harness is the backbone, agent is the scenario
The STT bake-off/recommendation harness is the product. The intake agent exists to measure in-pipeline metrics (TTFA, endpointing, barge-in) and to be the demo. Replaced: two competing framings (agent-with-evals vs vendor harness).

## 2026-10-06 — v1 scope cut
Keep: 4 provider configs, 5 dataset groups + telephony/noise variants, WER + entity + streaming + endpointing + in-pipeline metrics, one memo. Defer to v2: Parakeet/GPU, 20-stream load, Opus packet loss, TTS scoring, self-recorded set. Reason: full research plan exceeds 4–5 weeks for a first voice agent build.

## 2026-10-06 — Pipecat, with two hand-built pieces
Pipecat (pinned) for transport and provider plumbing. Hand-built: (1) turn-taking/barge-in controller with event tracing, (2) one raw-WebSocket streaming STT client. Reason: framework keeps every layer visible without weeks of audio plumbing; the hand-built pieces are where depth shows. Controller policy logic is pure Python, unit-tested on recorded event traces, so framework upgrades don't silently break it.

## 2026-10-06 — Pooled WER is the headline WER
Pooled = total errors / total reference words. Per-utterance mean is reported alongside. Reason: per-utterance mean overweights short turns, which dominate voice-agent audio.

## 2026-10-06 — No LLM in scoring or recommendation
Semantic/LLM-judged WER is non-deterministic and conflicts with a reproducible recommendation. May appear later only as a clearly labeled secondary column.

## 2026-10-06 — Recommender treats overlapping CIs as ties
Hard-filter on constraints using CI bounds (e.g. upper 95% bound of p95 TTFA must be under budget), then rank survivors; ties broken by cost, then p95 latency. It may answer "not distinguishable".

## 2026-10-06 — Open corpora only; no social-video audio
YouTube/TikTok/Instagram terms bar downloading/scraping; no ground-truth transcripts; redistribution risk. Publish manifests and augmentation recipes, never audio.

## 2026-10-06 — Repo is the only source of truth
Decisions made in chat don't exist until written here or in an issue.
