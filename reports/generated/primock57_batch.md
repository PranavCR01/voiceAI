# Offline STT accuracy report

- **Generated:** 2026-11-05 03:56 UTC
- **Manifest:** `data/manifests/primock57.jsonl` (7108 utterances; excluded from scoring: inaudible 706, unintelligible 1147)
- **Profile:** `configs/profiles/healthcare_intake.yaml`
- **Normalizer (headline WER):** `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy`, `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy,hyp-mdy`
- **Leaderboard-comparable WER:** `whisper-normalizer==0.1.15/EnglishTextNormalizer`
- **Intervals:** 95% paired percentile bootstrap, 10000 resamples, seed 0, resampling whole speakers. Pairwise p-values Holm-adjusted within each table. "Tie" = difference interval includes 0. No winner is called with fewer than 10 speakers in a table.
- **Failed requests** are scored as empty transcripts (every reference word deleted).
- **Empty on speech:** successful requests that returned no text although the normalized reference has words (Wilson interval, not clustered). An empty transcript for "Um." is correct and not counted. These rows are scored as they came back, never selectively re-run.

## Configurations

| Config | Provider | Model | Mode | Settings | Hyp. dates | Run | Recorded | Git |
|---|---|---|---|---|---|---|---|---|
| assemblyai_batch | assemblyai | `universal-3-5-pro` | batch | `{"format_text": true, "language_code": "en", "punctuate": true}` | as reference | assemblyai-batch | 2026-11-05 | `a0f7da9` |
| deepgram_nova3_batch | deepgram | `nova-3` | batch | `{"punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch | 2026-11-04 | `207cdd3` |
| deepgram_nova3_batch_keyterms | deepgram | `nova-3` | batch | `{"keyterms": "lexicon", "punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch-keyterms | 2026-11-04 | `8f09f37` |
| deepgram_nova3_batch_keyterms_common | deepgram | `nova-3` | batch | `{"keyterms": "profile", "punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch-keyterms-common | 2026-11-05 | `a0f7da9` |
| elevenlabs_scribe_v2_batch | elevenlabs | `scribe_v2` | batch | `{"language_code": "en", "temperature": 0}` | as reference | elevenlabs-scribe-v2-batch | 2026-11-05 | `beb7ab9` |
| elevenlabs_scribe_v2_batch_keyterms_common | elevenlabs | `scribe_v2` | batch | `{"keyterms": "profile", "language_code": "en", "temperature": 0}` | as reference | elevenlabs-scribe-v2-batch-keyterms-common | 2026-11-05 | `a0f7da9` |
| elevenlabs_scribe_v2_medical_batch | elevenlabs | `scribe_v2_medical` | batch | `{"language_code": "en", "temperature": 0}` | as reference | elevenlabs-scribe-v2-medical-batch | 2026-11-05 | `a0f7da9` |

## Real audio

### All real audio

114 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 6.6% [6.0, 7.1] | 9.3% | 10.5% | 5255 | 56795 | 0 | 0.4% [0.2, 0.6] (19/5105) |
| deepgram_nova3_batch | 7.4% [6.8, 8.1] | 10.2% | 12.2% | 5255 | 56795 | 0 | 1.1% [0.9, 1.4] (57/5105) |
| deepgram_nova3_batch_keyterms | 7.4% [6.8, 8.1] | 10.2% | 12.2% | 5255 | 56795 | 0 | 1.2% [1.0, 1.6] (63/5105) |
| deepgram_nova3_batch_keyterms_common | 7.4% [6.8, 8.1] | 10.3% | 12.3% | 5255 | 56795 | 0 | 1.2% [0.9, 1.5] (61/5105) |
| elevenlabs_scribe_v2_batch | 5.7% [5.1, 6.2] | 8.4% | 10.2% | 5255 | 56795 | 0 | 0.3% [0.2, 0.5] (17/5105) |
| elevenlabs_scribe_v2_batch_keyterms_common | 5.5% [5.0, 6.0] | 8.3% | 9.9% | 5255 | 56795 | 0 | 0.3% [0.2, 0.5] (15/5105) |
| elevenlabs_scribe_v2_medical_batch | 5.8% [5.3, 6.4] | 8.6% | 10.5% | 5255 | 56795 | 0 | 0.8% [0.6, 1.1] (43/5105) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -0.9 pp [-1.3, -0.5] | 0.0002 | 0.0042 | assemblyai_batch better |
| assemblyai_batch − deepgram_nova3_batch_keyterms | -0.9 pp [-1.3, -0.5] | 0.0002 | 0.0042 | assemblyai_batch better |
| assemblyai_batch − deepgram_nova3_batch_keyterms_common | -0.9 pp [-1.3, -0.5] | 0.0002 | 0.0042 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | +0.9 pp [+0.6, +1.2] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch_keyterms_common | +1.1 pp [+0.8, +1.4] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| assemblyai_batch − elevenlabs_scribe_v2_medical_batch | +0.7 pp [+0.4, +1.1] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms | +0.0 pp [-0.1, +0.1] | 0.9677 | 1.0000 | tie |
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms_common | -0.0 pp [-0.1, +0.0] | 0.6121 | 1.0000 | tie |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +1.8 pp [+1.4, +2.1] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch_keyterms_common | +1.9 pp [+1.6, +2.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_medical_batch | +1.6 pp [+1.3, +1.9] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| deepgram_nova3_batch_keyterms − deepgram_nova3_batch_keyterms_common | -0.0 pp [-0.1, +0.0] | 0.5647 | 1.0000 | tie |
| deepgram_nova3_batch_keyterms − elevenlabs_scribe_v2_batch | +1.8 pp [+1.4, +2.1] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch_keyterms − elevenlabs_scribe_v2_batch_keyterms_common | +1.9 pp [+1.6, +2.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| deepgram_nova3_batch_keyterms − elevenlabs_scribe_v2_medical_batch | +1.6 pp [+1.3, +1.9] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| deepgram_nova3_batch_keyterms_common − elevenlabs_scribe_v2_batch | +1.8 pp [+1.4, +2.2] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch_keyterms_common − elevenlabs_scribe_v2_batch_keyterms_common | +2.0 pp [+1.6, +2.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| deepgram_nova3_batch_keyterms_common − elevenlabs_scribe_v2_medical_batch | +1.6 pp [+1.3, +2.0] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| elevenlabs_scribe_v2_batch − elevenlabs_scribe_v2_batch_keyterms_common | +0.2 pp [+0.1, +0.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| elevenlabs_scribe_v2_batch − elevenlabs_scribe_v2_medical_batch | -0.2 pp [-0.3, +0.0] | 0.1020 | 0.4080 | tie |
| elevenlabs_scribe_v2_batch_keyterms_common − elevenlabs_scribe_v2_medical_batch | -0.3 pp [-0.5, -0.2] | 0.0004 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 84.7% [78.3, 89.4] | 138/163 | 7.1% | - |
| assemblyai_batch | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 87.5% [64.0, 96.5] |
| assemblyai_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.1% | 85.7% [65.4, 95.0] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 74.2% [67.0, 80.3] | 121/163 | 12.4% | - |
| deepgram_nova3_batch | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms | medication | 87.7% [81.8, 91.9] | 143/163 | 6.4% | - |
| deepgram_nova3_batch_keyterms | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch_keyterms | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch_keyterms | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms_common | medication | 73.6% [66.4, 79.8] | 120/163 | 11.5% | - |
| deepgram_nova3_batch_keyterms_common | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch_keyterms_common | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch_keyterms_common | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | medication | 82.8% [76.3, 87.8] | 135/163 | 8.6% | - |
| elevenlabs_scribe_v2_batch | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 18.8% [6.6, 43.0] |
| elevenlabs_scribe_v2_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 6.6% | 52.4% [32.4, 71.7] |
| elevenlabs_scribe_v2_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 13.3% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch_keyterms_common | medication | 87.7% [81.8, 91.9] | 143/163 | 5.9% | - |
| elevenlabs_scribe_v2_batch_keyterms_common | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 18.8% [6.6, 43.0] |
| elevenlabs_scribe_v2_batch_keyterms_common | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.1% | 47.6% [28.3, 67.6] |
| elevenlabs_scribe_v2_batch_keyterms_common | phone | 50.0% [9.5, 90.5] | 1/2 | 13.3% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_medical_batch | medication | 82.8% [76.3, 87.8] | 135/163 | 9.8% | - |
| elevenlabs_scribe_v2_medical_batch | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 25.0% [10.2, 49.5] |
| elevenlabs_scribe_v2_medical_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 6.6% | 42.9% [24.5, 63.5] |
| elevenlabs_scribe_v2_medical_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 1, deepgram_nova3_batch_keyterms 9, deepgram_nova3_batch_keyterms_common 4, elevenlabs_scribe_v2_batch 3, elevenlabs_scribe_v2_batch_keyterms_common 12, elevenlabs_scribe_v2_medical_batch 5.

### doctor (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 5.5% [4.9, 6.2] | 9.3% | 7.8% | 2615 | 33869 | 0 | 0.3% [0.1, 0.6] (7/2570) |
| deepgram_nova3_batch | 6.5% [5.7, 7.4] | 10.2% | 9.3% | 2615 | 33869 | 0 | 0.6% [0.4, 1.0] (16/2570) |
| deepgram_nova3_batch_keyterms | 6.6% [5.8, 7.5] | 10.3% | 9.3% | 2615 | 33869 | 0 | 0.7% [0.4, 1.1] (18/2570) |
| deepgram_nova3_batch_keyterms_common | 6.6% [5.8, 7.4] | 10.3% | 9.3% | 2615 | 33869 | 0 | 0.7% [0.4, 1.1] (17/2570) |
| elevenlabs_scribe_v2_batch | 4.7% [4.1, 5.5] | 8.5% | 7.3% | 2615 | 33869 | 0 | 0.1% [0.0, 0.3] (3/2570) |
| elevenlabs_scribe_v2_batch_keyterms_common | 4.6% [4.0, 5.3] | 8.4% | 7.2% | 2615 | 33869 | 0 | 0.1% [0.0, 0.3] (3/2570) |
| elevenlabs_scribe_v2_medical_batch | 5.0% [4.3, 5.6] | 8.8% | 7.4% | 2615 | 33869 | 0 | 0.4% [0.2, 0.7] (10/2570) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -1.0 pp [-1.5, -0.5] | 0.0004 | 0.0042 | assemblyai_batch better |
| assemblyai_batch − deepgram_nova3_batch_keyterms | -1.1 pp [-1.6, -0.6] | 0.0004 | 0.0042 | assemblyai_batch better |
| assemblyai_batch − deepgram_nova3_batch_keyterms_common | -1.1 pp [-1.6, -0.6] | 0.0004 | 0.0042 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | +0.8 pp [+0.4, +1.1] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch_keyterms_common | +0.9 pp [+0.6, +1.2] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| assemblyai_batch − elevenlabs_scribe_v2_medical_batch | +0.6 pp [+0.2, +0.9] | 0.0032 | 0.0224 | elevenlabs_scribe_v2_medical_batch better |
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms | -0.1 pp [-0.1, +0.0] | 0.2764 | 0.8291 | tie |
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms_common | -0.0 pp [-0.1, +0.0] | 0.3554 | 0.8291 | tie |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +1.8 pp [+1.3, +2.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch_keyterms_common | +1.9 pp [+1.4, +2.4] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_medical_batch | +1.6 pp [+1.2, +2.0] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| deepgram_nova3_batch_keyterms − deepgram_nova3_batch_keyterms_common | +0.0 pp [-0.1, +0.1] | 0.8981 | 0.8981 | tie |
| deepgram_nova3_batch_keyterms − elevenlabs_scribe_v2_batch | +1.8 pp [+1.3, +2.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch_keyterms − elevenlabs_scribe_v2_batch_keyterms_common | +1.9 pp [+1.4, +2.4] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| deepgram_nova3_batch_keyterms − elevenlabs_scribe_v2_medical_batch | +1.6 pp [+1.2, +2.0] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| deepgram_nova3_batch_keyterms_common − elevenlabs_scribe_v2_batch | +1.8 pp [+1.3, +2.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch_keyterms_common − elevenlabs_scribe_v2_batch_keyterms_common | +1.9 pp [+1.4, +2.4] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| deepgram_nova3_batch_keyterms_common − elevenlabs_scribe_v2_medical_batch | +1.6 pp [+1.2, +2.0] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| elevenlabs_scribe_v2_batch − elevenlabs_scribe_v2_batch_keyterms_common | +0.1 pp [-0.0, +0.2] | 0.0634 | 0.3170 | tie |
| elevenlabs_scribe_v2_batch − elevenlabs_scribe_v2_medical_batch | -0.2 pp [-0.5, +0.0] | 0.1056 | 0.4224 | tie |
| elevenlabs_scribe_v2_batch_keyterms_common − elevenlabs_scribe_v2_medical_batch | -0.3 pp [-0.6, -0.1] | 0.0086 | 0.0516 | elevenlabs_scribe_v2_batch_keyterms_common better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 83.0% [74.1, 89.2] | 78/94 | 7.9% | - |
| assemblyai_batch | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 85.7% [60.1, 96.0] |
| assemblyai_batch | date_of_birth | no instances | 0 | - | - |
| assemblyai_batch | phone | no instances | 0 | - | - |
| deepgram_nova3_batch | medication | 76.6% [67.1, 84.0] | 72/94 | 10.0% | - |
| deepgram_nova3_batch | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch | phone | no instances | 0 | - | - |
| deepgram_nova3_batch_keyterms | medication | 90.4% [82.8, 94.9] | 85/94 | 5.1% | - |
| deepgram_nova3_batch_keyterms | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch_keyterms | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch_keyterms | phone | no instances | 0 | - | - |
| deepgram_nova3_batch_keyterms_common | medication | 75.5% [66.0, 83.1] | 71/94 | 9.6% | - |
| deepgram_nova3_batch_keyterms_common | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch_keyterms_common | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch_keyterms_common | phone | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch | medication | 88.3% [80.2, 93.3] | 83/94 | 7.0% | - |
| elevenlabs_scribe_v2_batch | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 7.1% [1.3, 31.5] |
| elevenlabs_scribe_v2_batch | date_of_birth | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch | phone | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch_keyterms_common | medication | 92.6% [85.4, 96.3] | 87/94 | 3.3% | - |
| elevenlabs_scribe_v2_batch_keyterms_common | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 7.1% [1.3, 31.5] |
| elevenlabs_scribe_v2_batch_keyterms_common | date_of_birth | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch_keyterms_common | phone | no instances | 0 | - | - |
| elevenlabs_scribe_v2_medical_batch | medication | 85.1% [76.5, 90.9] | 80/94 | 7.5% | - |
| elevenlabs_scribe_v2_medical_batch | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 14.3% [4.0, 39.9] |
| elevenlabs_scribe_v2_medical_batch | date_of_birth | no instances | 0 | - | - |
| elevenlabs_scribe_v2_medical_batch | phone | no instances | 0 | - | - |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 0, deepgram_nova3_batch 1, deepgram_nova3_batch_keyterms 4, deepgram_nova3_batch_keyterms_common 3, elevenlabs_scribe_v2_batch 0, elevenlabs_scribe_v2_batch_keyterms_common 6, elevenlabs_scribe_v2_medical_batch 1.

### patient (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 8.1% [7.3, 9.0] | 9.4% | 13.3% | 2640 | 22926 | 0 | 0.5% [0.3, 0.8] (12/2535) |
| deepgram_nova3_batch | 8.7% [7.7, 9.9] | 10.2% | 15.2% | 2640 | 22926 | 0 | 1.6% [1.2, 2.2] (41/2535) |
| deepgram_nova3_batch_keyterms | 8.6% [7.7, 9.8] | 10.2% | 15.2% | 2640 | 22926 | 0 | 1.8% [1.3, 2.4] (45/2535) |
| deepgram_nova3_batch_keyterms_common | 8.7% [7.7, 9.8] | 10.2% | 15.3% | 2640 | 22926 | 0 | 1.7% [1.3, 2.3] (44/2535) |
| elevenlabs_scribe_v2_batch | 7.0% [6.2, 7.9] | 8.3% | 13.1% | 2640 | 22926 | 0 | 0.6% [0.3, 0.9] (14/2535) |
| elevenlabs_scribe_v2_batch_keyterms_common | 6.7% [5.9, 7.6] | 8.0% | 12.6% | 2640 | 22926 | 0 | 0.5% [0.3, 0.8] (12/2535) |
| elevenlabs_scribe_v2_medical_batch | 7.1% [6.2, 8.0] | 8.4% | 13.6% | 2640 | 22926 | 0 | 1.3% [0.9, 1.8] (33/2535) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -0.6 pp [-1.3, +0.0] | 0.0602 | 0.4074 | tie |
| assemblyai_batch − deepgram_nova3_batch_keyterms | -0.6 pp [-1.2, +0.1] | 0.0884 | 0.4420 | tie |
| assemblyai_batch − deepgram_nova3_batch_keyterms_common | -0.6 pp [-1.3, +0.0] | 0.0582 | 0.4074 | tie |
| assemblyai_batch − elevenlabs_scribe_v2_batch | +1.1 pp [+0.5, +1.6] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch_keyterms_common | +1.4 pp [+0.8, +1.9] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| assemblyai_batch − elevenlabs_scribe_v2_medical_batch | +1.0 pp [+0.5, +1.6] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms | +0.1 pp [-0.0, +0.2] | 0.1584 | 0.6335 | tie |
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms_common | +0.0 pp [-0.1, +0.1] | 0.7551 | 1.0000 | tie |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +1.7 pp [+1.2, +2.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch_keyterms_common | +2.0 pp [+1.5, +2.6] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_medical_batch | +1.7 pp [+1.1, +2.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| deepgram_nova3_batch_keyterms − deepgram_nova3_batch_keyterms_common | -0.1 pp [-0.2, +0.0] | 0.2078 | 0.6335 | tie |
| deepgram_nova3_batch_keyterms − elevenlabs_scribe_v2_batch | +1.7 pp [+1.1, +2.2] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch_keyterms − elevenlabs_scribe_v2_batch_keyterms_common | +1.9 pp [+1.4, +2.5] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| deepgram_nova3_batch_keyterms − elevenlabs_scribe_v2_medical_batch | +1.6 pp [+1.0, +2.2] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| deepgram_nova3_batch_keyterms_common − elevenlabs_scribe_v2_batch | +1.7 pp [+1.2, +2.3] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch_keyterms_common − elevenlabs_scribe_v2_batch_keyterms_common | +2.0 pp [+1.5, +2.6] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_batch_keyterms_common better |
| deepgram_nova3_batch_keyterms_common − elevenlabs_scribe_v2_medical_batch | +1.7 pp [+1.1, +2.2] | 0.0002 | 0.0042 | elevenlabs_scribe_v2_medical_batch better |
| elevenlabs_scribe_v2_batch − elevenlabs_scribe_v2_batch_keyterms_common | +0.3 pp [+0.1, +0.4] | 0.0006 | 0.0054 | elevenlabs_scribe_v2_batch_keyterms_common better |
| elevenlabs_scribe_v2_batch − elevenlabs_scribe_v2_medical_batch | -0.1 pp [-0.3, +0.2] | 0.6115 | 1.0000 | tie |
| elevenlabs_scribe_v2_batch_keyterms_common − elevenlabs_scribe_v2_medical_batch | -0.3 pp [-0.6, -0.1] | 0.0068 | 0.0544 | elevenlabs_scribe_v2_batch_keyterms_common better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 87.0% [77.0, 93.0] | 60/69 | 6.1% | - |
| assemblyai_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| assemblyai_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.1% | 85.7% [65.4, 95.0] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 71.0% [59.4, 80.4] | 49/69 | 15.9% | - |
| deepgram_nova3_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms | medication | 84.1% [73.7, 90.9] | 58/69 | 8.1% | - |
| deepgram_nova3_batch_keyterms | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch_keyterms | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms_common | medication | 71.0% [59.4, 80.4] | 49/69 | 14.0% | - |
| deepgram_nova3_batch_keyterms_common | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms_common | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch_keyterms_common | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | medication | 75.4% [64.0, 84.0] | 52/69 | 10.9% | - |
| elevenlabs_scribe_v2_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| elevenlabs_scribe_v2_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 6.6% | 52.4% [32.4, 71.7] |
| elevenlabs_scribe_v2_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 13.3% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch_keyterms_common | medication | 81.2% [70.4, 88.6] | 56/69 | 9.5% | - |
| elevenlabs_scribe_v2_batch_keyterms_common | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| elevenlabs_scribe_v2_batch_keyterms_common | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.1% | 47.6% [28.3, 67.6] |
| elevenlabs_scribe_v2_batch_keyterms_common | phone | 50.0% [9.5, 90.5] | 1/2 | 13.3% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_medical_batch | medication | 79.7% [68.8, 87.5] | 55/69 | 12.9% | - |
| elevenlabs_scribe_v2_medical_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| elevenlabs_scribe_v2_medical_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 6.6% | 42.9% [24.5, 63.5] |
| elevenlabs_scribe_v2_medical_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 0, deepgram_nova3_batch_keyterms 5, deepgram_nova3_batch_keyterms_common 1, elevenlabs_scribe_v2_batch 3, elevenlabs_scribe_v2_batch_keyterms_common 6, elevenlabs_scribe_v2_medical_batch 4.

## Worst utterances

Normalized alignment: `[ref→hyp]` substitution, `[-ref]` deletion, `[+hyp]` insertion. Top 10 by error count per config.

### assemblyai_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096` | doctor | 18/17 | [+4] [+or] [45→5] days [-ago] yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day1_consultation07:patient:0083` | patient | 14/36 | you know [-you] [-know] i have [-i] [-have] got a wee bit [a→around] [-wee] [-bit] [-round] the midriff the spare tire is definitely there and [-i] [-have] [-i] [-have] [-got] [-the] i have got the diabetes |
| `primock57:day4_consultation05:patient:0094` | patient | 14/67 | okay i did [-not] yeah sorry [-i] [-did] [-not] no i was saying i did not have any fever recently i i was sweating a little bit [-the] last [4→for] [days→bed] but i i [+am] not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day1_consultation14:doctor:0090` | doctor | 11/23 | okay [+all] [alright→right] who is looking after your diabetes is there anyone [+do] [is→you] [there→have] a doctor in [-a] hospital [-who] [-looks] [-after] [-your] [-diabetes] |
| `primock57:day1_consultation06:doctor:0045` | doctor | 10/32 | and some swelling in your ankles [+but] [reporting→importantly] no chest pain and [-and] [-have] [-you] [-had] [-any] [-have] [-you] [-any] have you noticed your heartbeat racing at all so palpitations or skipped heartbeat |
| `primock57:day2_consultation04:doctor:0136` | doctor | 10/32 | [no→yeah] okay [-i] [-i] [-am] [-not] [-i] [-am] [-going] [-to] [-not] i am not going to prescribe anything for you now because i think you need to have that basic assessment 1 |
| `primock57:day5_consultation02:doctor:0113` | doctor | 10/57 | no not if you are better if you [-are] [-if] [-you] feel like your symptoms get worse at any point or they are not resolving with the treatment or you keep getting a similar [-you] [-keep] [-getting] [-a] [-similar] problem [reccurently→recurrently] then it is important for us to [-talk] talk to you in more detail about that |
| `primock57:day5_consultation10:patient:0032` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |
| `primock57:day1_consultation09:patient:0073` | patient | 9/33 | so i live in a [-live] [-in] [-a] flat near my college with a [-a] couple [-of] [-like] friends of mine so i am [-i] [-am] not [-like] living at home or anything |
| `primock57:day2_consultation02:doctor:0070` | doctor | 9/51 | from now [-but] it [may→takes] [-take] time for the [form→forms] to come out to you and if you get the form [+to] get the [blood→test] [-tests] done straight away by the time that we are expecting [+a] result back you know one or 2 days after that we are looking [+at] maybe 6 days |

### deepgram_nova3_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096` | doctor | 18/17 | 45 days [-ago] [-yeah] okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day4_consultation05:patient:0094` | patient | 14/67 | okay i did [-not] yeah sorry [i→patrick] [-did] [-not] no i was saying i did not have any fever recently i i was sweating a little bit [the→glass] [last→for] [4→bed] [-days] but i i not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day2_consultation02:doctor:0070` | doctor | 13/51 | from now but [it→we] [-may] take time for the [form→forms] to come out to you and if you get the [form→forms] [get→that] [the→test] [-blood] [-tests] done straight away by the time that we are expecting [+a] result back you know [one→12] [-or] [-2] days after that we are looking [+at] maybe 6 days |
| `primock57:day5_consultation06:patient:0078` | patient | 12/30 | no like i said i only take [vitamins→vitamin] [-and] for my menstrual [cramps→comes] when [+it] [+comes] [they→to] [come→me] [maybe→but] i might take a [a→knife] [-an] [-ibuprofen] just to [ease→eat] the pain but |
| `primock57:day1_consultation10:doctor:0010` | doctor | 10/57 | right [-okay] i am sorry to hear there is a lot going on there and i can see why it is affecting you so you mentioned [it→you] [has→have] been [going→getting] [on→in] for [+the] last 3 days mainly the burning pain when you pass urine you [said→are] [you→just] [-are] going to the toilet more often as well [+is] that right |
| `primock57:day1_consultation10:doctor:0103` | doctor | 10/54 | sure and [obviously→as] as [your→you] [doctor→talk] [i→to] [am→somebody] [-here] to look after you so yeah i [-i] would strongly recommend you you know to avoid if you can great fine so at this [stage→point] i would not normally examine you but i think based on your story i think you know [+i] [+am] i am reassured |
| `primock57:day1_consultation13:doctor:0081` | doctor | 10/41 | okay [all→alright] [right→so] [something→feel] [for→free] [-you] to bear in mind if you feel [that→like] [-you] [-are] your eyes are straining i [would→will] always recommend having a repeat eye test done have you been [-feeling] more stressed or anxious at work recently |
| `primock57:day4_consultation05:patient:0015` | patient | 10/52 | yes so i have [+a] i have [+a] i do not know how do you say it properly in english i mean [+we] [+that] [+was] [without→from] [sounding→the] [good→google] like diarrhea for for yeah so it is lasting for like 3 days and yeah i i do not know i do not know what [could→would] because it [-i] |
| `primock57:day5_consultation08:doctor:0090` | doctor | 10/16 | [-who] [-do] you [live→deal] with do you live [on→with] [your→me] [own→right] [or→now] [do→deal] [-you] [-live] with |
| `primock57:day5_consultation10:patient:0032` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |

### deepgram_nova3_batch_keyterms

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096` | doctor | 18/17 | 45 days [-ago] [-yeah] okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day4_consultation05:patient:0094` | patient | 14/67 | okay i did [-not] yeah sorry [i→patrick] [-did] [-not] no i was saying i did not have any fever recently i i was sweating a little bit [the→glass] [last→for] [4→bed] [-days] but i i not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day2_consultation02:doctor:0070` | doctor | 13/51 | from now but [it→we] [-may] take time for the [form→forms] to come out to you and if you get the [form→forms] [get→that] [the→test] [-blood] [-tests] done straight away by the time that we are expecting [+a] result back you know [one→12] [-or] [-2] days after that we are looking [+at] maybe 6 days |
| `primock57:day5_consultation06:patient:0078` | patient | 12/30 | no like i said i only take [vitamins→vitamin] [-and] for my menstrual [cramps→comes] when [+it] [+comes] [they→to] [come→me] [maybe→but] i might take a [a→knife] [-an] [-ibuprofen] just to [ease→eat] the pain but |
| `primock57:day1_consultation02:doctor:0047` | doctor | 11/11 | [-so] [-for] [-example] [-have] [-you] [-changed] [-your] [-shower] [-gel] [-any] [-clothing] |
| `primock57:day1_consultation10:doctor:0010` | doctor | 10/57 | right [-okay] i am sorry to hear there is a lot going on there and i can see why it is affecting you so you mentioned [it→you] [has→have] been [going→getting] [on→in] for [+the] last 3 days mainly the burning pain when you pass urine you [said→are] [you→just] [-are] going to the toilet more often as well [+is] that right |
| `primock57:day1_consultation10:doctor:0103` | doctor | 10/54 | sure and [obviously→as] as [your→you] [doctor→talk] [i→to] [am→somebody] [-here] to look after you so yeah i [-i] would strongly recommend you you know to avoid if you can great fine so at this [stage→point] i would not normally examine you but i think based on your story i think you know [+i] [+am] i am reassured |
| `primock57:day1_consultation13:doctor:0081` | doctor | 10/41 | okay [all→alright] [right→so] [something→feel] [for→free] [-you] to bear in mind if you feel [that→like] [-you] [-are] your eyes are straining i [would→will] always recommend having a repeat eye test done have you been [-feeling] more stressed or anxious at work recently |
| `primock57:day2_consultation08:doctor:0088` | doctor | 10/13 | [i→so] [am→peter] [sorry→how] [-to] [-hear] [-that] how [old→does] [was→it] [-he] when that [happened→happens] |
| `primock57:day4_consultation05:patient:0015` | patient | 10/52 | yes so i have [+a] i have [+a] i do not know how do you say it properly in english i mean [+we] [+that] [+was] [without→from] [sounding→the] [good→google] like diarrhea for for yeah so it is lasting for like 3 days and yeah i i do not know i do not know what [could→would] because it [-i] |

### deepgram_nova3_batch_keyterms_common

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096` | doctor | 18/17 | 45 days [-ago] [-yeah] okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day4_consultation05:patient:0094` | patient | 14/67 | okay i did [-not] yeah sorry [i→patrick] [-did] [-not] no i was saying i did not have any fever recently i i was sweating a little bit [the→glass] [last→for] [4→bed] [-days] but i i not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day2_consultation02:doctor:0070` | doctor | 13/51 | from now but [it→we] [-may] take time for the [form→forms] to come out to you and if you get the [form→forms] [get→that] [the→test] [-blood] [-tests] done straight away by the time that we are expecting [+a] result back you know [one→12] [-or] [-2] days after that we are looking [+at] maybe 6 days |
| `primock57:day5_consultation06:patient:0078` | patient | 12/30 | no like i said i only take [vitamins→vitamin] [-and] for my menstrual [cramps→comes] when [+it] [+comes] [they→to] [come→me] [maybe→but] i might take a [a→knife] [-an] [-ibuprofen] just to [ease→eat] the pain but |
| `primock57:day5_consultation08:doctor:0090` | doctor | 11/16 | [-who] [-do] you [live→deal] with do you live [on→with] [your→me] [own→right] [or→now] [do→deal] [you→with] [live→.] [-with] |
| `primock57:day1_consultation10:doctor:0010` | doctor | 10/57 | right [-okay] i am sorry to hear there is a lot going on there and i can see why it is affecting you so you mentioned [it→you] [has→have] been [going→getting] [on→in] for [+the] last 3 days mainly the burning pain when you pass urine you [said→are] [you→just] [-are] going to the toilet more often as well [+is] that right |
| `primock57:day1_consultation10:doctor:0103` | doctor | 10/54 | sure and [obviously→as] as [your→you] [doctor→talk] [i→to] [am→somebody] [-here] to look after you so yeah i [-i] would strongly recommend you you know to avoid if you can great fine so at this [stage→point] i would not normally examine you but i think based on your story i think you know [+i] [+am] i am reassured |
| `primock57:day1_consultation13:doctor:0081` | doctor | 10/41 | okay [all→alright] [right→so] [something→feel] [for→free] [-you] to bear in mind if you feel [that→like] [-you] [-are] your eyes are straining i [would→will] always recommend having a repeat eye test done have you been [-feeling] more stressed or anxious at work recently |
| `primock57:day4_consultation05:patient:0015` | patient | 10/52 | yes so i have [+a] i have [+a] i do not know how do you say it properly in english i mean [+we] [+that] [+was] [without→from] [sounding→the] [good→bug] like diarrhea for for yeah so it is lasting for like 3 days and yeah i i do not know i do not know what [could→would] because it [-i] |
| `primock57:day5_consultation10:patient:0032` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |

### elevenlabs_scribe_v2_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096` | doctor | 19/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day4_consultation05:patient:0094` | patient | 10/67 | okay i did not yeah sorry i did [-not] no i was saying i did not have any fever recently i i was sweating a little bit [-the] last [4→for] [days→bed] but i i not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day5_consultation10:patient:0032` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |
| `primock57:day1_consultation03:doctor:0128` | doctor | 9/31 | okay now [+there] [+are] a couple of things i want you to think about is you know if your symptoms are not getting [+any] better [+in] [+the] next [+2] [+to] [23→3] days or indeed [-they] are getting worse |
| `primock57:day1_consultation10:patient:0031` | patient | 8/4 | no [+i] [+know] [+what] [+you] [+are] [no→about] [nausea→to] [vomiting→say] |
| `primock57:day1_consultation10:patient:0129` | patient | 8/13 | either [+that] [back→train] [pain→bottom] [vomiting→thing] great okay yeah i will [watch→chat] [out→with] [for→liz] [-those] |
| `primock57:day1_consultation11:patient:0129` | patient | 8/33 | [+on] [honest→a] i suppose not every week but maybe [-i] [-will] once or twice a month that yeah i will [+i] [+will] go out with my friends and [+we] [+will] drink a lot so that that is yeah |
| `primock57:day2_consultation02:doctor:0070` | doctor | 8/51 | from now but it [may→will] take time for the form to come out to you and if you get the form [get→to] [the→do] [blood→that] [tests→test] done straight away by the time that we are expecting [+a] result back you know one or 2 days after that we [+we] are looking [+at] maybe 6 days |
| `primock57:day2_consultation08:doctor:0088` | doctor | 8/13 | [i→so] [am→how] [sorry→old] [-to] [-hear] [-that] how old [was→is] he when that [happened→happens] |
| `primock57:day3_consultation08:doctor:0062` | doctor | 8/19 | [+it] [+is] [cool→all] because there [is→was] nothing alarming yeah [no→normal] [-more] okay [that→absolutely] [-is] fine okay so that seems all right |

### elevenlabs_scribe_v2_batch_keyterms_common

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096` | doctor | 19/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day2_consultation02:doctor:0070` | doctor | 10/51 | from now but it [may→takes] [-take] time for the form to come out to you and [+then] if you get the form [+to] [get→do] the [blood→test] [-tests] done straight away by the time that we are expecting [+a] result back you know one or 2 days after that we [+we] are looking [+at] maybe 6 days |
| `primock57:day4_consultation05:patient:0094` | patient | 10/67 | okay i did not yeah sorry i did [-not] no i was saying i did not have any fever recently i i was sweating a little bit [-the] last [4→for] [days→bed] but i i not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day5_consultation10:patient:0032` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |
| `primock57:day1_consultation10:patient:0031` | patient | 8/4 | no [+i] [+know] [+what] [+you] [+are] [no→trying] [nausea→to] [vomiting→say] |
| `primock57:day1_consultation11:patient:0129` | patient | 8/33 | [+on] [honest→a] i suppose not every week but maybe [-i] [-will] once or twice a month that yeah i will [+i] [+will] go out with my friends and [+we] [+will] drink a lot so that that is yeah |
| `primock57:day3_consultation01:patient:0052` | patient | 8/27 | no [i→well] [i→well] [-got] [-no] i [do→think] sometimes but i do not know which ones [but→so] i have a peanut allergy as well like [+i] [+have] always had it |
| `primock57:day3_consultation08:doctor:0062` | doctor | 8/19 | [+it] [+is] [cool→all] because there [is→was] nothing alarming yeah [no→normal] [-more] okay [that→absolutely] [-is] fine okay so that seems all right |
| `primock57:day1_consultation02:doctor:0115` | doctor | 7/18 | because if that is causing [your→you] symptoms then we need to have a discussion about [+it] [+next] [+time] [an→i] [eczema→see] [cu→you] |
| `primock57:day1_consultation03:doctor:0032` | doctor | 7/23 | so you mentioned a few things you mentioned [+the] [a→headaches] [headache→and] you also mentioned some [disease→zigzag] [like→lines] [-lyme] [-is] before the headaches came on |

### elevenlabs_scribe_v2_medical_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096` | doctor | 19/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day1_consultation10:doctor:0053` | doctor | 10/7 | [+i] [+am] [+going] [if→to] [you→put] [do→it] [not→on] [want→my] [me→own] [asking→screen] |
| `primock57:day1_consultation15:patient:0037` | patient | 10/19 | yeah it is not really [-it] [-is] [-not] [-really] major yeah it is just [+a] [+little] [+bit] [like→of] [literally→drainage] [grinding→from] my legs |
| `primock57:day3_consultation08:doctor:0062` | doctor | 10/19 | [+it] [+is] [cool→all] because there [is→was] nothing alarming yeah [no→normal] [-more] okay [that→absolutely] [-is] fine okay so that seems [all→alright] [-right] |
| `primock57:day4_consultation05:patient:0094` | patient | 10/67 | okay i did not yeah sorry i did [-not] no i was saying i did not have any fever recently i i was sweating a little bit [-the] last [4→for] [days→bed] but i i not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day5_consultation10:patient:0032` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |
| `primock57:day1_consultation03:doctor:0128` | doctor | 8/31 | okay now [+there] [+are] a couple of things i want you to think about is you know if your symptoms are not getting better [+in] [+the] next [+2] [+to] [23→3] days or indeed [-they] are getting worse |
| `primock57:day1_consultation10:patient:0031` | patient | 8/4 | [+huh] [+i] [+know] [+what] [no→you] [no→are] [nausea→talking] [vomiting→say] |
| `primock57:day1_consultation10:patient:0129` | patient | 8/13 | either [+that] [back→train] [pain→bottom] [vomiting→thing] great okay yeah i will [watch→chat] [out→liz] [-for] [-those] |
| `primock57:day1_consultation11:patient:0129` | patient | 8/33 | [+ah] [+on] [honest→a] i suppose not every week but maybe [-i] [-will] once or twice a month [that→but] yeah i will go out with my friends and [+we] [+will] drink a lot so that that is yeah |
