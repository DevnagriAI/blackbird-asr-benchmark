"""Unpack Hugging Face parquet datasets (audio embedded) into
datasets/<dataset>/<lang>/audio/ + manifest.jsonl.

Audio bytes are written out exactly as published (no resampling or
re-encoding). The reference is the dataset's own `text` field. Speaker and
recording labels are kept so results can be sliced (scenario, noise, area,
gender, ...).

    python tools/prepare_hf.py svarah
    python tools/prepare_hf.py lahaja
    python tools/prepare_hf.py indicvoices
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]

INDICVOICES_LANGS = {
    "assamese": "as", "bengali": "bn", "bodo": "brx", "dogri": "doi", "gujarati": "gu",
    "hindi": "hi", "kannada": "kn", "kashmiri": "ks", "konkani": "kok", "maithili": "mai",
    "malayalam": "ml", "manipuri": "mni", "marathi": "mr", "nepali": "ne", "odia": "or",
    "punjabi": "pa", "sanskrit": "sa", "santali": "sat", "sindhi": "sd", "tamil": "ta",
    "telugu": "te", "urdu": "ur",
}

NOISE_FLAGS = ("noise_persistent", "noise_intermittent", "chatter_persistent",
               "chatter_intermittent", "echo_present", "low_volume", "unclear_audio")


def noise_labels(report: str | None) -> dict:
    if not report:
        return {}
    try:
        rep = ast.literal_eval(report)
    except Exception:
        return {}
    flags = {k: bool(rep.get(k)) for k in NOISE_FLAGS}
    flags["noisy"] = any(flags[k] for k in ("noise_persistent", "noise_intermittent",
                                            "chatter_persistent", "chatter_intermittent"))
    return flags


def write_split(files: list[Path], dataset: str, lang: str, meta_keys: list[str], source: str, license_: str):
    out_dir = ROOT / "datasets" / dataset / lang
    (out_dir / "audio").mkdir(parents=True, exist_ok=True)
    n = 0
    seen = set()
    with (out_dir / "manifest.jsonl").open("w", encoding="utf-8") as mf:
        for fp in files:
            pf = pq.ParquetFile(fp)
            for batch in pf.iter_batches(batch_size=256):
                for row in batch.to_pylist():
                    audio = row["audio_filepath"]
                    data = audio["bytes"]
                    name = Path(audio["path"] or "").name
                    if not name or name in seen:
                        name = hashlib.sha1(data).hexdigest()[:16]
                    if "." not in name:
                        name += ".flac" if data[:4] == b"fLaC" else ".wav"
                    seen.add(name)
                    (out_dir / "audio" / name).write_bytes(data)
                    rec = {
                        "id": f"{dataset}/{lang}/{Path(name).stem}",
                        "audio": f"audio/{name}",
                        "text": row["text"],
                        "duration": row.get("duration"),
                        "lang": lang,
                        "source": source,
                        "license": license_,
                        "split": fp.name.split("-")[0],
                    }
                    for k in meta_keys:
                        if k in row:
                            rec[k] = row[k]
                    if "verification_report" in row:
                        rec.update(noise_labels(row["verification_report"]))
                    mf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n += 1
    print(f"{dataset}/{lang}: {n} clips -> {out_dir.relative_to(ROOT)}", flush=True)


def main(which: str):
    dl = ROOT / "downloads"
    if which == "svarah":
        write_split(sorted((dl / "Svarah").rglob("test-*.parquet")), "svarah", "en",
                    ["gender", "age-group", "primary_language", "native_place_state",
                     "native_place_district"],
                    "huggingface.co/datasets/ai4bharat/Svarah (test)", "CC-BY-4.0")
    elif which == "lahaja":
        write_split(sorted((dl / "Lahaja").rglob("test-*.parquet")), "lahaja", "hi",
                    ["scenario", "native_language", "gender", "age_group", "native_state",
                     "native_district", "sp_id"],
                    "huggingface.co/datasets/ai4bharat/Lahaja (test)", "MIT")
    elif which == "indicvoices":
        for folder, code in INDICVOICES_LANGS.items():
            files = sorted((dl / "IndicVoices" / folder).glob("valid*.parquet"))
            if files:
                write_split(files, "indicvoices", code,
                            ["scenario", "task_name", "gender", "age_group", "job_type",
                             "area", "district", "state", "speaker_id"],
                            "huggingface.co/datasets/ai4bharat/IndicVoices (valid)", "CC-BY-4.0")
    else:
        raise SystemExit(f"unknown dataset {which}")


if __name__ == "__main__":
    main(sys.argv[1])
