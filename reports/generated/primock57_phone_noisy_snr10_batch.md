# Offline STT accuracy report

- **Generated:** 2026-11-05 10:26 UTC
- **Manifest:** `data/manifests/primock57.phone_noisy_snr10.jsonl` (5255 utterances)
- **Profile:** `configs/profiles/healthcare_intake.yaml`
- **Normalizer (headline WER):** `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy`, `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy,hyp-mdy`
- **Leaderboard-comparable WER:** `whisper-normalizer==0.1.15/EnglishTextNormalizer`
- **Intervals:** 95% paired percentile bootstrap, 10000 resamples, seed 0, resampling whole speakers. Pairwise p-values Holm-adjusted within each table. "Tie" = difference interval includes 0. No winner is called with fewer than 10 speakers in a table.
- **Failed requests** are scored as empty transcripts (every reference word deleted).
- **Empty on speech:** successful requests that returned no text although the normalized reference has words (Wilson interval, not clustered). An empty transcript for "Um." is correct and not counted. These rows are scored as they came back, never selectively re-run.

## Configurations

| Config | Provider | Model | Mode | Settings | Hyp. dates | Run | Recorded | Git |
|---|---|---|---|---|---|---|---|---|
| assemblyai_batch | assemblyai | `universal-3-5-pro` | batch | `{"format_text": true, "language_code": "en", "punctuate": true}` | as reference | assemblyai-batch | 2026-11-05 | `e7dabf6` |
| deepgram_nova3_batch | deepgram | `nova-3` | batch | `{"punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch | 2026-11-05 | `e7dabf6` |
| elevenlabs_scribe_v2_batch | elevenlabs | `scribe_v2` | batch | `{"language_code": "en", "temperature": 0}` | as reference | elevenlabs-scribe-v2-batch | 2026-11-05 | `e7dabf6` |

## Real audio

### All real audio

114 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 10.3% [9.4, 11.2] | 12.9% | 17.8% | 5255 | 56795 | 0 | 1.5% [1.2, 1.8] (75/5105) |
| deepgram_nova3_batch | 17.1% [15.7, 18.6] | 19.7% | 25.6% | 5255 | 56795 | 0 | 2.4% [2.0, 2.9] (123/5105) |
| elevenlabs_scribe_v2_batch | 10.7% [9.7, 11.8] | 13.3% | 19.2% | 5255 | 56795 | 0 | 1.5% [1.2, 1.9] (77/5105) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -6.8 pp [-7.7, -6.0] | 0.0002 | 0.0006 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | -0.4 pp [-0.8, -0.0] | 0.0486 | 0.0486 | assemblyai_batch better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +6.4 pp [+5.7, +7.1] | 0.0002 | 0.0006 | elevenlabs_scribe_v2_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 76.1% [69.0, 82.0] | 124/163 | 15.7% | - |
| assemblyai_batch | dosage | 87.5% [64.0, 96.5] | 14/16 | 6.4% | 68.8% [44.4, 85.8] |
| assemblyai_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.5% | 85.7% [65.4, 95.0] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 46.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 53.4% [45.7, 60.9] | 87/163 | 32.8% | - |
| deepgram_nova3_batch | dosage | 75.0% [50.5, 89.8] | 12/16 | 15.5% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch | date_of_birth | 76.2% [54.9, 89.4] | 16/21 | 9.3% | 76.2% [54.9, 89.4] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 40.0% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | medication | 68.1% [60.6, 74.8] | 111/163 | 20.1% | - |
| elevenlabs_scribe_v2_batch | dosage | 87.5% [64.0, 96.5] | 14/16 | 6.4% | 6.2% [1.1, 28.3] |
| elevenlabs_scribe_v2_batch | date_of_birth | 76.2% [54.9, 89.4] | 16/21 | 8.8% | 28.6% [13.8, 50.0] |
| elevenlabs_scribe_v2_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 53.3% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 0, elevenlabs_scribe_v2_batch 1.

### doctor (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 8.6% [7.6, 9.6] | 12.0% | 13.7% | 2615 | 33869 | 0 | 0.9% [0.6, 1.4] (24/2570) |
| deepgram_nova3_batch | 15.2% [13.3, 17.1] | 18.5% | 21.1% | 2615 | 33869 | 0 | 2.0% [1.5, 2.6] (51/2570) |
| elevenlabs_scribe_v2_batch | 8.9% [7.8, 10.0] | 12.4% | 14.9% | 2615 | 33869 | 0 | 0.6% [0.4, 1.0] (16/2570) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -6.6 pp [-7.8, -5.6] | 0.0002 | 0.0006 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | -0.3 pp [-0.8, +0.1] | 0.1360 | 0.1360 | tie |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +6.3 pp [+5.2, +7.4] | 0.0002 | 0.0006 | elevenlabs_scribe_v2_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 79.8% [70.6, 86.7] | 75/94 | 12.5% | - |
| assemblyai_batch | dosage | 85.7% [60.1, 96.0] | 12/14 | 6.9% | 64.3% [38.8, 83.7] |
| assemblyai_batch | date_of_birth | no instances | 0 | - | - |
| assemblyai_batch | phone | no instances | 0 | - | - |
| deepgram_nova3_batch | medication | 60.6% [50.5, 69.9] | 57/94 | 24.4% | - |
| deepgram_nova3_batch | dosage | 71.4% [45.4, 88.3] | 10/14 | 16.8% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch | phone | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch | medication | 74.5% [64.8, 82.2] | 70/94 | 15.0% | - |
| elevenlabs_scribe_v2_batch | dosage | 85.7% [60.1, 96.0] | 12/14 | 6.9% | 7.1% [1.3, 31.5] |
| elevenlabs_scribe_v2_batch | date_of_birth | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch | phone | no instances | 0 | - | - |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 0, deepgram_nova3_batch 0, elevenlabs_scribe_v2_batch 0.

### patient (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 12.9% [11.5, 14.4] | 14.1% | 22.0% | 2640 | 22926 | 0 | 2.0% [1.5, 2.6] (51/2535) |
| deepgram_nova3_batch | 19.9% [17.8, 22.2] | 21.3% | 30.1% | 2640 | 22926 | 0 | 2.8% [2.3, 3.6] (72/2535) |
| elevenlabs_scribe_v2_batch | 13.4% [11.7, 15.3] | 14.6% | 23.5% | 2640 | 22926 | 0 | 2.4% [1.9, 3.1] (61/2535) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -7.0 pp [-8.4, -5.8] | 0.0002 | 0.0006 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | -0.5 pp [-1.3, +0.2] | 0.1800 | 0.1800 | tie |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +6.5 pp [+5.6, +7.5] | 0.0002 | 0.0006 | elevenlabs_scribe_v2_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 71.0% [59.4, 80.4] | 49/69 | 20.1% | - |
| assemblyai_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| assemblyai_batch | date_of_birth | 85.7% [65.4, 95.0] | 18/21 | 7.5% | 85.7% [65.4, 95.0] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 46.7% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 43.5% [32.4, 55.2] | 30/69 | 44.6% | - |
| deepgram_nova3_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | date_of_birth | 76.2% [54.9, 89.4] | 16/21 | 9.3% | 76.2% [54.9, 89.4] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 40.0% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | medication | 59.4% [47.6, 70.2] | 41/69 | 27.3% | - |
| elevenlabs_scribe_v2_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | date_of_birth | 76.2% [54.9, 89.4] | 16/21 | 8.8% | 28.6% [13.8, 50.0] |
| elevenlabs_scribe_v2_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 53.3% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 0, elevenlabs_scribe_v2_batch 1.

## Worst utterances

Normalized alignment: `[ref→hyp]` substitution, `[-ref]` deletion, `[+hyp]` insertion. Top 10 by error count per config.

### assemblyai_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation10:doctor:0010:phone_noisy_snr10` | doctor | 20/57 | [right→unfortunately] [okay→it] [-i] [-am] [-sorry] [-to] [-hear] [-there] is [a→not] [-lot] going on there and i can see why it is affecting you [-so] you mentioned [it→you] [has→have] been going [on→over] [for→the] last 3 days mainly the burning pain when you pass urine you [said→used] [you→to] [are→be] going to the toilet more often as well [-that] [-right] |
| `primock57:day2_consultation05:patient:0015:phone_noisy_snr10` | patient | 20/30 | and i [do→just] [-not] [-know] [-what] [-is] [-causing] [-them] i have googled [it→this] and nothing is coming up [-so] [-i] [-thought] [-i] [-would] [-come] [-and] [-speak] [-to] [-you] [-about] [-it] |
| `primock57:day1_consultation07:doctor:0096:phone_noisy_snr10` | doctor | 17/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day1_consultation07:patient:0083:phone_noisy_snr10` | patient | 14/36 | you know [-you] [-know] i have [-i] [-have] got a wee bit [a→around] [-wee] [-bit] [-round] the midriff the spare tire is definitely there and [-i] [-have] [-i] [-have] [-got] [-the] i have got the diabetes |
| `primock57:day5_consultation08:doctor:0090:phone_noisy_snr10` | doctor | 14/16 | [who→you] [do→need] [you→to] [live→leave] [with→but] [-do] you [live→left] [on→me] [your→i] [own→know] [-or] [-do] you [live→did] [-with] |
| `primock57:day1_consultation05:doctor:0099:phone_noisy_snr10` | doctor | 13/45 | could [just→this] be a [-you] [-know] [-could] [-just] [-be] [-a] urine infection for example could [just→this] be something related to [your→his] gut could [just→this] be something related to your [-you] [-know] [-a] pregnancy related because and so it is probably worth doing some tests initially |
| `primock57:day4_consultation01:patient:0018:phone_noisy_snr10` | patient | 13/16 | i [would→will] say [that→this] [it→now] [-is] [-come] [-on] quite [suddenly→sudden] i [+did] [was→not] [digging→even] [in→know] [the→about] [garden→it] |
| `primock57:day1_consultation08:patient:0027:phone_noisy_snr10` | patient | 12/10 | i [+do] [+not] think [+that] [+is] [the→something] [kids→that] [have→you] [been→and] [really→i] [annoying→need] [these→to] [days→say] |
| `primock57:day3_consultation01:patient:0057:phone_noisy_snr10` | patient | 12/31 | yeah [is→the] [that→play] [-well] [-i] was like 6 or something i i i think [ohh→0] sorry [the→it] [-swelling] is [getting→falling] [ohh→again] [my→00] [-god] [-ohh] yeah i think when i was 6 |
| `primock57:day4_consultation05:patient:0049:phone_noisy_snr10` | patient | 12/36 | yes but [-yes] [-but] i [-i] go to the toilet [also→so] often so i [-i] [-i] [-yeah] [-i] try not to eat a lot because i [-yeah] [-i] just [going→went] to the toilet every 10 [minute→minutes] |

### deepgram_nova3_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day2_consultation02:doctor:0070:phone_noisy_snr10` | doctor | 46/51 | [-from] [-now] [-but] [-it] [-may] [-take] [-time] [-for] the [form→results] [-to] [-come] [-out] [-to] [-you] [-and] [-if] [-you] [-get] [-the] [-form] [-get] [-the] [-blood] [-tests] [-done] [-straight] [-away] [-by] [-the] [-time] that [we→looking] [are→at] [-expecting] [-result] [-back] [-you] [-know] [-one] [-or] [-2] [-days] [-after] [-that] [-we] [-are] [-looking] maybe 6 days |
| `primock57:day1_consultation10:doctor:0010:phone_noisy_snr10` | doctor | 33/57 | [-right] [-okay] [-i] [-am] [-sorry] [-to] [-hear] [-there] [-is] [-a] [-lot] [-going] [-on] [-there] [-and] [-i] [-can] [-see] [-why] [-it] [-is] [-affecting] you [so→mentioned] you [mentioned→have] [-it] [-has] been [going→there] [on→for] [for→the] last 3 days mainly the burning pain when you pass urine you [-said] [-you] are [going→speaking] to the toilet more often as well [+is] that right |
| `primock57:day2_consultation02:doctor:0050:phone_noisy_snr10` | doctor | 30/30 | [-right] [-okay] [-and] [-if] [-you] [-can] [-just] [-raise] [-your] [-elbow] [-up] [-a] [-little] [-bit] [-like] [-that] [-a] [-bit] [-higher] [-so] [-i] [-can] [-just] [-see] [-the] [-underside] [-okay] [-fantastic] [-all] [-right] |
| `primock57:day1_consultation07:doctor:0096:phone_noisy_snr10` | doctor | 27/17 | [+yeah] [+okay] [+so] [+you] [+were] [+waiting] [45→that] [days→month] [ago→that] [yeah→your] [okay→symptoms] are [+off] [+is] [+it] [+something] you [aware→have] [of→you] [anything→have] [that→eaten] [might→or] have [+you] [+been] [+traveling] [set→recently] [your→abroad] [symptoms→or] [off→.] |
| `primock57:day1_consultation10:doctor:0103:phone_noisy_snr10` | doctor | 26/54 | sure and [+i] [obviously→am] [as→going] [your→to] [doctor→talk] [i→to] [am→somebody] [here→who] [to→can] [look→talk] [after→to] you [so→i] [yeah→will] [i→just] [i→want] [would→to] [-strongly] recommend you [-you] [-know] to avoid [if→it] [-you] [-can] [-great] fine so at this stage [-i] would not normally examine you but i think based on your story i think [-you] [-know] i am reassured |
| `primock57:day3_consultation07:doctor:0032:phone_noisy_snr10` | doctor | 26/26 | [-yeah] [-so] [-you] [-have] [-cracks] [-over] [-there] [-okay] [-and] [-is] [-there] [-any] [-scratch] [-marks] [-on] [-your] [-on] [-any] [-of] [-the] [-you] [-know] [-areas] [-any] [-scratch] [-marks] |
| `primock57:day1_consultation05:doctor:0099:phone_noisy_snr10` | doctor | 23/45 | [could→it] [-just] be a [-you] [-know] [-could] [-just] [-be] [-a] urine infection for example could [just→it] be something related to your [-gut] [-could] [-just] [-be] [-something] [-related] [-to] [-your] [-you] [-know] [-a] pregnancy related because and so it is probably worth [doing→thinking] [some→test] [-tests] initially |
| `primock57:day4_consultation07:doctor:0085:phone_noisy_snr10` | doctor | 23/23 | [-and] [-you] [-are] [-a] [-little] [-bit] [-concerned] [-about] [-that] [-but] [-you] [-have] [-not] [-you] [-have] [-not] [-lost] [-any] [-weight] [-that] [-you] [-think] [-of] |
| `primock57:day5_consultation03:patient:0067:phone_noisy_snr10` | patient | 20/29 | yeah i mean i [find→am] [public→having] [transport→trouble] [really→with] [stressful→transport] [anyway→but] [especially→just] being on the [tube→cheap] [-it] [-is] [-because] [-it] [-is] [-quite] getting warmer [so→to] [it→the] [is→airline] [-just] [-really] [-airless] |
| `primock57:day1_consultation04:doctor:0063:phone_noisy_snr10` | doctor | 19/38 | okay fine [what→when] [i→we] [am→are] [going→done] [-to] [-do] i am [-just] going to run through a few [yes→yesno] [-no] questions [-if] you [-if] [-you] do not mind [just→if] [a→need] [review→assistance] [-of] [-your] [-systems] [-any] any headaches at all |

