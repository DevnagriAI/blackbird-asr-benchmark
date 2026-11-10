# Method

How the Blackbird ASR v1 benchmark (October 2026) was run and scored. Every
number in `results/` follows from the choices below and the code in this
repository.

## System under test

Blackbird ASR, Devnagri's hosted speech recognition API, called through its
public file-transcription endpoint (`POST /v1/transcribe`). The deployed model
was frozen for the whole run and nothing was tuned on these test sets. Every
clip was sent as a separate request, exactly as a customer would send it.

## Data

- **Public test sets only.** No private, proprietary or self-recorded audio.
  The ten datasets, their sources, versions and licences are in
  [DATASETS.md](DATASETS.md).
- **Official test splits where they exist.** IndicVoices has no public test
  split, so its `valid` split is used.
- **No added noise.** Noisy conditions come only from recordings that are
  naturally noisy. Kathbath's "noisy" variant (Kathbath-Hard) is excluded
  because its noise is synthetic.
- **Audio is used exactly as published**: no resampling, trimming or
  re-encoding before upload.
- **Two IndicVoices languages are not scored** because the reference script
  differs from the script the model writes: Manipuri (references in Meetei
  Mayek) and Sindhi (references in Devanagari).

## Requests

- **The language is passed explicitly** (`language=<code>`), as a customer with
  a known language would configure it.
- **Output mode follows each dataset's reference convention:**
  - `native` for monolingual sets, where references are in the language's own
    script;
  - `mixed` for code-switched sets (MUCS 2021 code-switching, HiACC), whose
    references write English in Latin script, and for Svarah (Indian English),
    whose references write numbers as digits.
- **A failed request counts as an empty transcript**: every reference word is
  a deletion. No clip is dropped. There were no failed requests in the
  published run.

## Scoring

- **Normalisation** follows the AI4Bharat Vistaar evaluation protocol
  unchanged, plus lowercasing of Latin script (`scoring/normalizer.py`). Numbers,
  negations and names are never rewritten.
- **WER (headline)** is corpus-level: total word errors divided by total
  reference words, computed with jiwer (`scoring/score.py`).
- **95% confidence intervals** come from 1,000 bootstrap resamples over
  utterances, seed 20261028.
- **CER** is computed the same way on characters, spaces included.
- **Spelling-tolerant WER** is reported next to strict WER, never instead of
  it. It additionally treats four kinds of spelling variant as equal: nukta,
  chandrabindu vs anusvara, a nasal consonant vs anusvara, and three Hindi word
  pairs (वह/वो, यह/ये, छः/छह). Grammar differences stay errors.
- **Vaani** is scored with its creators' official toolkit
  (`tools/third_party/vaani-toolkit`, via `scoring/vaani_score.py`): three human
  references per clip, the toolkit's own transliteration and cleaning. That is
  the reported Vaani figure. The generic single-reference row for Vaani in
  `scores.csv` counts the dataset's event tags and annotations as words, so it
  is not comparable and not reported.
- **Numbers and negations** (`scoring/critical.py`): the share of reference
  number tokens not recognised exactly, and the rate at which negation words
  (नहीं, not, ...) are dropped or added. In `mixed` mode, number tokens also
  catch digit-versus-word convention differences, so the HiACC number rates
  mostly measure convention, not recognition.
- **IndicVoices slices** (`scoring/slices.py`): WER by recording scenario (read,
  extempore, conversation) and by the human annotators' own noise labels.

## Semantic WER

An estimate of how many errors change what was meant, on IndicVoices Hindi and
Svarah English.

1. **Sample.** 100 clips per set, drawn uniformly at random with seed
   20261028 (`scoring/semantic_sample.py`). Error-free clips stay in the
   sample.
2. **Judging.** Every error span in the sample was labelled by Claude
   (Anthropic) with the published prompt in `scoring/judge_prompt.md`. The
   judge sees only the reference and the transcript, never the audio or the
   system's name. The eight classes are number, negation, entity and content
   (meaning-changing), and grammar, filler, spelling and format (not
   meaning-changing). When unsure, the judge must choose the meaning-changing
   class.
3. **Score.** Semantic WER counts only meaning-changing errors
   (`scoring/semantic_score.py`), with a bootstrap 95% interval. The
   per-span labels are in `results/semantic/*.judgements.txt`.

## Known output behaviour, counted as errors

These are scored as errors, because a customer would see them:

- Very short one-word replies (for example a lone "हाँ" under about a second)
  can come back empty.
- In `mixed` mode the word "एक" is sometimes written as the digit "1" even when
  it means "a".
- English contractions are sometimes split ("don t").

## Not measured here

- **Latency.** All clips went through the batch file API; streaming latency is
  a separate measurement.
- **Automatic language detection.** Every request passed its language.
- **Training-data overlap.** The provider of the underlying model has not
  disclosed its training data, so the absence of overlap between these public
  test sets and the model's training data could not be independently verified.

## Reproducibility

- The datasets are pinned: Hugging Face sets to the commit benchmarked, other
  archives by SHA-256 (`tools/download.py`, [DATASETS.md](DATASETS.md)).
- Rescoring the published predictions reproduces `results/` exactly.
- Re-running the API gives the model as deployed on that day. Even on the same
  build, batched decoding is not bit-identical between runs: a few long clips
  can differ by a word.
