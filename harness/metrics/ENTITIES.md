# Entity tagging and scoring rules

Code: `harness/metrics/entities.py`. Categories come from the use-case profile (`configs/profiles/README.md`); this module holds no domain vocabulary (a test enforces that no lexicon term appears in its source).

## Where tagging happens
On the **normalized reference** (Whisper + equivalence layer, same as WER), so entity spans line up with the WER alignment. Normalize with the same `date_order` you score with.

## Category kinds
| Kind | Matches | Notes |
|---|---|---|
| `lexicon` | Lexicon terms, normalized the same way as the text, longest match first, non-overlapping. | `co-codamol` normalizes to `co codamol` on both sides. |
| `regex` | The profile's pattern, run on the normalized text. A span covers every token the match overlaps. | Write patterns against normalized text (lowercase, digits, no punctuation). |
| `builtin: number` | Single tokens like `45`, `$45.20`, `10%`. | Yields to every other category: number spans overlapping a date, phone, ID etc. are dropped, so "amount" means "numbers that aren't something more specific". |
| `builtin: phone` | One token of 7–15 digits. | The equivalence layer joins digit runs, so `(555) 123-4567`, `555 123 4567` and spoken digits all become `5551234567`. Known false positives: any long number, e.g. "one million" → `1000000`. |
| `builtin: date` | `march 4 1980`, `4 of march 1980`, `4 march`, `march 4`, `march 1980`. | Spans start at the number or month; a leading "the" is not part of the entity. Numeric dates are converted to month form by the equivalence layer first. Every date matches; the category *name* (e.g. `date_of_birth`) is a label, not a filter. |
| `builtin: dosage` | Number + unit: mg, mcg, ml, g, iu, unit(s), puff(s), tablet(s), capsule(s), drop(s), sachet(s), spray(s). | "one" counts as a number (Whisper keeps a standalone 1 as "one"). "half a tablet" is not matched. `2.1 mg` becomes `2 1 mg` inside Whisper, so only `1 mg` is tagged; this is identical on both sides. |
| `builtin: duration` | Number + seconds…years. | "a couple of days" is not matched. |

## Per-entity measures
- **Recovered:** every reference token in the span aligned as correct. One wrong token in "march 4 1980" misses the whole entity.
- **Character errors:** Levenshtein distance between the span's characters (spaces removed) and the hypothesis tokens aligned to it: substituted/correct tokens one to one, insertions only when strictly inside the span, deletions contribute nothing. A phone number with one wrong digit is 1 error out of 11 characters, not a lost entity. Reported per category as pooled CER.
- **Formatted** (builtins only, needs the raw hypothesis): recovered **and** every number in the span appears as digits in the raw hypothesis (leading zeros and thousands separators ignored; "one" counts as 1). For phones, separators between digits are removed and the whole digit string must appear. "ten milligrams" is recovered but not formatted; "10mg" is both.
- **Category summary:** recall with a Wilson 95% interval, pooled CER, formatted accuracy with a Wilson interval.

## Keyterm false insertions
For each boosted term (normalized), count hypothesis occurrences whose tokens are not all aligned as correct to the reference: the provider wrote the term where the speaker didn't say it. Boosting can cause this; the count is reported next to the recall gain from boosting.

## Sample size
Recall intervals need roughly 200+ instances per category to be useful. On PriMock57 (5,961 scorable utterances, dmy dates) the healthcare profile finds: medication 166, date 21, dosage 18, phone 2 (both false positives). Dosage, date-of-birth and phone scoring therefore depend on the synthetic intake scripts.
