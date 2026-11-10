"""Reference transcripts for published prediction files.

The prediction files in this repository carry clip IDs and the API output only,
not the datasets' reference text. The scorers fill each reference in from
datasets/<dataset>/<lang>/manifest.jsonl, which tools/download.py and the
tools/prepare_*.py scripts rebuild from the original public sources.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_cache: dict[Path, dict[str, str]] = {}


def attach_refs(rows: list[dict], pred_path: Path) -> list[dict]:
    """Set r["ref"] on every row that lacks it, from the rebuilt manifest."""
    if all("ref" in r for r in rows):
        return rows
    dataset, lang = Path(pred_path).parent.name, Path(pred_path).name.split(".")[0]
    manifest = ROOT / "datasets" / dataset / lang / "manifest.jsonl"
    if manifest not in _cache:
        if not manifest.exists():
            raise SystemExit(f"{manifest.relative_to(ROOT)} is missing: run the download and prepare "
                             "steps in README.md first.")
        with manifest.open(encoding="utf-8") as f:
            _cache[manifest] = {r["id"]: r["text"] for r in map(json.loads, f) if r}
    refs = _cache[manifest]
    missing = [r["id"] for r in rows if "ref" not in r and r["id"] not in refs]
    if missing:
        raise SystemExit(f"{len(missing)} clips of {pred_path} are not in {manifest.relative_to(ROOT)}, "
                         f"e.g. {missing[0]}. The dataset version differs from the one benchmarked "
                         "(see DATASETS.md for the pinned revisions).")
    for r in rows:
        r.setdefault("ref", refs.get(r["id"]))
    return rows
