# Offline STT accuracy report

- **Generated:** 2026-11-05 00:21 UTC
- **Manifest:** `data/manifests/primock57.jsonl` (7108 utterances; excluded from scoring: inaudible 706, unintelligible 1147)
- **Profile:** `configs/profiles/healthcare_intake.yaml`
- **Normalizer (headline WER):** `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy,hyp-mdy`
- **Leaderboard-comparable WER:** `whisper-normalizer==0.1.15/EnglishTextNormalizer`
- **Intervals:** 95% paired percentile bootstrap, 10000 resamples, seed 0, resampling whole speakers. Pairwise p-values Holm-adjusted within each table. "Tie" = difference interval includes 0. No winner is called with fewer than 10 speakers in a table.
- **Failed requests** are scored as empty transcripts (every reference word deleted).
- **Empty on speech:** successful requests that returned no text although the normalized reference has words (Wilson interval, not clustered). An empty transcript for "Um." is correct and not counted. These rows are scored as they came back, never selectively re-run.

## Configurations

| Config | Provider | Model | Mode | Settings | Hyp. dates | Run | Recorded | Git |
|---|---|---|---|---|---|---|---|---|
| deepgram_nova3_batch | deepgram | `nova-3` | batch | `{"punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch | 2026-11-04 | `207cdd3` |
| deepgram_nova3_batch_keyterms | deepgram | `nova-3` | batch | `{"keyterms": "lexicon", "punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch-keyterms | 2026-11-04 | `8f09f37` |
| deepgram_nova3_batch_keyterms_common | deepgram | `nova-3` | batch | `{"keyterms": "profile", "punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch-keyterms-common | 2026-11-04 | `1d54f4d` |

## Real audio

### All real audio

114 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| deepgram_nova3_batch | 7.4% [6.8, 8.1] | 10.2% | 12.2% | 5255 | 56795 | 0 | 1.1% [0.9, 1.4] (57/5105) |
| deepgram_nova3_batch_keyterms | 7.4% [6.8, 8.1] | 10.2% | 12.2% | 5255 | 56795 | 0 | 1.2% [1.0, 1.6] (63/5105) |
| deepgram_nova3_batch_keyterms_common | 7.4% [6.8, 8.1] | 10.2% | 12.2% | 5255 | 56795 | 0 | 1.2% [0.9, 1.5] (60/5105) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms | +0.0 pp [-0.1, +0.1] | 0.9677 | 1.0000 | tie |
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms_common | +0.0 pp [-0.1, +0.1] | 1.0000 | 1.0000 | tie |
| deepgram_nova3_batch_keyterms − deepgram_nova3_batch_keyterms_common | -0.0 pp [-0.1, +0.1] | 0.9509 | 1.0000 | tie |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| deepgram_nova3_batch | medication | 74.2% [67.0, 80.3] | 121/163 | 12.4% | - |
| deepgram_nova3_batch | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms | medication | 87.7% [81.8, 91.9] | 143/163 | 6.4% | - |
| deepgram_nova3_batch_keyterms | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch_keyterms | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch_keyterms | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms_common | medication | 78.5% [71.6, 84.1] | 128/163 | 9.4% | - |
| deepgram_nova3_batch_keyterms_common | dosage | 93.8% [71.7, 98.9] | 15/16 | 0.9% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch_keyterms_common | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch_keyterms_common | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): deepgram_nova3_batch 4, deepgram_nova3_batch_keyterms 9, deepgram_nova3_batch_keyterms_common 9.

### doctor (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| deepgram_nova3_batch | 6.5% [5.7, 7.4] | 10.2% | 9.3% | 2615 | 33869 | 0 | 0.6% [0.4, 1.0] (16/2570) |
| deepgram_nova3_batch_keyterms | 6.6% [5.8, 7.5] | 10.3% | 9.3% | 2615 | 33869 | 0 | 0.7% [0.4, 1.1] (18/2570) |
| deepgram_nova3_batch_keyterms_common | 6.5% [5.7, 7.4] | 10.2% | 9.2% | 2615 | 33869 | 0 | 0.6% [0.4, 1.0] (16/2570) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms | -0.1 pp [-0.1, +0.0] | 0.2764 | 0.8291 | tie |
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms_common | -0.0 pp [-0.1, +0.1] | 0.9985 | 0.9985 | tie |
| deepgram_nova3_batch_keyterms − deepgram_nova3_batch_keyterms_common | +0.0 pp [-0.0, +0.1] | 0.3124 | 0.8291 | tie |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| deepgram_nova3_batch | medication | 76.6% [67.1, 84.0] | 72/94 | 10.0% | - |
| deepgram_nova3_batch | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch | phone | no instances | 0 | - | - |
| deepgram_nova3_batch_keyterms | medication | 90.4% [82.8, 94.9] | 85/94 | 5.1% | - |
| deepgram_nova3_batch_keyterms | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch_keyterms | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch_keyterms | phone | no instances | 0 | - | - |
| deepgram_nova3_batch_keyterms_common | medication | 79.8% [70.6, 86.7] | 75/94 | 8.6% | - |
| deepgram_nova3_batch_keyterms_common | dosage | 92.9% [68.5, 98.7] | 13/14 | 1.0% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch_keyterms_common | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch_keyterms_common | phone | no instances | 0 | - | - |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): deepgram_nova3_batch 1, deepgram_nova3_batch_keyterms 4, deepgram_nova3_batch_keyterms_common 4.

### patient (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| deepgram_nova3_batch | 8.7% [7.7, 9.9] | 10.2% | 15.2% | 2640 | 22926 | 0 | 1.6% [1.2, 2.2] (41/2535) |
| deepgram_nova3_batch_keyterms | 8.6% [7.7, 9.8] | 10.2% | 15.2% | 2640 | 22926 | 0 | 1.8% [1.3, 2.4] (45/2535) |
| deepgram_nova3_batch_keyterms_common | 8.7% [7.7, 9.9] | 10.2% | 15.3% | 2640 | 22926 | 0 | 1.7% [1.3, 2.3] (44/2535) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms | +0.1 pp [-0.0, +0.2] | 0.1584 | 0.3180 | tie |
| deepgram_nova3_batch − deepgram_nova3_batch_keyterms_common | +0.0 pp [-0.1, +0.1] | 0.9609 | 0.9609 | tie |
| deepgram_nova3_batch_keyterms − deepgram_nova3_batch_keyterms_common | -0.1 pp [-0.2, +0.0] | 0.1060 | 0.3180 | tie |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| deepgram_nova3_batch | medication | 71.0% [59.4, 80.4] | 49/69 | 15.9% | - |
| deepgram_nova3_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms | medication | 84.1% [73.7, 90.9] | 58/69 | 8.1% | - |
| deepgram_nova3_batch_keyterms | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch_keyterms | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms_common | medication | 76.8% [65.6, 85.2] | 53/69 | 10.5% | - |
| deepgram_nova3_batch_keyterms_common | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch_keyterms_common | date_of_birth | 90.5% [71.1, 97.3] | 19/21 | 3.5% | 90.5% [71.1, 97.3] |
| deepgram_nova3_batch_keyterms_common | phone | 50.0% [9.5, 90.5] | 1/2 | 26.7% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): deepgram_nova3_batch 3, deepgram_nova3_batch_keyterms 5, deepgram_nova3_batch_keyterms_common 5.

## Worst utterances

Normalized alignment: `[ref→hyp]` substitution, `[-ref]` deletion, `[+hyp]` insertion. Top 10 by error count per config.

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
| `primock57:day1_consultation10:doctor:0010` | doctor | 10/57 | right [-okay] i am sorry to hear there is a lot going on there and i can see why it is affecting you so you mentioned [it→you] [has→have] been [going→getting] [on→in] for [+the] last 3 days mainly the burning pain when you pass urine you [said→are] [you→just] [-are] going to the toilet more often as well [+is] that right |
| `primock57:day1_consultation10:doctor:0103` | doctor | 10/54 | sure and [obviously→as] as [your→you] [doctor→talk] [i→to] [am→somebody] [-here] to look after you so yeah i [-i] would strongly recommend you you know to avoid if you can great fine so at this [stage→point] i would not normally examine you but i think based on your story i think you know [+i] [+am] i am reassured |
| `primock57:day1_consultation13:doctor:0081` | doctor | 10/41 | okay [all→alright] [right→so] [something→feel] [for→free] [-you] to bear in mind if you feel [that→like] [-you] [-are] your eyes are straining i [would→will] always recommend having a repeat eye test done have you been [-feeling] more stressed or anxious at work recently |
| `primock57:day4_consultation05:patient:0015` | patient | 10/52 | yes so i have [+a] i have [+a] i do not know how do you say it properly in english i mean [+we] [+that] [+was] [without→from] [sounding→the] [good→google] like diarrhea for for yeah so it is lasting for like 3 days and yeah i i do not know i do not know what [could→would] because it [-i] |
| `primock57:day5_consultation08:doctor:0090` | doctor | 10/16 | [-who] [-do] you [live→deal] with do you live [on→with] [your→me] [own→right] [or→now] [do→deal] [-you] [-live] with |
| `primock57:day5_consultation10:patient:0032` | patient | 10/21 | i [was→would] [sick→say] [but→quite] [i→normal] [had→headaches] [-no] [-more] [-headache] [-it] [-is] just a bit of a pressure in between my eyes |