### elevenlabs_scribe_v2_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day4_consultation05:patient:0049:phone_noisy_snr10` | patient | 37/36 | [+yy] [+jest] [+pa] [yes→jest] [but→pa] [yes→taj] [but→aj] [i→ku] [i→0] [go→se] to [the→je] [toilet→to] [also→ko] [often→ko] [so→ohen] [i→to] [i→aj] [i→aj] [yeah→aj] [i→ja] [try→aj] [not→treba] to [+biti] [eat→los] [a→jer] [lot→to] [because→aj] [i→ja] [yeah→aj] [i→ku] [just→0] [going→se] to [the→je] [toilet→to] [every→je] [10→tebi] [minute→emi] |
| `primock57:day1_consultation07:doctor:0096:phone_noisy_snr10` | doctor | 19/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day5_consultation03:patient:0090:phone_noisy_snr10` | patient | 18/56 | maybe i maybe i do have like a bit during the week [like→that] my parents [+look] [+after] [obviously→me] [are→or] retired so they just [+look] [+after] [drink→me] whenever they want so whenever they are [having→free] [a→that] [glass→is] [of→fine] [-wine] they will offer [it→to] [to→see] me and [it→stuff] [is→like] [like→that] i guess i do not really keep track of it that much |
| `primock57:day1_consultation10:doctor:0010:phone_noisy_snr10` | doctor | 17/57 | [right→yeah] [-okay] i am [sorry→pleased] to hear [there→it] is [a→not] [lot→day] [going→one] [on→though] [-there] and i can see why it is affecting you so you mentioned [it→you] [has→have] been going [on→for] [for→the] last 3 days mainly the burning pain when you pass urine you [said→have] [you→been] [-are] going to the toilet more often as well [+is] that right |
| `primock57:day1_consultation14:patient:0018:phone_noisy_snr10` | patient | 16/33 | i do not think so like i guess [i→like] [get→it] [labored→flavors] [when→what] i am [coughing→cooking] [and→in] [i→my] [can→calories] [-not] [-breathe] but i not yeah [not→no] i i do not think [+it] [+is] [so→ever] [not→a] [really→problem] |
| `primock57:day2_consultation05:patient:0015:phone_noisy_snr10` | patient | 16/30 | and i [do→just] [not→was] [know→in] [-what] [-is] [-causing] them i have googled it and nothing is coming up so i [thought→think] [i→it] [would→is] [come→advanced] [-and] [-speak] [-to] [-you] [-about] [-it] |
| `primock57:day5_consultation08:doctor:0090:phone_noisy_snr10` | doctor | 15/16 | [who→we] [do→did] [you→it] [live→but] [with→did] [do→it] you [live→know] [on→i] [your→know] [own→did] [or→it] [-do] [-you] [-live] [-with] |
| `primock57:day1_consultation07:patient:0083:phone_noisy_snr10` | patient | 14/36 | you know [-you] [-know] i have [-i] [-have] got a wee bit [a→around] [-wee] [-bit] [-round] the midriff the spare tire is definitely there and [-i] [-have] [-i] [-have] [-got] [-the] i have got the diabetes |
| `primock57:day4_consultation05:patient:0094:phone_noisy_snr10` | patient | 13/67 | okay i did not yeah sorry [i→about] [did→it] [-not] no i was saying i did not have any fever recently i i was sweating a little bit [-the] last [4→for] [days→bed] but i i not sure if if i had [+a] bit of fever but very little or [-or] [-i] [-am] [-i] [-am] but i do not think so i do not think i do not [-know] maybe |
| `primock57:day5_consultation03:patient:0067:phone_noisy_snr10` | patient | 13/29 | yeah i mean i find [+it] [+quite] [+uncomfortable] [public→just] [transport→but] [really→in] [stressful→a] [anyway→way] especially being on the tube [+because] it is [because→quite] it is [-quite] getting warmer [-so] it is [-just] really airless |
