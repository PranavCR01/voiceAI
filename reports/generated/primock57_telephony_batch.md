# Offline STT accuracy report

- **Generated:** 2026-11-05 05:12 UTC
- **Manifest:** `data/manifests/primock57.telephony_mulaw.jsonl` (5255 utterances)
- **Profile:** `configs/profiles/healthcare_intake.yaml`
- **Normalizer (headline WER):** `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy`, `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy,hyp-mdy`
- **Leaderboard-comparable WER:** `whisper-normalizer==0.1.15/EnglishTextNormalizer`
- **Intervals:** 95% paired percentile bootstrap, 10000 resamples, seed 0, resampling whole speakers. Pairwise p-values Holm-adjusted within each table. "Tie" = difference interval includes 0. No winner is called with fewer than 10 speakers in a table.
- **Failed requests** are scored as empty transcripts (every reference word deleted).
- **Empty on speech:** successful requests that returned no text although the normalized reference has words (Wilson interval, not clustered). An empty transcript for "Um." is correct and not counted. These rows are scored as they came back, never selectively re-run.

## Configurations

| Config | Provider | Model | Mode | Settings | Hyp. dates | Run | Recorded | Git |
|---|---|---|---|---|---|---|---|---|
| assemblyai_batch | assemblyai | `universal-3-5-pro` | batch | `{"format_text": true, "language_code": "en", "punctuate": true}` | as reference | assemblyai-batch | 2026-11-05 | `744903f` |
| deepgram_nova3_batch | deepgram | `nova-3` | batch | `{"punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch | 2026-11-05 | `744903f` |
| elevenlabs_scribe_v2_batch | elevenlabs | `scribe_v2` | batch | `{"language_code": "en", "temperature": 0}` | as reference | elevenlabs-scribe-v2-batch | 2026-11-05 | `744903f` |

## Real audio

### All real audio

114 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 7.3% [6.7, 7.9] | 10.0% | 12.0% | 5255 | 56795 | 0 | 0.3% [0.2, 0.5] (16/5105) |
| deepgram_nova3_batch | 8.6% [7.8, 9.3] | 11.4% | 14.0% | 5255 | 56795 | 0 | 1.0% [0.7, 1.3] (49/5105) |
| elevenlabs_scribe_v2_batch | 6.8% [6.2, 7.5] | 9.6% | 13.5% | 5255 | 56795 | 0 | 0.5% [0.3, 0.7] (23/5105) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -1.3 pp [-1.7, -0.8] | 0.0002 | 0.0006 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | +0.5 pp [+0.1, +0.9] | 0.0188 | 0.0188 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +1.8 pp [+1.4, +2.1] | 0.0002 | 0.0006 | elevenlabs_scribe_v2_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 80.4% [73.6, 85.7] | 131/163 | 10.0% | - |
| assemblyai_batch | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 81.2% [57.0, 93.4] |
| assemblyai_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.1% | 85.7% [65.4, 95.0] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 71.8% [64.4, 78.1] | 117/163 | 15.0% | - |
| deepgram_nova3_batch | dosage | 87.5% [64.0, 96.5] | 14/16 | 6.4% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 81.0% [60.0, 92.3] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | medication | 80.4% [73.6, 85.7] | 131/163 | 11.1% | - |
| elevenlabs_scribe_v2_batch | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 12.5% [3.5, 36.0] |
| elevenlabs_scribe_v2_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 6.6% | 42.9% [24.5, 63.5] |
| elevenlabs_scribe_v2_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 1, elevenlabs_scribe_v2_batch 3.

### doctor (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 6.0% [5.4, 6.7] | 9.7% | 9.0% | 2615 | 33869 | 0 | 0.3% [0.1, 0.6] (7/2570) |
| deepgram_nova3_batch | 7.4% [6.5, 8.3] | 11.1% | 10.8% | 2615 | 33869 | 0 | 0.7% [0.4, 1.1] (18/2570) |
| elevenlabs_scribe_v2_batch | 5.8% [5.1, 6.6] | 9.6% | 10.3% | 2615 | 33869 | 0 | 0.2% [0.1, 0.5] (6/2570) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -1.4 pp [-1.9, -0.8] | 0.0002 | 0.0006 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | +0.2 pp [-0.2, +0.6] | 0.3050 | 0.3050 | tie |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +1.6 pp [+1.1, +2.1] | 0.0002 | 0.0006 | elevenlabs_scribe_v2_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 81.9% [72.9, 88.4] | 77/94 | 8.8% | - |
| assemblyai_batch | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 78.6% [52.4, 92.4] |
| assemblyai_batch | date_of_birth | no instances | 0 | - | - |
| assemblyai_batch | phone | no instances | 0 | - | - |
| deepgram_nova3_batch | medication | 77.7% [68.2, 84.9] | 73/94 | 10.4% | - |
| deepgram_nova3_batch | dosage | 85.7% [60.1, 96.0] | 12/14 | 6.9% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch | phone | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch | medication | 84.0% [75.3, 90.1] | 79/94 | 9.8% | - |
| elevenlabs_scribe_v2_batch | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 0.0% [0.0, 21.5] |
| elevenlabs_scribe_v2_batch | date_of_birth | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch | phone | no instances | 0 | - | - |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 0, deepgram_nova3_batch 1, elevenlabs_scribe_v2_batch 1.

### patient (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 9.1% [8.2, 10.1] | 10.4% | 15.1% | 2640 | 22926 | 0 | 0.4% [0.2, 0.7] (9/2535) |
| deepgram_nova3_batch | 10.3% [9.1, 11.6] | 11.8% | 17.2% | 2640 | 22926 | 0 | 1.2% [0.9, 1.7] (31/2535) |
| elevenlabs_scribe_v2_batch | 8.3% [7.2, 9.5] | 9.6% | 16.7% | 2640 | 22926 | 0 | 0.7% [0.4, 1.1] (17/2535) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -1.2 pp [-2.0, -0.4] | 0.0054 | 0.0108 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | +0.8 pp [+0.1, +1.6] | 0.0246 | 0.0246 | elevenlabs_scribe_v2_batch better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +2.0 pp [+1.5, +2.5] | 0.0002 | 0.0006 | elevenlabs_scribe_v2_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 78.3% [67.2, 86.4] | 54/69 | 11.7% | - |
| assemblyai_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| assemblyai_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.1% | 85.7% [65.4, 95.0] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 63.8% [52.0, 74.1] | 44/69 | 21.4% | - |
| deepgram_nova3_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 81.0% [60.0, 92.3] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | medication | 75.4% [64.0, 84.0] | 52/69 | 12.9% | - |
| elevenlabs_scribe_v2_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| elevenlabs_scribe_v2_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 6.6% | 42.9% [24.5, 63.5] |
| elevenlabs_scribe_v2_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 0, elevenlabs_scribe_v2_batch 2.

## Worst utterances

Normalized alignment: `[ref→hyp]` substitution, `[-ref]` deletion, `[+hyp]` insertion. Top 10 by error count per config.

### assemblyai_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096:telephony_mulaw` | doctor | 17/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day1_consultation07:patient:0083:telephony_mulaw` | patient | 14/36 | you know [-you] [-know] i have [-i] [-have] got a wee bit [a→around] [-wee] [-bit] [-round] the midriff the spare tire is definitely there and [-i] [-have] [-i] [-have] [-got] [-the] i have got the diabetes |
| `primock57:day4_consultation05:patient:0094:telephony_mulaw` | patient | 12/67 | okay i did not yeah sorry [-i] [-did] [-not] no i was saying i did not have any fever recently i i was sweating a little bit [-the] last 4 days but i i [+am] not sure if [-if] i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day1_consultation06:doctor:0045:telephony_mulaw` | doctor | 10/32 | and some swelling in your ankles [+but] [reporting→importantly] no chest pain and [-and] [-have] [-you] [-had] [-any] [-have] [-you] [-any] have you noticed your heartbeat racing at all so palpitations or skipped heartbeat |
| `primock57:day2_consultation05:doctor:0139:telephony_mulaw` | doctor | 10/44 | okay great so just bear with me a few minutes and then i will send that all through and then you should [-you] [-should] be able to [-help] [-you] [-should] have the information at your hands [-to] in order to [take→think] [things→about] [further→it] [-okay] |
| `primock57:day5_consultation02:doctor:0113:telephony_mulaw` | doctor | 10/57 | no not if you are better if you [-are] [-if] [-you] feel like your symptoms get worse at any point or they are not resolving with the treatment or you keep getting a similar [-you] [-keep] [-getting] [-a] [-similar] problem [reccurently→recurrently] then it is important for us to [-talk] talk to you in more detail about that |
| `primock57:day5_consultation10:patient:0032:telephony_mulaw` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |
| `primock57:day1_consultation05:doctor:0056:telephony_mulaw` | doctor | 9/23 | yeah okay well [-it] [-is] something [for→else] [-us] to think about maybe [+we] [+will] [+have] [worth→to] [taking→do] a pregnancy test later on just to confirm that |
| `primock57:day1_consultation09:patient:0073:telephony_mulaw` | patient | 9/33 | so i live in a [-live] [-in] [-a] flat near my college with a [-a] couple [-of] [-like] friends of mine so i am [-i] [-am] not [-like] living at home or anything |
| `primock57:day3_consultation01:patient:0016:telephony_mulaw` | patient | 9/29 | yeah that is well i do not think [-i] [-do] [-not] [-think] it was it [-it] was not a sandwich but it was [-it] [-was] something with [prawn→prawns] [-so] |

