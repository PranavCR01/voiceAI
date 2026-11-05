# Offline STT accuracy report

- **Generated:** 2026-11-05 10:25 UTC
- **Manifest:** `data/manifests/primock57.telephony_g712.jsonl` (5255 utterances)
- **Profile:** `configs/profiles/healthcare_intake.yaml`
- **Normalizer (headline WER):** `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy`, `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy,hyp-mdy`
- **Leaderboard-comparable WER:** `whisper-normalizer==0.1.15/EnglishTextNormalizer`
- **Intervals:** 95% paired percentile bootstrap, 10000 resamples, seed 0, resampling whole speakers. Pairwise p-values Holm-adjusted within each table. "Tie" = difference interval includes 0. No winner is called with fewer than 10 speakers in a table.
- **Failed requests** are scored as empty transcripts (every reference word deleted).
- **Empty on speech:** successful requests that returned no text although the normalized reference has words (Wilson interval, not clustered). An empty transcript for "Um." is correct and not counted. These rows are scored as they came back, never selectively re-run.

## Configurations

| Config | Provider | Model | Mode | Settings | Hyp. dates | Run | Recorded | Git |
|---|---|---|---|---|---|---|---|---|
| assemblyai_batch | assemblyai | `universal-3-5-pro` | batch | `{"format_text": true, "language_code": "en", "punctuate": true}` | as reference | assemblyai-batch | 2026-11-05 | `86d94f1` |
| deepgram_nova3_batch | deepgram | `nova-3` | batch | `{"punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch | 2026-11-05 | `86d94f1` |

## Real audio

### All real audio

114 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 7.6% [7.0, 8.3] | 10.3% | 13.0% | 5255 | 56795 | 0 | 0.6% [0.4, 0.8] (29/5105) |
| deepgram_nova3_batch | 9.8% [9.0, 10.6] | 12.6% | 15.8% | 5255 | 56795 | 0 | 0.5% [0.3, 0.7] (24/5105) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -2.2 pp [-2.7, -1.7] | 0.0002 | 0.0002 | assemblyai_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 82.2% [75.6, 87.3] | 134/163 | 9.3% | - |
| assemblyai_batch | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 81.2% [57.0, 93.4] |
| assemblyai_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.1% | 85.7% [65.4, 95.0] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 40.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 67.5% [60.0, 74.2] | 110/163 | 18.0% | - |
| deepgram_nova3_batch | dosage | 87.5% [64.0, 96.5] | 14/16 | 6.4% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 85.7% [65.4, 95.0] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 33.3% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 1.

### doctor (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 6.4% [5.7, 7.2] | 10.1% | 9.6% | 2615 | 33869 | 0 | 0.4% [0.2, 0.8] (11/2570) |
| deepgram_nova3_batch | 8.3% [7.4, 9.3] | 12.0% | 12.3% | 2615 | 33869 | 0 | 0.4% [0.2, 0.8] (11/2570) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -1.9 pp [-2.4, -1.4] | 0.0002 | 0.0002 | assemblyai_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 81.9% [72.9, 88.4] | 77/94 | 8.9% | - |
| assemblyai_batch | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 78.6% [52.4, 92.4] |
| assemblyai_batch | date_of_birth | no instances | 0 | - | - |
| assemblyai_batch | phone | no instances | 0 | - | - |
| deepgram_nova3_batch | medication | 72.3% [62.6, 80.4] | 68/94 | 14.0% | - |
| deepgram_nova3_batch | dosage | 85.7% [60.1, 96.0] | 12/14 | 6.9% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch | phone | no instances | 0 | - | - |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 0, deepgram_nova3_batch 1.

### patient (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 9.3% [8.4, 10.4] | 10.6% | 16.3% | 2640 | 22926 | 0 | 0.7% [0.4, 1.1] (18/2535) |
| deepgram_nova3_batch | 11.9% [10.7, 13.4] | 13.4% | 19.4% | 2640 | 22926 | 0 | 0.5% [0.3, 0.9] (13/2535) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -2.6 pp [-3.5, -1.7] | 0.0002 | 0.0002 | assemblyai_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 82.6% [72.0, 89.8] | 57/69 | 9.8% | - |
| assemblyai_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| assemblyai_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.1% | 85.7% [65.4, 95.0] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 40.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 60.9% [49.1, 71.5] | 42/69 | 23.6% | - |
| deepgram_nova3_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 85.7% [65.4, 95.0] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 33.3% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 0.

## Worst utterances

Normalized alignment: `[ref→hyp]` substitution, `[-ref]` deletion, `[+hyp]` insertion. Top 10 by error count per config.

### assemblyai_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096:telephony_g712` | doctor | 17/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day5_consultation08:doctor:0090:telephony_g712` | doctor | 15/16 | [who→he] [do→delivered] [you→did] [live→he] [with→bring] [-do] [-you] [-live] [-on] [-your] [-own] or [do→did] [you→he] [live→just] [-with] |
| `primock57:day1_consultation07:patient:0083:telephony_g712` | patient | 14/36 | you know [-you] [-know] i have [-i] [-have] got a wee bit [a→around] [-wee] [-bit] [-round] the midriff the spare tire is definitely there and [-i] [-have] [-i] [-have] [-got] [-the] i have got the diabetes |
| `primock57:day4_consultation05:patient:0049:telephony_g712` | patient | 12/36 | yes but [-yes] [-but] i [-i] go to the toilet [also→so] often so i [-i] [-i] [-yeah] [-i] try not to eat a lot because i [-yeah] [-i] just [going→go] to the toilet every 10 [minute→minutes] |
| `primock57:day1_consultation04:patient:0097:telephony_g712` | patient | 11/25 | no i think [-i] [-think] it is [-it] [-is] the [-you] [-know] [-it] [-is] [-the] good kind of stress [-it] [-is] it is good work |
| `primock57:day1_consultation14:doctor:0090:telephony_g712` | doctor | 11/23 | okay [+all] [alright→right] who is looking after your diabetes is there anyone [+do] [is→you] [there→have] a doctor in [-a] hospital [-who] [-looks] [-after] [-your] [-diabetes] |
| `primock57:day4_consultation05:patient:0094:telephony_g712` | patient | 11/67 | okay i did not yeah sorry [-i] [-did] [-not] no i was saying i did not have any fever recently i i was sweating a little bit [-the] last 4 days but i i [+am] not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day1_consultation06:doctor:0045:telephony_g712` | doctor | 10/32 | and some swelling in your ankles [+but] [reporting→importantly] no chest pain and [-and] [-have] [-you] [-had] [-any] [-have] [-you] [-any] have you noticed your heartbeat racing at all so palpitations or skipped heartbeat |
| `primock57:day2_consultation04:doctor:0136:telephony_g712` | doctor | 10/32 | [no→yeah] okay [-i] [-i] [-am] [-not] [-i] [-am] [-going] [-to] [-not] i am not going to prescribe anything for you now because i think you need to have that basic assessment 1 |
| `primock57:day5_consultation02:doctor:0113:telephony_g712` | doctor | 10/57 | no not if you are better if you [-are] [-if] [-you] feel like your symptoms get worse at any point or they are not resolving with the treatment or you keep getting a similar [-you] [-keep] [-getting] [-a] [-similar] problem [reccurently→recurrently] then it is important for us to [-talk] talk to you in more detail about that |

