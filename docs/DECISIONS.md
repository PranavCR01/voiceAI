# Decisions

Newest first. Each entry: date, decision, reason, what it replaced (if anything).

## 2026-11-04 — "Empty on speech" metric; runner flags `suspect_empty`
- **Definition:** a successful request whose raw hypothesis is blank while the *normalized* reference has words (`harness.metrics.wer.empty_on_speech`). Rate = those / successful requests on references with words, Wilson 95% interval (not speaker-clustered). Failed requests are excluded here because they already count in "Failed".
- **The proposed definition ("an empty hyp on a non-empty reference") overcounts by 2.5×.** Whisper drops fillers, so 88 of the 145 empty hypotheses in the plain run are on references like "Mm.", "Um", "<UNSURE>Um</UNSURE>", where empty is correct. Real rate on PriMock57: plain 1.1% [0.9, 1.4] (57/5,105), keyterms 1.2% [1.0, 1.6] (63/5,105); patient side 1.6–1.8%, doctor 0.6–0.7%. Most are 1-word backchannels ("Yeah", "Okay"); about 7–9 per config are 3+ words, e.g. the 11-word sentence in the #13 entry below.
- **Runner:** sets `ResultRow.suspect_empty` with the same predicate, counts it in the run summary, and never retries those rows (retrying only the bad rows would be cherry-picking; `--retry-failed` leaves them alone). Runs recorded before today have no column and read as False. The report recomputes from text, so old runs score the same.
- An agent hears silence on these turns, so for turn-taking this is a missed turn, not just WER. Reported per config so provider differences show up once more vendors run.

## 2026-11-04 — Dates: provider output order + spoken day-month order (equivalence v3)
DOB recall on PriMock57 was 2/21 for both Deepgram configs; it is now 17/21 (81.0% [60.0, 92.3]). The 4 still missed are real: wrong month (November → June), wrong day (22 → 27), and two references whose transcript has no day while Deepgram wrote one.
- **The fix proposed in the #13 entry below (read hypothesis dates month-first) was necessary but not sufficient: on its own it moves DOB recall from 2/21 to 2/21.** Most misses were word order: people say "the twentieth of April", formatters write "April 20, 1980", so a correct date cost two errors. Both changes were needed.
- **Hypothesis date order per provider config.** New registry field `output_date_order` (`mdy`/`dmy`/unset = same as the reference). References are still read by manifest `language`. Both Deepgram batch configs are `mdy`: `smart_format` writes `04/20/1980` for en-GB audio, and `language=en-GB` doesn't change it (observed 2026-11-04, not from docs). Ambiguous digits (05/06/1990) follow the stated order, never a guess. The report reads the registry (`--registry`, default `configs/providers.yaml`), shows a "Hyp. dates" column, and the normalizer id records both orders when they differ (`.../equiv-v3/dmy,hyp-mdy`).
- **Equivalence v3: "D [of] MONTH" → "MONTH D"**, on both sides, plus "MONTH one" → "MONTH 1" (Whisper spells a lone 1). "may"/"march" count as months only after "of" or before a 4-digit year, so "one may be late" and "we march 2 miles" are untouched (fixtures). Replaces, for dates only, "word-order differences are not equated" (equivalence v2 entry): this is the same convention gap the numeric-date rule already closes. Any other word order still counts. Side effect: the "of" is gone, so reference word counts fall slightly (PriMock57: 56,812 → 56,798) and pooled WER drops 0.1 pp (7.5% → 7.4%; patient 9.0% → 8.8%).
- Normalizer id changes from `equiv-v2` to `equiv-v3`; earlier reports are not comparable digit-for-digit.

## 2026-11-04 — Commit run results, not raw responses
`results/<run_id>/run.json` and `results.parquet` are tracked; everything else under `results/` (the `raw/` provider responses) stays local and ignored. Reason: cloud containers are reclaimed, and the scoring follow-ups to #13 (per-provider date order, empty-transcript rate, equivalence-rule breakdown) need the hypotheses to re-score without paying for new runs. The two Deepgram runs are ~600 KB together. Raw responses are kept out because they carry provider request ids and are ~46 MB uncompressed; the cost is that anything needing word timings or confidences (e.g. telling a provider's empty response apart from a correctly empty transcript) can't be recomputed from the repo. Replaced: all of `results/` gitignored.

