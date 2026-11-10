"""Move an unzipped AI4Bharat Vistaar benchmark into
datasets/vistaar-<name>/<lang>/audio/ + manifest.jsonl.

Source zips: https://indicwhisper.objectstore.e2enetworks.net/vistaar_benchmarks/<name>.zip
(SHA-256 in downloads/vistaar_sha256.txt). Audio files are moved unchanged.
The reference is the manifest's own `text` field, as in Vistaar's evaluation.

    python tools/prepare_vistaar.py kathbath fleurs commonvoice
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "downloads" / "vistaar"
LANGS = {
    "bengali": "bn", "gujarati": "gu", "hindi": "hi", "kannada": "kn", "malayalam": "ml",
    "marathi": "mr", "odia": "or", "punjabi": "pa", "sanskrit": "sa", "tamil": "ta",
    "telugu": "te", "urdu": "ur",
}


def main(name: str):
    base = SRC / name
    for lang_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        code = LANGS[lang_dir.name.lower()]
        manifests = list(lang_dir.rglob("manifest.json"))
        if not manifests:
            print(f"  {name}/{lang_dir.name}: no manifest, skipped")
            continue
        out = ROOT / "datasets" / f"vistaar-{name}" / code
        (out / "audio").mkdir(parents=True, exist_ok=True)
        n = 0
        with (out / "manifest.jsonl").open("w", encoding="utf-8") as mf:
            for man in manifests:
                for line in man.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    src = SRC / r["audio_filepath"]
                    if not src.exists():
                        src = man.parent / Path(r["audio_filepath"]).name
                        if not src.exists():
                            src = next(man.parent.rglob(Path(r["audio_filepath"]).name), None)
                    dst = out / "audio" / Path(r["audio_filepath"]).name
                    if src and src.exists() and not dst.exists():
                        shutil.move(str(src), dst)
                    if not dst.exists():
                        print("  missing audio:", r["audio_filepath"])
                        continue
                    mf.write(json.dumps({
                        "id": f"vistaar-{name}/{code}/{dst.stem}",
                        "audio": f"audio/{dst.name}",
                        "text": r["text"],
                        "duration": r.get("duration"),
                        "lang": code,
                        "source": f"AI4Bharat Vistaar benchmark: {name}.zip",
                        "license": "see LICENSES.md",
                        "split": "test",
                    }, ensure_ascii=False) + "\n")
                    n += 1
        print(f"vistaar-{name}/{code}: {n} clips", flush=True)


if __name__ == "__main__":
    for nm in sys.argv[1:]:
        main(nm)
