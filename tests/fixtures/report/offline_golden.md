# Offline STT accuracy report

- **Generated:** 2026-10-06 12:00 UTC
- **Manifest:** `tests/fixtures/report/manifest.jsonl` (9 utterances; excluded from scoring: unintelligible 1)
- **Profile:** `configs/profiles/healthcare_intake.yaml`
- **Normalizer (headline WER):** `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy`, `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/mdy`
- **Leaderboard-comparable WER:** `whisper-normalizer==0.1.15/EnglishTextNormalizer`
- **Intervals:** 95% paired percentile bootstrap, 2000 resamples, seed 0, resampling whole speakers. Pairwise p-values Holm-adjusted within each table. "Tie" = difference interval includes 0. No winner is called with fewer than 10 speakers in a table.
- **Failed requests** are scored as empty transcripts (every reference word deleted).
- **Empty on speech:** successful requests that returned no text although the normalized reference has words (Wilson interval, not clustered). An empty transcript for "Um." is correct and not counted. These rows are scored as they came back, never selectively re-run.

## Configurations

| Config | Provider | Model | Mode | Settings | Hyp. dates | Run | Recorded | Git |
|---|---|---|---|---|---|---|---|---|
| fake_a | Fake Provider A | `fake-a-2026-10` | batch | `{"smart_format": true}` | as reference | run-a | 2026-10-06 | `0123456` |
| fake_b | Fake Provider B | `fake-b-v3` | batch | `{"keyterms": "profile"}` | as reference | run-b | 2026-10-06 | `fedcba9` |

## Real audio

### All real audio

4 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| fake_a | 2.3% [0.0, 4.9] | 6.8% | 1.9% | 6 | 43 | 0 | 0.0% [0.0, 39.0] (0/6) |
| fake_b | 20.9% [0.0, 50.0] | 20.5% | 27.1% | 6 | 43 | 1 | 0.0% [0.0, 43.4] (0/5) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| fake_a − fake_b | -18.6 pp [-50.0, +4.0] | 0.2479 | 0.2479 | too few speakers (4) to call |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| fake_a | medication | 100.0% [43.9, 100.0] | 3/3 | 0.0% | - |
| fake_a | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| fake_a | date_of_birth | 100.0% [20.7, 100.0] | 1/1 | 0.0% | 100.0% [20.7, 100.0] |
| fake_a | phone | no instances | 0 | - | - |
| fake_b | medication | 66.7% [20.8, 93.9] | 2/3 | 20.7% | - |
| fake_b | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| fake_b | date_of_birth | 100.0% [20.7, 100.0] | 1/1 | 0.0% | 0.0% [0.0, 79.3] |
| fake_b | phone | no instances | 0 | - | - |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): fake_a 0, fake_b 0.

### doctor (real)

2 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| fake_a | 0.0% [0.0, 0.0] | 0.0% | 0.0% | 2 | 11 | 0 | 0.0% [0.0, 65.8] (0/2) |
| fake_b | 18.2% [0.0, 50.0] | 18.2% | 25.0% | 2 | 11 | 0 | 0.0% [0.0, 65.8] (0/2) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| fake_a − fake_b | -18.2 pp [-50.0, +0.0] | 0.5087 | 0.5087 | too few speakers (2) to call |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| fake_a | medication | 100.0% [20.7, 100.0] | 1/1 | 0.0% | - |
| fake_a | dosage | no instances | 0 | - | - |
| fake_a | date_of_birth | no instances | 0 | - | - |
| fake_a | phone | no instances | 0 | - | - |
| fake_b | medication | 0.0% [0.0, 79.3] | 0/1 | 60.0% | - |
| fake_b | dosage | no instances | 0 | - | - |
| fake_b | date_of_birth | no instances | 0 | - | - |
| fake_b | phone | no instances | 0 | - | - |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): fake_a 0, fake_b 0.

### patient (real)

2 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| fake_a | 3.1% [0.0, 5.6] | 9.1% | 2.8% | 4 | 32 | 0 | 0.0% [0.0, 49.0] (0/4) |
| fake_b | 21.9% [0.0, 50.0] | 21.2% | 28.1% | 4 | 32 | 1 | 0.0% [0.0, 56.1] (0/3) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| fake_a − fake_b | -18.8 pp [-50.0, +5.6] | 0.5127 | 0.5127 | too few speakers (2) to call |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| fake_a | medication | 100.0% [34.2, 100.0] | 2/2 | 0.0% | - |
| fake_a | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| fake_a | date_of_birth | 100.0% [20.7, 100.0] | 1/1 | 0.0% | 100.0% [20.7, 100.0] |
| fake_a | phone | no instances | 0 | - | - |
| fake_b | medication | 100.0% [34.2, 100.0] | 2/2 | 0.0% | - |
| fake_b | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| fake_b | date_of_birth | 100.0% [20.7, 100.0] | 1/1 | 0.0% | 0.0% [0.0, 79.3] |
| fake_b | phone | no instances | 0 | - | - |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): fake_a 0, fake_b 0.

## Synthetic audio (TTS-generated; not comparable to real audio)

### All synthetic audio

2 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| fake_a | 0.0% [0.0, 0.0] | 0.0% | 0.0% | 2 | 13 | 0 | 0.0% [0.0, 65.8] (0/2) |
| fake_b | 23.1% [16.7, 28.6] | 35.7% | 22.6% | 2 | 13 | 0 | 0.0% [0.0, 65.8] (0/2) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| fake_a − fake_b | -23.1 pp [-28.6, -16.7] | 0.0010 | 0.0010 | too few speakers (2) to call |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| fake_a | medication | 100.0% [20.7, 100.0] | 1/1 | 0.0% | - |
| fake_a | dosage | 100.0% [20.7, 100.0] | 1/1 | 0.0% | 100.0% [20.7, 100.0] |
| fake_a | date_of_birth | no instances | 0 | - | - |
| fake_a | phone | 100.0% [20.7, 100.0] | 1/1 | 0.0% | 100.0% [20.7, 100.0] |
| fake_b | medication | 100.0% [20.7, 100.0] | 1/1 | 0.0% | - |
| fake_b | dosage | 100.0% [20.7, 100.0] | 1/1 | 0.0% | 100.0% [20.7, 100.0] |
| fake_b | date_of_birth | no instances | 0 | - | - |
| fake_b | phone | 0.0% [0.0, 79.3] | 0/1 | 9.1% | 0.0% [0.0, 79.3] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): fake_a 0, fake_b 1.

## Worst utterances

Normalized alignment: `[ref→hyp]` substitution, `[-ref]` deletion, `[+hyp]` insertion. Top 10 by error count per config.

### fake_a

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `fixture:p2` | patient | 1/9 | my date of birth is [-the] march 3 1980 |

### fake_b

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `fixture:p4` | patient | 6/6 | [-it] [-started] [-about] [-3] [-days] [-ago] |
| `fixture:d1` | doctor | 2/4 | any allergies to [+penny] [penicillin→selin] |
| `fixture:s2` | intake_script | 2/7 | i take ibuprofen [+and] [+metformin] 400 mg as needed |
| `fixture:p3` | patient | 1/8 | 2 puffs of ventolin when i am [wheezy→weezy] |
| `fixture:s1` | intake_script | 1/6 | you can reach me on [07700900123→07700900124] |