### deepgram_nova3_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096:telephony_mulaw` | doctor | 18/17 | 45 days [-ago] yeah okay [are→and] you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day1_consultation10:doctor:0103:telephony_mulaw` | doctor | 18/54 | sure and [obviously→i] [as→am] [your→glad] [doctor→you] [i→talk] [-am] [-here] to [look→somebody] [after→at] [you→the] so yeah i [-i] would strongly recommend you you know to avoid [if→it] [-you] [-can] [-great] fine so at this [stage→point] i would not normally examine you but i think based on your story i think you know [+i] [+am] i am reassured |
| `primock57:day5_consultation08:doctor:0090:telephony_mulaw` | doctor | 16/16 | [-who] [-do] [-you] [-live] [-with] [-do] [-you] [-live] [-on] [-your] [-own] [-or] [-do] [-you] [-live] [-with] |
| `primock57:day1_consultation10:doctor:0010:telephony_mulaw` | doctor | 15/57 | [right→alright] [-okay] i am sorry to hear [-there] [-is] a lot going on there and i can see why it is affecting you so you mentioned [it→you] [has→have] been [going→getting] [on→in] for [+the] last 3 days mainly the burning pain when you pass urine you [said→used] [you→get] [are→into] [-going] [-to] the toilet more often as well [+is] that right |
| `primock57:day2_consultation02:doctor:0070:telephony_mulaw` | doctor | 13/51 | from now but [it→we] [-may] take time for the [form→forms] to come out to you and if you get the [form→forms] [get→that] [the→test] [-blood] [-tests] done straight away by the time that we are expecting [+a] result back you know [one→12] [-or] [-2] days after that we are looking [+at] maybe 6 days |
| `primock57:day4_consultation05:patient:0094:telephony_mulaw` | patient | 12/67 | okay i did not yeah sorry [i→about] [did→it] [-not] no i was saying i did not have any fever recently i i was sweating a little bit [-the] last [4→for] [days→bed] but i i not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day5_consultation06:patient:0078:telephony_mulaw` | patient | 12/30 | no like i said i only take [vitamins→weekly] [-and] for my menstrual [cramps→comes] when [+it] [+comes] [they→to] [come→me] [maybe→but] i might take a a [an→knife] [-ibuprofen] just to [ease→eat] the pain but [+.] |
| `primock57:day4_consultation05:patient:0015:telephony_mulaw` | patient | 10/52 | yes so i have [+a] i have [+a] i do not know how do you say it properly in english i mean [+with] [+that] [+was] [without→from] [sounding→the] [good→bug] like diarrhea for for yeah so it is lasting for like 3 days and yeah i i do not know i do not know what [could→would] because it [-i] |
| `primock57:day5_consultation09:doctor:0098:telephony_mulaw` | doctor | 10/31 | well you can get [you→a] can get [-a] bacterial infection caused [which→what] is [+it] called it is [+it] [+is] called lyme disease [that→but] you can get a rash [-like] [-that] from a tick [-bite] |
| `primock57:day5_consultation10:patient:0032:telephony_mulaw` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |

### elevenlabs_scribe_v2_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation07:doctor:0096:telephony_mulaw` | doctor | 19/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day5_consultation08:doctor:0090:telephony_mulaw` | doctor | 15/16 | [who→3] [do→chile] [you→peppers] [live→chile] [with→peppers] [-do] you [live→know] [on→chile] [your→peppers] [-own] [-or] [-do] [-you] [-live] [-with] |
| `primock57:day1_consultation10:doctor:0103:telephony_mulaw` | doctor | 10/54 | sure and obviously as your doctor [i→something] [-am] [-here] to look after you so yeah i [-i] would strongly recommend you you know to avoid [+it] if you can great fine so [at→as] [this→i] [stage→said] i would not normally examine you but i think based on your story i think you know [+i] [+am] i am reassured |
| `primock57:day4_consultation05:patient:0094:telephony_mulaw` | patient | 10/67 | okay i did not yeah sorry i did [-not] no i was saying i did not have any fever recently i i was sweating a little bit [-the] last [4→for] [days→bed] but i i not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not know maybe |
| `primock57:day5_consultation10:patient:0032:telephony_mulaw` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |
| `primock57:day1_consultation10:doctor:0010:telephony_mulaw` | doctor | 9/57 | right okay i am sorry to hear there is a lot going on there and i can see why it is affecting you so you mentioned [it→you] [has→have] been [going→getting] [on→it] for [+the] last 3 days mainly the burning pain when you pass urine you [said→have] [you→been] [-are] going to the toilet more often as well [+is] that right |
| `primock57:day3_consultation01:patient:0052:telephony_mulaw` | patient | 9/27 | no [i→well] [i→well] [-got] [-no] i [do→think] sometimes but i do not know which [ones→one] [but→so] i have a peanut allergy as well like [+i] [+have] always had it |
| `primock57:day5_consultation07:doctor:0082:telephony_mulaw` | doctor | 9/8 | okay [+i] [+am] [+going] [who→to] [do→reach] you [live→later] [with→that] [at→time] [-home] |
| `primock57:day1_consultation06:doctor:0069:telephony_mulaw` | doctor | 8/28 | [+even] [you→i] [have→get] [been→symptom] okay [since→all] [then→right] [-okay] [-alright] so apart from the the heart the heart problems the heart failure any other problems i should be aware of |
| `primock57:day1_consultation13:doctor:0081:telephony_mulaw` | doctor | 8/41 | okay all right [something→feel] [for→free] [-you] to bear in mind if you feel [that→like] [-you] [-are] your eyes are straining i [would→will] always recommend having a repeat eye test done have you been [-feeling] more stressed or anxious at work recently |
