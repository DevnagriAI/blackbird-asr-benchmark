# Datasets

Ten public datasets, 58 test sets. None of their audio or reference text is
redistributed here: `tools/download.py` fetches each one from its original
source at the version benchmarked, and the `tools/prepare_*.py` scripts rebuild
it. Each dataset stays under its own licence; please cite its authors.

| Folder | Dataset | Publisher | Split | Languages | Clips | Hours | Licence |
|---|---|---|---|---|---:|---:|---|
| `indicvoices` | IndicVoices | AI4Bharat, IIT Madras | valid | 20 Indian languages | 71,985 | 120.2 | CC-BY-4.0 (gated) |
| `vistaar-kathbath` | Kathbath (Vistaar test set) | AI4Bharat | test | 12 | 19,672 | 37.0 | CC-BY-4.0 |
| `vistaar-commonvoice` | Common Voice (Vistaar test set) | Mozilla, packaged by AI4Bharat | test | 8 | 17,153 | 27.9 | CC0-1.0 |
| `vistaar-fleurs` | FLEURS (Vistaar test set) | Google, packaged by AI4Bharat | test | 11 | 7,968 | 27.8 | CC-BY-4.0 |
| `mucs2021-cs` | MUCS 2021 code-switching | Microsoft, IIT Madras (OpenSLR SLR104) | test | Hindi-English, Bengali-English | 7,411 | 12.2 | CC-BY-SA-4.0 |
| `svarah` | Svarah | AI4Bharat | test | Indian English | 6,656 | 9.6 | CC-BY-4.0 (gated) |
| `lahaja` | Lahaja | AI4Bharat | test | Hindi | 6,152 | 12.3 | MIT (gated) |
| `vaani-benchmark` | Vaani Benchmark V1.0 | ARTPARK, IISc | test | Hindi | 5,050 | 10.9 | CC-BY-4.0 (gated) |
| `hiacc-adult` | HiACC adult | Trelis | test | Hinglish | 664 | 0.7 | CC-BY-4.0 |
| `hiacc-child` | HiACC child | Trelis | test | Hinglish | 372 | 0.4 | CC-BY-4.0 |
| | **Total** | | | | **143,083** | **259.0** | |

"Gated" means the dataset's Hugging Face page asks you to accept its terms
before downloading.

## Sources and pinned versions

| Folder | Source | Version benchmarked |
|---|---|---|
| `indicvoices` | [huggingface.co/datasets/ai4bharat/IndicVoices](https://huggingface.co/datasets/ai4bharat/IndicVoices), `*/valid-*.parquet` | commit `c96f9088f138cf89d419da7e8e643e1f05c00a87` |
| `lahaja` | [huggingface.co/datasets/ai4bharat/Lahaja](https://huggingface.co/datasets/ai4bharat/Lahaja) | commit `d4ffd2ecbdd933e37c917ddcf620eef159ceb3a7` |
| `svarah` | [huggingface.co/datasets/ai4bharat/Svarah](https://huggingface.co/datasets/ai4bharat/Svarah) | commit `ebbf7777fe771490696a3f7b007097606fa8c924` |
| `vaani-benchmark` | [huggingface.co/datasets/ARTPARK-IISc/Vaani-Benchmark-V1.0](https://huggingface.co/datasets/ARTPARK-IISc/Vaani-Benchmark-V1.0) | commit `d742f1cca7111ac5e9890bffbc91e6df79517627` |
| `hiacc-adult` | [huggingface.co/datasets/Trelis/hiacc-adult-test-eval](https://huggingface.co/datasets/Trelis/hiacc-adult-test-eval) | commit `45782b4752f1e353173cd0b940332a984fc0a249` |
| `hiacc-child` | [huggingface.co/datasets/Trelis/hiacc-child-test-eval](https://huggingface.co/datasets/Trelis/hiacc-child-test-eval) | commit `19f4fda91183b889f642e1e16c88c7bbeda64dad` |
| `vistaar-kathbath` | `https://indicwhisper.objectstore.e2enetworks.net/vistaar_benchmarks/kathbath.zip` | SHA-256 `cb7d4fcdef4d3dc6303bb52cf665cbf567ba4dc0664590041c14a3e9c01d23de` |
| `vistaar-fleurs` | `https://indicwhisper.objectstore.e2enetworks.net/vistaar_benchmarks/fleurs.zip` | SHA-256 `0e1abc2d687ca78f4dda424bb6595997f23d5417855bd0c9b54739666fc252ed` |
| `vistaar-commonvoice` | `https://indicwhisper.objectstore.e2enetworks.net/vistaar_benchmarks/commonvoice.zip` | SHA-256 `3fcd15bcef9e1f46d1402f889ede8b79700c4dd7cb97b95f885811f298359c5f` |
| `mucs2021-cs` (hi) | `https://www.openslr.org/resources/104/Hindi-English_test.tar.gz` | SHA-256 `93e358b3bf8233a897fcd353c1f4f98fdda6b8c01b7eed17a70c7dd26e984b37` |
| `mucs2021-cs` (bn) | `https://www.openslr.org/resources/104/Bengali-English_test.tar.gz` | SHA-256 `2e3604eab0839be8c4e2d92cdd2638a91922fbd7b16ddd08465c0e8e8b64bfe1` |

## How each set is rebuilt

- **Hugging Face parquet sets** (`tools/prepare_hf.py`, `tools/prepare_new.py`):
  audio bytes are written out exactly as published; the reference is the
  dataset's own transcript field. Vaani keeps all three human references, which
  its official scorer uses.
- **Vistaar sets** (`tools/prepare_vistaar.py`): audio files are used
  unchanged; the reference is the Vistaar manifest's `text`, as in Vistaar's own
  evaluation.
- **MUCS 2021 code-switching** (`tools/prepare_mucs_cs.py`): utterances are cut
  from the Kaldi recordings at the published segment boundaries, without
  resampling; the reference is the Kaldi `text` line (Hindi or Bengali in native
  script, English in Latin).

Clip IDs in `predictions/` are the IDs these scripts produce, so a rebuilt
dataset lines up with the published transcripts clip by clip.
