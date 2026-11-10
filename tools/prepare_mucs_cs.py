"""Cut the MUCS 2021 code-switching test sets (OpenSLR SLR104, Kaldi layout)
into utterance clips at the published segment boundaries.

datasets/mucs2021-cs/<lang>/audio/<utt>.wav + manifest.jsonl
Samples are copied exactly (16 kHz PCM, no resampling). The reference is the
Kaldi `text` line: Hindi/Bengali in native script, English in Latin.

    python tools/prepare_mucs_cs.py hi downloads/mucs_cs_hi
    python tools/prepare_mucs_cs.py bn downloads/mucs_cs_bn
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]


def main(lang: str, src: Path):
    tdir = next(src.rglob("segments")).parent
    text = dict(l.split(" ", 1) for l in (tdir / "text").read_text(encoding="utf-8").splitlines() if " " in l)
    wavs = {}
    for l in (tdir / "wav.scp").read_text(encoding="utf-8").splitlines():
        rec, path = l.split(None, 1)
        p = next(src.rglob(Path(path.strip()).name), None)
        wavs[rec] = p
    out = ROOT / "datasets" / "mucs2021-cs" / lang
    (out / "audio").mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    n = 0
    with (out / "manifest.jsonl").open("w", encoding="utf-8") as mf:
        for l in (tdir / "segments").read_text(encoding="utf-8").splitlines():
            utt, rec, start, end = l.split()
            if utt not in text or wavs.get(rec) is None:
                continue
            if rec not in cache:
                cache.clear()
                cache[rec] = sf.read(wavs[rec], dtype="int16")
            data, sr = cache[rec]
            seg = data[int(float(start) * sr):int(float(end) * sr)]
            sf.write(out / "audio" / f"{utt}.wav", seg, sr, subtype="PCM_16")
            mf.write(json.dumps({
                "id": f"mucs2021-cs/{lang}/{utt}", "audio": f"audio/{utt}.wav",
                "text": text[utt].strip(), "duration": round(len(seg) / sr, 3), "lang": lang,
                "source": "OpenSLR SLR104 (MUCS 2021 code-switching, test)",
                "license": "CC-BY-SA-4.0", "split": "test",
            }, ensure_ascii=False) + "\n")
            n += 1
    print(f"mucs2021-cs/{lang}: {n} clips")


if __name__ == "__main__":
    main(sys.argv[1], ROOT / sys.argv[2])
