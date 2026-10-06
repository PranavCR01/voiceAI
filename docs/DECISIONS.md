# Decisions

Newest first. Each entry: date, decision, reason, what it replaced (if anything).

## 2026-10-06 — Scenario is healthcare patient intake
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
