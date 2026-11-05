# Offline STT accuracy report

- **Generated:** 2026-11-05 10:26 UTC
- **Manifest:** `data/manifests/primock57.phone_noisy_snr5.jsonl` (5255 utterances)
- **Profile:** `configs/profiles/healthcare_intake.yaml`
- **Normalizer (headline WER):** `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy`, `whisper-normalizer==0.1.15/EnglishTextNormalizer+equiv-v4/dmy,hyp-mdy`
- **Leaderboard-comparable WER:** `whisper-normalizer==0.1.15/EnglishTextNormalizer`
- **Intervals:** 95% paired percentile bootstrap, 10000 resamples, seed 0, resampling whole speakers. Pairwise p-values Holm-adjusted within each table. "Tie" = difference interval includes 0. No winner is called with fewer than 10 speakers in a table.
- **Failed requests** are scored as empty transcripts (every reference word deleted).
- **Empty on speech:** successful requests that returned no text although the normalized reference has words (Wilson interval, not clustered). An empty transcript for "Um." is correct and not counted. These rows are scored as they came back, never selectively re-run.

## Configurations

| Config | Provider | Model | Mode | Settings | Hyp. dates | Run | Recorded | Git |
|---|---|---|---|---|---|---|---|---|
| assemblyai_batch | assemblyai | `universal-3-5-pro` | batch | `{"format_text": true, "language_code": "en", "punctuate": true}` | as reference | assemblyai-batch | 2026-11-05 | `f7aa43e` |
| deepgram_nova3_batch | deepgram | `nova-3` | batch | `{"punctuate": true, "smart_format": true}` | mdy | deepgram-nova3-batch | 2026-11-05 | `f7aa43e` |
| elevenlabs_scribe_v2_batch | elevenlabs | `scribe_v2` | batch | `{"language_code": "en", "temperature": 0}` | as reference | elevenlabs-scribe-v2-batch | 2026-11-05 | `0a4a9f7` |

## Real audio

### All real audio

114 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 12.6% [11.6, 13.8] | 15.1% | 21.1% | 5255 | 56795 | 0 | 2.4% [2.1, 2.9] (125/5105) |
| deepgram_nova3_batch | 22.2% [20.4, 24.1] | 24.6% | 31.1% | 5255 | 56795 | 0 | 3.9% [3.4, 4.5] (200/5105) |
| elevenlabs_scribe_v2_batch | 13.3% [12.2, 14.6] | 15.9% | 22.7% | 5255 | 56795 | 0 | 2.2% [1.9, 2.7] (114/5105) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -9.6 pp [-10.6, -8.6] | 0.0002 | 0.0006 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | -0.7 pp [-1.2, -0.3] | 0.0006 | 0.0006 | assemblyai_batch better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +8.9 pp [+8.0, +9.9] | 0.0002 | 0.0006 | elevenlabs_scribe_v2_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 73.0% [65.7, 79.2] | 119/163 | 18.0% | - |
| assemblyai_batch | dosage | 87.5% [64.0, 96.5] | 14/16 | 6.4% | 68.8% [44.4, 85.8] |
| assemblyai_batch | date_of_birth | 81.0% [60.0, 92.3] | 17/21 | 10.2% | 81.0% [60.0, 92.3] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 53.3% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 42.3% [35.0, 50.0] | 69/163 | 43.9% | - |
| deepgram_nova3_batch | dosage | 68.8% [44.4, 85.8] | 11/16 | 21.8% | 0.0% [0.0, 19.4] |
| deepgram_nova3_batch | date_of_birth | 66.7% [45.4, 82.8] | 14/21 | 17.3% | 66.7% [45.4, 82.8] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 40.0% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | medication | 65.6% [58.1, 72.5] | 107/163 | 23.8% | - |
| elevenlabs_scribe_v2_batch | dosage | 81.2% [57.0, 93.4] | 13/16 | 7.3% | 0.0% [0.0, 19.4] |
| elevenlabs_scribe_v2_batch | date_of_birth | 76.2% [54.9, 89.4] | 16/21 | 9.7% | 42.9% [24.5, 63.5] |
| elevenlabs_scribe_v2_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 53.3% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 0, elevenlabs_scribe_v2_batch 2.

