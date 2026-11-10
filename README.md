# Blackbird ASR v1 benchmark (October 2026)

Scripts, per-clip outputs and results for the public edition of the
**Blackbird ASR v1 benchmark**: Devnagri's hosted speech recognition API,
tested on public Indian-language and Indian English test sets.

| | |
|---|---|
| Test sets | 58, from 10 public datasets |
| Clips | 143,083 |
| Audio | 259.0 hours |
| Languages | 21 Indian languages and Indian English |

This repository contains **no audio and no reference transcripts**. Every
dataset is public, so the scripts here download each one from its original
source, at the exact version benchmarked, and rebuild it locally. What is
published:

- **The API's transcript for every clip** (`predictions/`), keyed by clip ID, so
  anyone can rescore it without access to the API. The clip IDs also fix exactly
  which clips make up each test set.
- **The scoring code** (`scoring/`) and the **results** (`results/`) it produces.

The method is described in [METHOD.md](METHOD.md); each dataset, its source,
version and licence in [DATASETS.md](DATASETS.md).

## Layout

```
predictions/<dataset>/<lang>.<mode>.given.jsonl
                                       one line per clip: id, status, hyp (the transcript),
                                       duration_s, processing_ms
results/scores.csv, scores.json        WER, CER, 95% CI, spelling-tolerant WER per set
results/critical.csv                   error rates on numbers and on negations
results/slices_indicvoices.csv         IndicVoices WER by scenario and by real noise
results/vaani_official.json            Vaani score from its creators' official toolkit
results/semantic/                      semantic WER: per-error judgements and scores
scoring/                               normalisation and scoring code
tools/download.py                      downloads every dataset at the benchmarked version
tools/prepare_*.py                     rebuild datasets/<dataset>/<lang>/ (audio + manifest)
tools/run_blackbird.py                 re-runs the API over a test set (needs your own key)
tools/third_party/vaani-toolkit/       the Vaani benchmark's official scoring toolkit (MIT)
```

## Reproduce the numbers

Python 3.11 or newer.

```
python -m venv .venv
.venv/bin/pip install -r tools/requirements.lock.txt      # Windows: .venv\Scripts\pip
```

**1. Download** (about 20 GB, and about twice that once unpacked). Four sets
are gated on Hugging Face: accept the terms of
[IndicVoices](https://huggingface.co/datasets/ai4bharat/IndicVoices),
[Lahaja](https://huggingface.co/datasets/ai4bharat/Lahaja),
[Svarah](https://huggingface.co/datasets/ai4bharat/Svarah) and
[Vaani](https://huggingface.co/datasets/ARTPARK-IISc/Vaani-Benchmark-V1.0)
with your account, then set `HF_TOKEN` to a token of that account.

```
export HF_TOKEN=hf_...
python tools/download.py all            # or: python tools/download.py svarah lahaja
```

**2. Prepare.** Each script writes `datasets/<dataset>/<lang>/` with the audio
as published and a `manifest.jsonl` holding the reference text.

```
python tools/prepare_hf.py indicvoices
python tools/prepare_hf.py lahaja
python tools/prepare_hf.py svarah
python tools/prepare_new.py vaani
python tools/prepare_new.py hiacc
python tools/prepare_vistaar.py kathbath fleurs commonvoice
python tools/prepare_mucs_cs.py hi downloads/mucs_cs
python tools/prepare_mucs_cs.py bn downloads/mucs_cs_bn
```

**3. Score.** No API access is needed: the scorers read the published
predictions and take each reference from the rebuilt manifests.

```
python scoring/score.py                 # -> results/scores.csv, scores.json
python scoring/critical.py              # -> results/critical.csv
python scoring/slices.py                # -> results/slices_indicvoices.csv
python scoring/vaani_score.py           # -> results/vaani_official.json
python scoring/semantic_sample.py 100 predictions/indicvoices/hi.native.given.jsonl predictions/svarah/en.mixed.given.jsonl
python scoring/semantic_score.py results/semantic/indicvoices.hi
python scoring/semantic_score.py results/semantic/svarah.en
```

The regenerated files should match the committed ones exactly; `git diff`
shows any difference (line endings aside). If a scorer reports clips missing
from a manifest, the dataset differs from the benchmarked version.

**4. Re-run the API (optional).** With your own Blackbird ASR key:

```
export BLACKBIRD_API_KEY=bb_live_...
python tools/run_blackbird.py datasets/svarah/en/manifest.jsonl --mode mixed
```

A re-run reflects the model as deployed on the day you run it, not the
October 2026 build these predictions come from.

## Reading the numbers

- **Strict WER** is the headline. It follows the AI4Bharat Vistaar evaluation
  protocol, so it can be set against Vistaar's published tables.
- **Spelling-tolerant WER** is reported next to it, never instead of it.
- **Vaani** is reported with its creators' official three-reference scoring
  (`results/vaani_official.json`). The generic single-reference figure in
  `scores.csv` counts the dataset's event tags as words and is not the
  reported number.
- **Training data.** The provider of the underlying model has not disclosed its
  training data, so the absence of overlap between these public test sets and
  the model's training data could not be independently verified.

See [METHOD.md](METHOD.md) for every choice behind the numbers.

## Licence

The code and the published predictions are released under the Apache License
2.0 ([LICENSE](LICENSE)). The Vaani toolkit in `tools/third_party/` keeps its
own MIT licence. The datasets are not redistributed here; each is governed by
its own licence, listed in [DATASETS.md](DATASETS.md). Please cite the dataset
authors when you use their data.
