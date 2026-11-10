# Semantic error judging prompt (published)

Used to estimate **Semantic WER**: the share of reference words recognised wrongly
*in a way that changes meaning*. Applied by Claude (Anthropic) in the same session,
temperature-equivalent deterministic use, to a fixed random sample of utterances
(sampling seed and sample files in `results/semantic/`). The judge sees only
the reference and the hypothesis text; it never hears audio and never sees which
system produced the hypothesis.

---

You are auditing a speech-recognition transcript against a human reference.

For each **error span** (a stretch where the hypothesis differs from the
reference after normalisation), decide whether the difference would change what
a reader, or an automated agent acting on the transcript, understands or does.

Label each span with exactly one class:

| Class | Meaning-changing? | Examples |
|---|---|---|
| `number` | yes, if the value differs | 15 vs 50, सौ vs हज़ार. A different *form* of the same value (5 vs five, दस vs 10) is `format`. |
| `negation` | yes | नहीं dropped or added; "can" vs "can't" |
| `entity` | yes | Wrong person, place, product, bank or organisation name |
| `content` | yes | A different content word: wrong verb, noun, adjective, or a missing or extra content word that changes the sense |
| `grammar` | no | Agreement, gender, number or case marking where the intended meaning is still clear (है/हैं, की/के) |
| `filler` | no | Fillers, hesitations, repetitions, discourse particles (uh, अच्छा, तो at a sentence start) |
| `spelling` | no | The same word spelled differently, including script variants and transliteration of the same English word |
| `format` | no | Digits vs number words, punctuation, word joining or splitting, contractions |

Rules:
1. Judge the *span in context* of the whole sentence.
2. If you are unsure whether the meaning changed, choose the meaning-changing class.
   The estimate must err against the system, not for it.
3. A span that merges several words is one judgement; record how many reference
   words it covers.

Output, one JSON object per span:
`{"utt": <id>, "span": <n>, "class": "<class>", "meaning_changing": true|false}`

Semantic WER = (reference words in meaning-changing spans + inserted words in
meaning-changing insertion spans) / reference words, over the sample. It is
reported with a bootstrap 95% confidence interval over utterances.
