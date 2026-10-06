# Decisions

Newest first. Each entry: date, decision, reason, what it replaced (if anything).

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
