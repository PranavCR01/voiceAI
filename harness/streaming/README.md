# Streaming traces

Every streaming adapter (#18) and the hand-written client (#19) records one `SessionTrace` per (config, utterance), and all latency metrics are computed from traces afterwards (`harness/metrics/latency.py`). Code: `trace.py`.

## File format
`<run>/traces/<trace_filename(utt_id)>.jsonl`: line 1 is `SessionMeta`, each later line one `Event`, in time order.

### SessionMeta
| Field | Meaning |
|---|---|
| `config_id`, `utt_id` | Which configuration and utterance. |
| `chunk_ms` | Audio chunk size used by the pacer. |
| `finalization_mode` | `natural` (provider endpointing decides) or `forced` (we send the provider's explicit finalize when the paced audio reaches the true speech end). |
| `finalize_supported` | False when the provider has no explicit finalize; forced-mode metrics then read "not supported". |
| `speech_start_ms`, `speech_end_ms` | Ground truth in audio time (#15). |
| `rtt_ms` | Network round-trip probe to the endpoint, so geography isn't mistaken for model speed. |

### Event
`t_ns` is monotonic-clock time since session start. Kinds:

| Kind | Recorded when | Extra fields |
|---|---|---|
| `connect_start` / `connect_ready` | Connection opened / ready to accept audio | |
| `audio_sent` | A chunk was sent (use the pacer's `sent_ns`, or better, the time right after the socket write) | `chunk_index`, `audio_offset_ms` |
| `audio_end` | Last audio chunk (incl. trailing silence) sent | |
| `finalize_sent` | Forced mode: explicit finalize sent | `audio_offset_ms` it was sent at, `raw` (the message) |
| `partial` / `final` | Provider transcript messages | `text`, `raw`; finals also `words` (word, `start_ms`, `end_ms` in *audio* time) whenever the provider returns word timings |
| `endpoint` | Provider end-of-turn signal (speech_final, utterance end, end of turn) | `raw` |
| `vad_event` | Provider speech start/end events, if any | `raw` |
| `error`, `closed` | Errors and session close | `raw` |

Use `Recorder` during a live session: `start()`, then `record(kind, at_ns=..., **fields)`.

## Metrics (per session)
- **connection setup** = `connect_ready − connect_start`; never folded into speech latency.
- **first partial** = first `partial` − send time of the chunk containing speech onset.
- **TTFS** = arrival of the final containing the speaker's last word − send time of the chunk containing speech end. With word timings, the last word is the latest-ending word among those ending within 300 ms of the true speech end, and the first final containing it counts; so a trailing final transcribed from silence ("um" two seconds later) or a re-sent final doesn't make a provider look slower. Without word timings it falls back to the last final after the anchor. Each TTFS records its `basis` (`word_timestamps` or `last_final`), and summaries count sessions per basis.
- **finalize latency** (forced) = first `final` after `finalize_sent` − `finalize_sent`.
- **endpoint delay** (natural) = first `endpoint` at/after the speech-end anchor − anchor; endpoints before it are counted as premature (rates in #20).

Statuses: `ok`, `timeout`, `not_applicable`, `not_supported`, `missing_ground_truth`. Aggregates (`summarize`) report p50/p95/p99 with bootstrap CIs, treating timeouts as +inf, plus the timeout rate. Pass `clusters` (utt_id → speaker) to resample whole speakers, as the WER intervals do; the summary then reports `cluster_effect`, the clustered p50 interval width divided by the iid one (≈1: speakers don't matter; well above 1: they do, and iid intervals would have been too narrow).

## Provider message mapping
Filled in per provider by #18 (which vendor flag becomes `partial` / `final` / `endpoint`).