### doctor (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 10.7% [9.4, 12.1] | 14.1% | 16.6% | 2615 | 33869 | 0 | 1.6% [1.1, 2.1] (40/2570) |
| deepgram_nova3_batch | 20.8% [18.3, 23.4] | 23.8% | 27.5% | 2615 | 33869 | 0 | 3.3% [2.6, 4.0] (84/2570) |
| elevenlabs_scribe_v2_batch | 11.5% [10.1, 13.1] | 14.9% | 18.1% | 2615 | 33869 | 0 | 1.2% [0.8, 1.7] (30/2570) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -10.1 pp [-11.5, -8.7] | 0.0002 | 0.0006 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | -0.8 pp [-1.4, -0.3] | 0.0024 | 0.0024 | assemblyai_batch better |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +9.3 pp [+7.9, +10.6] | 0.0002 | 0.0006 | elevenlabs_scribe_v2_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 80.9% [71.7, 87.5] | 76/94 | 12.7% | - |
| assemblyai_batch | dosage | 85.7% [60.1, 96.0] | 12/14 | 6.9% | 64.3% [38.8, 83.7] |
| assemblyai_batch | date_of_birth | no instances | 0 | - | - |
| assemblyai_batch | phone | no instances | 0 | - | - |
| deepgram_nova3_batch | medication | 50.0% [40.1, 59.9] | 47/94 | 35.0% | - |
| deepgram_nova3_batch | dosage | 64.3% [38.8, 83.7] | 9/14 | 23.8% | 0.0% [0.0, 21.5] |
| deepgram_nova3_batch | date_of_birth | no instances | 0 | - | - |
| deepgram_nova3_batch | phone | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch | medication | 73.4% [63.7, 81.3] | 69/94 | 17.5% | - |
| elevenlabs_scribe_v2_batch | dosage | 78.6% [52.4, 92.4] | 11/14 | 7.9% | 0.0% [0.0, 21.5] |
| elevenlabs_scribe_v2_batch | date_of_birth | no instances | 0 | - | - |
| elevenlabs_scribe_v2_batch | phone | no instances | 0 | - | - |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 0, deepgram_nova3_batch 0, elevenlabs_scribe_v2_batch 1.

### patient (real)

57 speakers.

| Config | WER [95% CI] | WER, Whisper-only | Mean utterance WER | Utterances | Ref words | Failed | Empty on speech [95% CI] |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 15.4% [13.8, 17.2] | 16.7% | 25.7% | 2640 | 22926 | 0 | 3.4% [2.7, 4.1] (85/2535) |
| deepgram_nova3_batch | 24.3% [21.9, 26.8] | 25.7% | 34.7% | 2640 | 22926 | 0 | 4.6% [3.8, 5.5] (116/2535) |
| elevenlabs_scribe_v2_batch | 16.0% [14.1, 18.0] | 17.2% | 27.3% | 2640 | 22926 | 0 | 3.3% [2.7, 4.1] (84/2535) |

| Pair (A − B) | WER difference [95% CI] | p | p (Holm) | Verdict |
|---|---|---|---|---|
| assemblyai_batch − deepgram_nova3_batch | -8.9 pp [-10.3, -7.6] | 0.0002 | 0.0006 | assemblyai_batch better |
| assemblyai_batch − elevenlabs_scribe_v2_batch | -0.6 pp [-1.3, +0.2] | 0.1416 | 0.1416 | tie |
| deepgram_nova3_batch − elevenlabs_scribe_v2_batch | +8.3 pp [+7.2, +9.5] | 0.0002 | 0.0006 | elevenlabs_scribe_v2_batch better |