### deepgram_nova3_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096:telephony_g712` | doctor | 20/17 | 45 days [-ago] yeah okay [are→and] you aware of anything that might [have→state] [-set] your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day1_consultation10:doctor:0103:telephony_g712` | doctor | 20/54 | sure and [+i] [obviously→am] [as→going] [your→to] [doctor→ask] [i→you] [am→doctor] [here→something] [to→after] [look→the] [after→cough] [you→too] so yeah i [-i] would strongly recommend you you know to avoid [if→it] [-you] [-can] [-great] fine so at this [stage→point] i would not normally examine you but i think based on your story i think you know [+i] [+am] i am reassured |
| `primock57:day2_consultation02:doctor:0070:telephony_g712` | doctor | 17/51 | from now [but→so] [it→we] [may→can] [take→not] [time→come] for the [form→forms] to come out to you and if you get the [form→forms] [get→that] [the→test] [blood→on] [-tests] [-done] straight away by the time that we are expecting [+a] result back you know [one→12] [-or] [-2] days after that we are looking [+at] maybe 6 days |
| `primock57:day1_consultation10:doctor:0010:telephony_g712` | doctor | 16/57 | [right→alright] [-okay] i [am→can] [sorry→certainly] [-to] hear [-there] [-is] a lot going on there and i can see why it is affecting you so you mentioned [it→you] [has→have] been going on for [+the] last 3 days mainly the burning pain when you pass urine you [said→should] [you→get] [are→into] [-going] [-to] the toilet more often as well [+is] that right |
| `primock57:day5_consultation06:patient:0078:telephony_g712` | patient | 16/30 | no like i said i only take [+a] [+bit] [vitamins→of] [and→it] [for→before] my menstrual [cramps→comes] when [+it] [they→comes] [come→to] [maybe→me] [i→then] might take a [a→knife] [-an] [-ibuprofen] just to [ease→eat] the pain but [+.] |
| `primock57:day5_consultation08:doctor:0090:telephony_g712` | doctor | 16/16 | [-who] [-do] [-you] [-live] [-with] [-do] [-you] [-live] [-on] [-your] [-own] [-or] [-do] [-you] [-live] [-with] |
| `primock57:day3_consultation01:patient:0057:telephony_g712` | patient | 13/31 | yeah [is→except] [that→when] [-well] i was like 6 or something i i i think [ohh→0] sorry [the→it] [-swelling] is [getting→swelling] [ohh→of] [my→gas] [god→00] [-ohh] yeah i think when i was [+sick] [6→.] |
| `primock57:day1_consultation04:doctor:0061:telephony_g712` | doctor | 12/14 | [no→yeah] you [do→know] [not→it] [feel→will] [blocked→block] [or→to] any [+good] [discharge→source] coming [out→as] [of→you] [your→is] [-ears] |
| `primock57:day1_consultation13:doctor:0081:telephony_g712` | doctor | 12/41 | okay [all→forward] [right→feel] [something→free] [-for] [-you] to bear in mind [if→like] you [-feel] [-that] [-you] are [-your] eyes are straining i [would→will] always recommend having a repeat eye test done have you been [-feeling] more stressed or anxious at work recently |
| `primock57:day1_consultation10:patient:0129:telephony_g712` | patient | 11/13 | either [back→that] [pain→same] [vomiting→box] [great→and] [okay→breakfast] yeah [i→0] [will→chocolate] [-watch] [-out] [-for] [-those] |
