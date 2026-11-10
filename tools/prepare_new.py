"""Unpack the 2026 additions into datasets/<name>/<lang>/audio + manifest.jsonl.

    python tools/prepare_new.py vaani | hiacc

vaani      ARTPARK-IISc/Vaani-Benchmark-V1.0. All three human references are
           kept (refs); `text` is transcription_v1 for the generic scorer. The
           official score uses scoring/vaani_score.py (the toolkit's
           multi-reference method).

hiacc      Trelis/hiacc-adult-test-eval, Trelis/hiacc-child-test-eval.
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
DL = ROOT / "downloads"



def rows(pattern: str):
    for fp in sorted(DL.glob(pattern)):
        for batch in pq.ParquetFile(fp).iter_batches(batch_size=64):
            yield from batch.to_pylist()


def write(dataset: str, lang: str, items):
    out = ROOT / "datasets" / dataset / lang
    (out / "audio").mkdir(parents=True, exist_ok=True)
    n = 0
    with (out / "manifest.jsonl").open("w", encoding="utf-8") as mf:
        for rec, data, name in items:
            (out / "audio" / name).write_bytes(data)
            rec = {"id": f"{dataset}/{lang}/{Path(name).stem}", "audio": f"audio/{name}", "lang": lang, **rec}
            mf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"{dataset}/{lang}: {n} clips", flush=True)


def vaani():
    def gen():
        for r in rows("Vaani-Benchmark-V1.0/data/*.parquet"):
            name = Path(r["audio"]["path"]).name
            name = name if name.endswith(".wav") else name + ".wav"
            yield ({"text": r["transcription_v1"],
                    "refs": [r["transcription_v1"], r["transcription_v2"], r["transcription_v3"]],
                    "duration": r["duration"], "state": r["state"], "district": r["district"],
                    "gender": r["gender"], "speaker": r["speakerID"],
                    "source": "huggingface.co/datasets/ARTPARK-IISc/Vaani-Benchmark-V1.0 (test)",
                    "license": "CC-BY-4.0", "split": "test"}, r["audio"]["bytes"], name)
    write("vaani-benchmark", "hi", gen())


GLOSS = re.compile(r"\([^)]*\)|<[^>]*>|\[[^\]]*\]")


def hiacc():
    for group in ("adult", "child"):
        def gen():
            for r in rows(f"hiacc-{group}-test-eval/**/*.parquet"):
                yield ({"text": r["transcription"], "duration": r.get("duration_sec"),
                        "speaker": r["pid"], "gender": r["speaker_gender"], "age": r["speaker_age"],
                        "cmi": r.get("cmi"),
                        "source": f"huggingface.co/datasets/Trelis/hiacc-{group}-test-eval (HiACC test)",
                        "license": "CC-BY-4.0", "split": "test"}, r["audio"]["bytes"], r["file_name"])
        write(f"hiacc-{group}", "hi", gen())


if __name__ == "__main__":
    {"vaani": vaani, "hiacc": hiacc}[sys.argv[1]]()