Entities (recall = every word of the entity correct; CER = character error rate on the entity; formatted = recalled and written as digits):

| Config | Category | Recall [95% CI] | n | CER | Formatted [95% CI] |
|---|---|---|---|---|---|
| assemblyai_batch | medication | 62.3% [50.5, 72.8] | 43/69 | 25.4% | - |
| assemblyai_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 100.0% [34.2, 100.0] |
| assemblyai_batch | date_of_birth | 81.0% [60.0, 92.3] | 17/21 | 10.2% | 81.0% [60.0, 92.3] |
| assemblyai_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 53.3% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | medication | 31.9% [22.1, 43.6] | 22/69 | 56.5% | - |
| deepgram_nova3_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| deepgram_nova3_batch | date_of_birth | 66.7% [45.4, 82.8] | 14/21 | 17.3% | 66.7% [45.4, 82.8] |
| deepgram_nova3_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 40.0% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | medication | 55.1% [43.4, 66.2] | 38/69 | 32.6% | - |
| elevenlabs_scribe_v2_batch | dosage | 100.0% [34.2, 100.0] | 2/2 | 0.0% | 0.0% [0.0, 65.8] |
| elevenlabs_scribe_v2_batch | date_of_birth | 76.2% [54.9, 89.4] | 16/21 | 9.7% | 42.9% [24.5, 63.5] |
| elevenlabs_scribe_v2_batch | phone | 50.0% [9.5, 90.5] | 1/2 | 53.3% | 0.0% [0.0, 65.8] |

Keyterms written where the speaker didn't say them (each run's own boost list from run.json; runs without boosting are counted against the profile's boost list as a baseline): assemblyai_batch 1, deepgram_nova3_batch 0, elevenlabs_scribe_v2_batch 1.

## Worst utterances

Normalized alignment: `[ref→hyp]` substitution, `[-ref]` deletion, `[+hyp]` insertion. Top 10 by error count per config.