## 2026-11-04 — First live Deepgram batch run (#13): how to read the numbers
Ran in a cloud session, not on the owner's machine: batch accuracy needs only the API key and audio, no latency or mic. Report: `reports/generated/primock57_batch.md` (both configs, 5,255 scorable utterances, 114 speakers, 0 failed). Read it with these caveats:
- **Keyterm gain is an oracle upper bound.** Medication recall goes 74.2% → 87.7% (121 → 143 of 163) with WER unchanged (tie, ±0.1 pp), and false keyterm insertions go 3 → 9. But the keyterm list is `data/lexicons/medications.txt`, built from drugs *observed in PriMock57*, so the model was told the test set's exact vocabulary. A real intake line won't know which drugs callers will say. Before the recommender uses this gain, rerun with a lexicon not derived from the test set (openFDA list, or held-out consultations).
- *(Fixed, see "Dates: provider output order" above.)* **Date-of-birth recall (9.5%) is a scoring artifact, not an STT result.** Deepgram transcribes the dates correctly, but `smart_format` writes them US-style (`04/20/1980`, `05/16/1982`, even with `language=en-GB`), and the `dmy` date normalizer reads those as different or invalid dates. Fix in the scorer: accept an all-digit date whose order is unambiguous (day > 12), and decide what to do with ambiguous ones. Until then, ignore the DOB row for any provider whose formatter writes dates as month-first digits.
- **Deepgram batch is not deterministic, and an empty 200 looks like a success.** The keyterms run returned an empty transcript (0 words, confidence 0.0, 6.4 s of speech) for `day1_consultation02:doctor:0047`; re-requested 3× with the same keyterms it came back correct. 8 utterances were empty only with keyterms and 5 only without, mostly backchannels. 412 of 5,255 transcripts differ between the two configs, and part of that is run-to-run noise of unknown size. So WER differences of ~0.1 pp between configs can't be attributed to the setting. Results were left as captured (no selective re-runs). Follow-ups: a test-retest run of one config to measure the noise floor, and making the runner flag empty transcripts on clips with speech as suspect.
- PriMock57 audio via `git lfs pull` is refused by the cloud git proxy; `data/fetch_primock57.sh` now falls back to GitHub's media host with sha256 checks.

