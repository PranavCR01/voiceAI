# Use-case profiles

A profile is the recommender's input: what the voice agent is for, what it must achieve, and which entities matter. Load with `recommender.profile.load_profile(path)`. Relative paths inside a profile resolve against the profile file's directory.

Examples: `healthcare_intake.yaml` (reference use case), `utility_billing_support.yaml` (proves the format isn't healthcare-shaped).

## `use_case` (required)
| Field | Type | Notes |
|---|---|---|
| `name`, `domain` | str | Free text. |
| `channel` | `telephony_8k` \| `wideband_16k` | Drives augmentation and suite matching. |
| `languages` | list of BCP-47 tags, ≥1 | e.g. `en-US`. Matching uses the primary subtag (`en`). |
| `expected_accents` | list[str] | Optional, informational for now. |
| `avg_call_minutes` | float > 0 | Cost modeling. |
| `agent_talk_ratio` | 0–1 | Share of call time the agent speaks; matters for session-billed STT. |

## `constraints` (all optional; absent = unconstrained)
| Group | Fields |
|---|---|
| `stack` | `max_p95_ttfa_ms`, `max_cost_per_min_usd`, `min_task_success_rate` (0–1), `require_baa` (bool), `data_residency` (list), `deployment` (`managed` \| `self_hosted` \| `either`, default `either`), `min_concurrency` (≥1) |
| `stt` | `min_entity_recall` (entity name → 0–1; names must be defined in `entities`), `max_wer` (0–1) |
| `turn_taking` | `max_premature_endpoint_rate` (0–1), `max_p95_endpoint_delay_ms` |
| `llm` | `min_check_pass_rate` (check name → 0–1; check names defined by the conversation scripts in M3), `max_p95_ttft_ms`, `require_tool_calling` (bool) |
| `tts` | `max_p95_ttfb_ms`, `max_roundtrip_wer` (0–1), `min_entity_pronunciation` (0–1), `voice` (free-text tags) |

## `entities`
List of categories; names are lowercase snake_case and unique. Each has a `kind` and exactly the matching source field:
- `lexicon` + `lexicon_path`: one term per line, `#` comment lines and blanks ignored, lowercased.
- `regex` + `pattern`: must compile.
- `builtin` + `builtin`: one of `number`, `date`, `dosage`, `phone`, `duration`.

A category's **signature** is its builtin type (so `date_of_birth` and `due_date` both have signature `date`) or, for lexicon/regex, its name. Suite matching compares signatures.

## Other fields
- `keyterms`: explicit STT boost list. If absent, `keyterm_list()` uses every lexicon term.
- `conversation_scripts`: path to scripted conversations for LLM checks (format defined in M3).
- `audio.manifest_path`: customer audio manifest (`harness/datasets/README.md`). Absent → no-audio mode.
- `reference_suite`: force a suite instead of matching.

`load_profile` fails if any referenced file is missing. Unknown fields are rejected everywhere.

## Reference suite matching
`recommender.suites.match_reference_suite(profile)` ranks registered suites by (channel supported, languages shared, entity signatures covered), highest first; ties go to the alphabetically first `suite_id`. The result is a **proxy** match unless the suite supports the profile's channel, every profile language and every entity signature. Every match carries human-readable reasons for the memo.