### assemblyai_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day1_consultation10:doctor:0010:phone_noisy_snr5` | doctor | 34/57 | [-right] [-okay] [-i] [-am] [-sorry] [-to] [-hear] [-there] [-is] [-a] [-lot] [-going] [-on] [-there] [-and] [-i] [-can] [-see] [-why] [-it] [-is] [-affecting] you [so→mentioned] you [mentioned→have] [-it] [-has] been [going→getting] [on→this] for [+the] last 3 days mainly the burning pain when you pass urine you [said→used] [you→to] [are→be] going to the toilet more often as well [-that] [-right] |
| `primock57:day2_consultation05:patient:0015:phone_noisy_snr5` | patient | 20/30 | and i [do→just] [not→for] [know→some] [what→reason] [-is] [-causing] [-them] i have googled [it→this] and nothing is coming up [-so] [-i] [-thought] [-i] [-would] [-come] [-and] [-speak] [-to] [-you] [-about] [-it] |
| `primock57:day5_consultation03:patient:0090:phone_noisy_snr5` | patient | 20/56 | maybe [-i] maybe i do have like a bit during the week [like→but] my parents [-obviously] are retired so they just [drink→do] [whenever→whatever] they want so whenever [+their] [they→things] are [having→offline] [a→they] [glass→are] [of→a] [wine→lot] [they→harder] [-will] [-offer] [-it] to [me→see] [-and] [-it] [-is] like i guess i do not really keep track of it that much |
| `primock57:day1_consultation07:doctor:0096:phone_noisy_snr5` | doctor | 17/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day1_consultation07:patient:0083:phone_noisy_snr5` | patient | 17/36 | you know [-you] [-know] i have [-i] [-have] got a wee bit [a→around] [-wee] [-bit] [-round] the midriff [the→of] spare [tire→tires] [-is] definitely there and [-i] [-have] [-i] [-have] [-got] [-the] i have got the diabetes |
| `primock57:day5_consultation03:patient:0067:phone_noisy_snr5` | patient | 17/29 | yeah i mean i [+kind] [+of] [+feel] [find→like] [public→comfort] [transport→food] [really→is] [stressful→chocolate] anyway especially being on the tube it is [-because] [-it] [-is] [-quite] getting warmer [-so] [-it] [-is] [-just] really [airless→early] |
| `primock57:day1_consultation05:doctor:0088:phone_noisy_snr5` | doctor | 15/23 | we have [-we] [-have] covered the [majority→georgism] [-of] [-them] already but [i→you] [just→can] [want→make] [to→it] [make→up] [sure→a] [i→little] [am→bit] [not→for] [-missing] anything else |
| `primock57:day1_consultation06:doctor:0069:phone_noisy_snr5` | doctor | 15/28 | [you→even] [have→i] [been→get] [okay→things] [since→that] [then→they] [okay→can] [alright→not] [so→always] apart from the [-the] heart the heart problems the heart failure any other problems [-i] [-should] [-be] [-aware] [-of] |
| `primock57:day5_consultation03:patient:0033:phone_noisy_snr5` | patient | 15/37 | probably not significant changes maybe no i would not say that i would not say that [i→the] [am→game] [-eating] like [much→scratched] differently [ohh→0] [that→i] [i→have] probably [have→had] more [+top] [chocolate→clips] than normal [-just] [-because] [-i] [-feel] so [down→chill] |
| `primock57:day1_consultation06:doctor:0045:phone_noisy_snr5` | doctor | 14/32 | [and→as] [some→the] swelling in your [+ankle] [ankles→so] [reporting→importantly] no chest pain and [and→again] have you [-had] [-any] [-have] [-you] [-any] [-have] [-you] noticed your heartbeat racing at all so palpitations or [-skipped] heartbeat |

### deepgram_nova3_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day2_consultation04:doctor:0149:phone_noisy_snr5` | doctor | 50/50 | [-45] [-okay] [-it] [-is] [-something] [-we] [-do] [-need] [-to] [-be] [-cognisant] [-of] [-okay] [-and] [-we] [-may] [-end] [-up] [-having] [-to] [-do] [-a] [-follow] [-up] [-chest] [-x] [-ray] [-if] [-things] [-do] [-not] [-settle] [-down] [-but] [-at] [-the] [-moment] [-it] [-it] [-seems] [-more] [-like] [-a] [-chest] [-infection] [-rather] [-than] [-a] [-lung] [-cancer] |
| `primock57:day2_consultation02:doctor:0070:phone_noisy_snr5` | doctor | 49/51 | [-from] [-now] [-but] [-it] [-may] [-take] [-time] [-for] [-the] [-form] [-to] [-come] [-out] [-to] [-you] and [if→we] [you→will] [get→next] [the→of] [form→we] [get→will] [the→looking] [blood→looking] [tests→at] [-done] [-straight] [-away] [-by] the [time→couple] [that→couple] [we→and] [-are] [-expecting] [-result] [-back] [-you] [-know] [-one] [-or] [-2] [-days] [-after] [-that] [-we] [-are] [-looking] [-maybe] [-6] [-days] |
| `primock57:day1_consultation10:doctor:0010:phone_noisy_snr5` | doctor | 36/57 | [-right] [-okay] [-i] [-am] [-sorry] [-to] [-hear] [-there] [-is] [-a] [-lot] [-going] [-on] [-there] [-and] [-i] [-can] [-see] [-why] [-it] [-is] [-affecting] you [so→mentioned] you [mentioned→have] [-it] [-has] been [going→doing] [on→it] for [+the] last 3 days mainly the burning pain when you pass urine you [said→just] [you→begin] [-are] [-going] to [-the] toilet more often as well [-that] [-right] |
| `primock57:day1_consultation10:doctor:0103:phone_noisy_snr5` | doctor | 33/54 | [-sure] [-and] [-obviously] [-as] [-your] [-doctor] [-i] [-am] [-here] [-to] [-look] [-after] [-you] [-so] [-yeah] [-i] [-i] [-would] [-strongly] [-recommend] [-you] [-you] [-know] [-to] [-avoid] [-if] [-you] [-can] great fine so [at→as] [this→i] [stage→said] i would not normally examine you but i think based on your story i think [-you] [-know] i am reassured |
| `primock57:day1_consultation07:doctor:0096:phone_noisy_snr5` | doctor | 29/17 | [45→okay] [-days] [-ago] yeah okay [are→so] you [+were] [aware→waiting] [of→that] [anything→month] that [+your] [+symptoms] [+are] [+off] [+so] [+is] [+it] [+something] [might→you] have [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [set→recently] [your→abroad] [symptoms→or] [off→.] |
| `primock57:day1_consultation06:doctor:0069:phone_noisy_snr5` | doctor | 28/28 | [you→we] [have→are] [been→going] [okay→to] [since→get] [then→some] [-okay] [-alright] [-so] [-apart] [-from] [-the] [-the] [-heart] [-the] [-heart] [-problems] [-the] [-heart] [-failure] [-any] [-other] [-problems] [-i] [-should] [-be] [-aware] [-of] |
| `primock57:day5_consultation03:patient:0090:phone_noisy_snr5` | patient | 28/56 | maybe [-i] maybe i do have like a [bit→picture] [during→of] [the→people] [week→that] [-like] [-my] [-parents] [-obviously] are [retired→tired] [-so] [-they] [-just] [-drink] whenever they want so whenever they are [having→playing] [a→offline] [-glass] [-of] [-wine] they will offer [it→a] [to→scene] [-me] [-and] [-it] [-is] like i guess [i→they] do not really keep track [-of] [-it] that much |
| `primock57:day1_consultation05:doctor:0099:phone_noisy_snr5` | doctor | 25/45 | [-could] [-just] [-be] a [-you] [-know] [-could] [-just] [-be] [-a] urine infection for example could [just→it] be something related to your [gut→it] [could→pregnancy] [-just] [-be] [-something] related to [your→it] [-you] [-know] [-a] [-pregnancy] [-related] [-because] and so it is probably [worth→working] [doing→from] [-some] tests initially |
| `primock57:day1_consultation08:doctor:0053:phone_noisy_snr5` | doctor | 23/23 | [-okay] [-all] [-right] [-so] [-just] [-moving] [-on] [-in] [-terms] [-of] [-your] [-other] [-medical] [-history] [-is] [-there] [-anything] [-else] [-i] [-should] [-be] [-aware] [-of] |
| `primock57:day2_consultation04:doctor:0131:phone_noisy_snr5` | doctor | 23/23 | [-no] [-okay] [-all] [-right] [-what] [-i] [-think] [-we] [-will] [-do] [-is] [-we] [-will] [-arrange] [-for] [-you] [-to] [-get] [-reviewed] [-in] [-a] [-clinic] [-today] |

### elevenlabs_scribe_v2_batch

| Utterance | Subset | Errors / ref words | Alignment |
|---|---|---|---|
| `primock57:day4_consultation05:patient:0049:phone_noisy_snr5` | patient | 35/36 | [+yy] [+jest] [yes→ba] [but→jest] [yes→ba] [but→taj] [i→aj] [i→kontej] [go→tore] to [the→osmes] [toilet→to] [also→aj] [often→aj] [so→aj] [i→ja] [i→aj] [i→treca] [yeah→su] i [try→te] [not→lokne] to [eat→aj] [a→ja] [lot→aj] [because→ker] [i→kontej] [yeah→tore] [i→te] [just→bi] [going→te] [to→bi] [-the] [-toilet] [-every] [-10] [-minute] |
| `primock57:day1_consultation10:doctor:0010:phone_noisy_snr5` | doctor | 32/57 | [right→so] [okay→you] [i→mentioned] [am→some] [sorry→symptoms] [to→that] [hear→they] [there→would] [is→not] [a→know] [lot→unless] [going→you] [on→have] [there→seen] [and→one] [i→for] [can→quite] [see→a] [why→few] [it→years] [-is] [-affecting] [-you] so you mentioned [it→you] [has→have] been going [on→for] [for→the] last 3 days mainly the burning pain when you pass urine you [said→just] [you→been] [-are] going to the toilet more often as well [-that] [-right] |
| `primock57:day2_consultation04:doctor:0149:phone_noisy_snr5` | doctor | 24/50 | [45→45%] [-okay] it is something we do need to be [cognisant→conscious] of okay and we may end up having to do a [follow→product] [up→temp] [chest→exchange] [x→in] [ray→the] [if→sense] [things→of] [do→that] [-not] [-settle] [-down] but at the moment it it seems more like [+it] [+is] [a→just] [chest→the] [infection→extra] [rather→charges] [than→that] [a→are] [lung→coming] [cancer→in] |
| `primock57:day5_consultation03:patient:0090:phone_noisy_snr5` | patient | 24/56 | maybe i [-maybe] [-i] do have like a bit during the week [like→where] my parents [+look] [+after] [obviously→me] [are→or] [retired→retire] [so→because] they just [drink→do] [whenever→whatever] they want so whenever they are [having→free] [-a] [-glass] [-of] [-wine] they will [offer→go] [it→for] [to→a] [me→meal] [and→but] [-it] [-is] [-like] i guess i do not really keep track of it that much |
| `primock57:day1_consultation06:doctor:0045:phone_noisy_snr5` | doctor | 22/32 | and [some→just] swelling in your ankles [+so] [reporting→importantly] no chest pain and and [+again] [have→if] you [had→if] [any→you] [have→go] [you→to] [any→your] [have→heart] [you→beat] [noticed→rate] [your→in] [heartbeat→the] [racing→pool] [at→so] [all→it] [so→is] palpitations or [+your] [skipped→heart] [heartbeat→beat] |
| `primock57:day5_consultation03:patient:0033:phone_noisy_snr5` | patient | 20/37 | probably [+there] [+is] [+a] [+lot] [not→of] significant changes maybe no i would not say that i would not say that [i→my] [am→eating] [eating→is] like [much→drastically] [differently→0] [-ohh] [-that] i probably [have→talk] more [+about] [chocolate→it] than normal [just→with] [because→the] [i→girls] [-feel] so [-down] |
| `primock57:day1_consultation07:doctor:0096:phone_noisy_snr5` | doctor | 19/17 | [+4] [+or] [45→5] days ago yeah okay are you aware of anything that might have set your symptoms off [+is] [+it] [+something] [+you] [+have] [+you] [+have] [+eaten] [+or] [+have] [+you] [+been] [+traveling] [+recently] [+abroad] [+or] |
| `primock57:day2_consultation05:patient:0015:phone_noisy_snr5` | patient | 18/30 | and i [do→just] [not→was] [know→thinking] [-what] [-is] [-causing] [-them] i have googled [it→this] and nothing is coming up so i [thought→think] [i→it] [would→is] [come→a] [and→bust] [-speak] [-to] [-you] [-about] [-it] |
| `primock57:day5_consultation03:patient:0067:phone_noisy_snr5` | patient | 18/29 | yeah i mean i [+kind] [+of] [+feel] [find→uncomfortable] [public→just] [transport→like] [really→in] [stressful→a] [anyway→way] especially being on the tube [-it] [-is] because it is [-quite] getting warmer [so→to] [it→the] [is→air] [just→like] [-really] [-airless] |
| `primock57:day1_consultation13:doctor:0119:phone_noisy_snr5` | doctor | 17/35 | okay in the meantime if your headaches are [-not] getting [-any] better or [-they] [-are] getting worse you know i [want→will] [you→not] [to→see] [give→you] [me→next] [a→fall] [call→i] [or→will] come back [and→to] see [+you] [+in] [me→the] [sooner→spring] okay |