## 2026-11-03 — TTFS from word timestamps; speaker-clustered latency intervals
Fixes two weaknesses of the first #14 implementation (entry below):
- **TTFS used the last final as "the final covering the last word"**, so a short trailing final transcribed from silence, or a re-sent final, made a provider look slower (a fixture showed 1,750 ms instead of 250 ms). Finals now carry word timings in audio time; the last word is the latest-ending word that ends within 300 ms of the true speech end, and TTFS is the arrival of the first final containing it. Without word timings it falls back to the last final, labelled `basis: last_final`, and summaries count sessions per basis, so a report can't silently mix the two. #18 adapters must keep word timings.
- **Latency intervals resampled sessions independently**, which was an untested assumption. `summarize(..., clusters=utt→speaker)` now resamples whole speakers (conservative; same rule as WER), and reports `cluster_effect`, the clustered/iid p50 interval-width ratio, so real data shows whether speaker clustering mattered. Simulated data with speaker effects gives a ratio > 2; independent data gives ≈ 1. Reports (#22) should cluster by default.

## 2026-11-03 — Streaming trace format and latency metrics
- One trace per session, all metrics computed afterwards from traces, so they are tested on hand-specified traces without a live provider. Schema: `harness/streaming/README.md`.
- Anchor: an audio moment (speech start/end from #15) maps to the time the chunk containing it was *sent*. A late chunk moves the anchor with it, so pacing jitter isn't charged to the provider.
- TTFS: see the entry above (word timestamps). Endpoint delay is natural-mode only; finalize latency is forced-mode only; endpoints before the anchor are counted as premature for #20.
- Timeouts are +inf in percentile aggregates, with the timeout rate beside them: if >5% of sessions never finalize, p95 reads as the timeout rather than a number computed over survivors. Percentiles use the `inverted_cdf` method (an observed value, no interpolation) so inf doesn't turn into NaN.
- Percentile intervals: see the entry above (speaker clustering).

## 2026-11-03 — Forced finalization as a separate latency; configurable host
- Prompted by an external comment on #20 (from someone who disclosed working for an STT vendor; the comment was later deleted). Judged on its merits:
- **Adopted:** measure finalize latency separately. In `forced` mode the adapter sends the provider's explicit finalize when the paced audio reaches the true speech end, and we time finalize → final. TTFS mixes model + network speed with the provider's endpointing policy; an agent with its own turn detector (our M5 controller) only needs the former, and the recommender scores STT and turn detection as separate layers. Providers without an explicit finalize show "not supported". Added to #14 and #18.
- **Adopted:** registry `base_url` (https only). The Deepgram adapter uses it, so any Deepgram-protocol endpoint (self-hosted, proxy, compatible vendor) is a registry entry; other adapters reject it. "Compatible" is checked per setting, never assumed.
- **Not adopted:** adding the commenter's own service as a fifth provider. No public footprint could be found, and providers are chosen by relevance to customers and hiring teams, not by request.

## 2026-10-06 — Batch adapters
- Plain `httpx`, no vendor SDKs: every request is visible and testable with a mock transport; no SDK version drift.
- Every provider receives the same 16 kHz mono WAV produced by `harness/audio.py`.
- Adapters reject settings they don't map (a typo can't become a silent default). Keyterm boosting is its own configuration (`*_keyterms`, `keyterms: profile` + `--profile`), so boosting is measured, never a hidden default.
- ElevenLabs audio-event tags are forced off (`tag_audio_events=false`).
- AssemblyAI is asynchronous (upload → create → poll); a poll timeout is retryable, a transcript `error` status is permanent.
- Written from recollection: vendor docs are blocked from the cloud environment. Request shapes and response fixtures are unverified; `harness/providers/README.md` holds the checklist, and the first live run must replace the fixtures with captured responses before results are trusted.

## 2026-10-06 — Audio I/O
- One decoding path (`harness/audio.py`) for adapters, augmentation and VAD, so every provider hears identical audio. Whole files are decoded once (ffmpeg → mono int16 at the target rate, cached) and segments are cut in NumPy: sample-exact for every format, where ffmpeg's own seeking isn't (MP3).
- The decoded file's real sample rate is recorded on every clip; a mismatch with the manifest warns (Common Voice's 48 kHz is an assumption until decoded).
- µ-law encoding is byte-identical to ffmpeg's `pcm_mulaw` over all 65,536 inputs (tested exhaustively). ffmpeg builds its encoder as a nearest-level lookup table rather than the Sun/ITU arithmetic; the two differ by one code at segment boundaries on 512 inputs. We match ffmpeg because the augmentation pipeline's telephony codec is ffmpeg, and two µ-law paths that disagree would make "telephony" mean two things.
- `pace()` schedules chunk k at t0 + k·chunk_ms on the monotonic clock (absolute deadlines), so a late chunk never shifts later ones; each chunk records scheduled and actual time, which the latency metrics use (#14). Wall-clock tests carry a `timing` marker (`pytest -m "not timing"` on a loaded machine).
- CI installs ffmpeg explicitly.

## 2026-10-06 — Provider registry and batch runner
- `configs/providers.yaml` holds one entry per *configuration* (provider + pinned model id + mode + settings). Prices carry `billing_basis` (audio vs session duration vs per channel), `source` and `as_of`, because the basis changes cost per conversation minute more than the headline rate. BAA status defaults to `unknown` and needs a source to be `yes`/`no`.
- Everything is `verify: true` until checked against vendor docs on the owner's machine; a verified entry must have a price. The CLI warns when running an unverified config.
- Batch and streaming configs are separate entries (`*_batch`, `*_stream`); batch exists to get a first real offline report quickly, and the report labels the mode.
- Runner: run id defaults to the config id so re-running resumes; results flushed every 20 utterances; failed requests recorded with the error and an empty transcript (scored as all-deletions by the report), skipped on resume unless `--retry-failed`. Retries only for `RetryableError` (429/5xx/timeouts), exponential backoff, 3 attempts. A resume refuses a run directory made with a different provider/model/settings.
- `git_sha` gets a `-dirty` suffix when the working tree has uncommitted changes, so a result can't silently claim a clean commit.

## 2026-10-06 — LibriSpeech and Common Voice loaders
- `audio_path` is computed relative to an explicit `--data-root`, so manifests stay portable regardless of where a dataset is unpacked.
- Common Voice is sampled, not loaded whole: 400 clips from the held-out `test.tsv` by default. Accents take turns (round robin) so the set measures *spread across accents*, not Common Voice's skewed population; WER on it is not an estimate of WER on "typical" Common Voice audio, and the report must not present it as one.
- The accent field has been free text since v8, so accents with fewer than 5 clips are pooled into one "other" stratum; otherwise hundreds of one-off strings would crowd out the main accents. Labels on clips are unchanged.
- At most 10 clips per speaker (`client_id`), so speaker clustering in the bootstrap has many clusters.
- Neither dataset can be fetched from the cloud environment (openslr.org blocked; Common Voice needs a terms acceptance), so both loaders are verified on fixtures that mirror the real layouts, including the pre-v8 `accent` column. The first real run on the owner's machine is the end-to-end check; expected counts are in `data/README.md`.
- Language tags: both `en` (no region), so numeric dates read month-first. LibriSpeech references contain no numeric dates; Common Voice sentences are rarely numeric.

## 2026-10-06 — Results format and offline report rules
- One run = one configuration. `<results>/<run_id>/run.json` (RunMeta: config, pinned model id, settings, date, git SHA) + `results.parquet` (one row per utterance: raw hypothesis, raw-response path, timestamps, error). Rows store the *raw* hypothesis; the normalizer id lives in the report header because normalization happens at scoring time (the issue asked for it per row; that would record a choice not yet made).
- Paired comparison: within each table, only utterances every run covers are scored; the number dropped is reported. A failed request is scored as an empty transcript (all deletions), never skipped, so unreliable providers aren't flattered.
- Real and synthetic audio are separate sections, never pooled. Each section has an "All" table plus one per subset when there are several.
- Intervals are speaker-clustered by default (`--cluster-by none` to resample utterances). Pairwise p-values are Holm-adjusted within each table.
- **No winner is called with fewer than 10 clusters** in a table ("too few speakers (n) to call"): with 2 speakers the bootstrap reported p = 0.001 on the fixture, which is meaningless. Ties and intervals are still shown.
- Headline WER (Whisper + equivalence layer) sits beside Whisper-only WER for leaderboard comparability; the per-utterance date order comes from the manifest `language`.
- Golden-file test pins the rendered report; regenerate deliberately with `UPDATE_GOLDEN=1 uv run pytest tests/test_report.py`. Scale check: PriMock57 (5,255 utterances, 2 configs, profile) renders in ~35 s.

## 2026-10-06 — PriMock57 loader choices
- Utterances containing `<UNIN/>` or the undocumented `<INAUDIBLE_SPEECH/>` are kept in the manifest but excluded from scoring: the reference is missing words there, so a provider that transcribes them would be charged insertions. This excludes 26% of utterances (1,853 of 7,108). They are likely the harder audio, so PriMock57 accuracy is optimistic relative to its full difficulty; the memo should say so. `<UNSURE>` spans are kept (inner text is the transcriber's best guess). No utterance is under the 0.3 s minimum.
- Seven known drug-name misspellings are corrected in `ref_text`, with the original in the new `ref_text_original` manifest field (5 utterances affected).
- New manifest field `language` (BCP-47). PriMock57 is `en-GB`, and `date_order_for(language)` turns that into day-first date reading, so the runner reads it from the data instead of having to remember it. Month-first: US-style regions and bare/missing tags; everything else day-first.
- Speaker IDs are `{consultation}_{role}`. Clinician identities aren't published, so the same doctor appears as several speakers and doctor-side speaker clustering understates correlation. Patients are 57 distinct actors. For the intake scenario the patient side is the caller, and it is unaffected.
- The generated manifest (3.7 MB of CC BY 4.0 text, no audio) is committed with attribution, so scoring and reports work without fetching the dataset; a test checks it stays valid and consistent with the correction map.

## 2026-10-06 — Entity scoring rules
- Tagging runs on the normalized reference so spans line up with the WER alignment. Recovery is strict (every token correct); a per-entity character error rate sits beside it so one wrong digit in a phone number isn't scored like a missing phone number.
- "Formatted" = recovered and the raw hypothesis carries the entity's numbers as digits. It measures downstream usability, separate from accuracy.
- The `number` builtin yields to every other category (drops overlapping spans), so a billing "amount" doesn't also count account numbers or the day in a date.
- Medication lexicon built from names observed in PriMock57 (49, hand-checked); openFDA merge deferred to the owner's machine because the cloud environment can't reach api.fda.gov. Reference misspellings (paracetemol, lisonopril…) are not lexicon terms; the PriMock57 loader (#5) should correct them, otherwise a provider that spells correctly is scored as wrong.
- PriMock57 alone has too few dosages (18), dates (21) and phones (0 real) for intervals. Synthetic intake scripts are required for those categories, not optional.
Rules in `harness/metrics/ENTITIES.md`.

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
- Seed lexicons (`data/lexicons/*.txt`) were placeholders so the example profiles load; #7 replaced the medication one with a list built from PriMock57 (the billing one remains a seed).

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
