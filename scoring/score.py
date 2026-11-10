"""Score Blackbird predictions.

    python scoring/score.py                      # score every predictions/*/*.jsonl
    python scoring/score.py predictions/kathbath/hi.native.given.jsonl

WER and CER are corpus-level (total errors / total reference words or
characters), computed with jiwer after scoring/normalizer.py, the same way the
AI4Bharat Vistaar evaluation does. The 95% confidence interval comes from a
bootstrap over utterances (1,000 resamples, fixed seed).

Failed API calls are NOT dropped. They are scored as an empty hypothesis (every
reference word counts as a deletion) and reported in the "failed" column, so a
failure can never improve a score.

Writes results/scores.csv and results/scores.json.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

import jiwer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalizer import normalize, normalize_tolerant  # noqa: E402
from refs import attach_refs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = 1000
SEED = 20261028


def word_errors(ref: str, hyp: str) -> tuple[int, int, int, int]:
    """(substitutions, deletions, insertions, reference words) for one utterance."""
    if not ref:
        return 0, 0, len(hyp.split()), 0
    if not hyp:
        n = len(ref.split())
        return 0, n, 0, n
    o = jiwer.process_words(ref, hyp)
    return o.substitutions, o.deletions, o.insertions, o.substitutions + o.deletions + o.hits


def char_errors(ref: str, hyp: str) -> tuple[int, int]:
    """(character edits, reference characters), spaces included, as jiwer.cer does."""
    if not ref:
        return len(hyp), 0
    if not hyp:
        return len(ref), len(ref)
    o = jiwer.process_characters(ref, hyp)
    return o.substitutions + o.deletions + o.insertions, o.substitutions + o.deletions + o.hits


def score_file(path: Path) -> dict | None:
    dataset = path.parent.name
    lang, mode, langtag = path.name[:-len(".jsonl")].split(".")
    rows = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                # Keep a success over an earlier failure for the same clip.
                if r["id"] not in rows or r["status"] == 200:
                    rows[r["id"]] = r
    if not rows:
        return None
    attach_refs(list(rows.values()), path)

    per = []
    failed = 0
    audio_s = proc_ms = 0.0
    for r in rows.values():
        ref = normalize(r["ref"], lang)
        hyp = normalize(r["hyp"] or "", lang) if r["status"] == 200 else ""
        failed += r["status"] != 200
        s, d, i, n = word_errors(ref, hyp)
        ce, cn = char_errors(ref, hyp)
        ts, td, ti, tn = word_errors(normalize_tolerant(r["ref"], lang),
                                     normalize_tolerant(r["hyp"] or "", lang) if r["status"] == 200 else "")
        per.append((s, d, i, n, ce, cn, ts + td + ti, tn))
        audio_s += float(r.get("duration_s") or 0)
        proc_ms += float(r.get("processing_ms") or 0)

    def wer_of(sample):
        e = sum(p[0] + p[1] + p[2] for p in sample)
        n = sum(p[3] for p in sample)
        return e / n if n else 0.0

    S = sum(p[0] for p in per); D = sum(p[1] for p in per); I = sum(p[2] for p in per)
    N = sum(p[3] for p in per)
    CE = sum(p[4] for p in per); CN = sum(p[5] for p in per)

    rng = random.Random(SEED)
    boots = sorted(wer_of([per[rng.randrange(len(per))] for _ in per]) for _ in range(BOOTSTRAP))
    lo, hi = boots[int(0.025 * BOOTSTRAP)], boots[int(0.975 * BOOTSTRAP) - 1]

    return {
        "dataset": dataset, "lang": lang, "mode": mode, "language_param": langtag,
        "utterances": len(per), "failed": failed, "hours": round(audio_s / 3600, 2),
        "ref_words": N,
        "wer": round(100 * (S + D + I) / N, 2) if N else None,
        "wer_ci95_low": round(100 * lo, 2), "wer_ci95_high": round(100 * hi, 2),
        "sub_pct": round(100 * S / N, 2) if N else None,
        "del_pct": round(100 * D / N, 2) if N else None,
        "ins_pct": round(100 * I / N, 2) if N else None,
        "cer": round(100 * CE / CN, 2) if CN else None,
        "wer_spelling_tolerant": round(100 * sum(p[6] for p in per) / sum(p[7] for p in per), 2)
        if sum(p[7] for p in per) else None,
        "rtfx": round(audio_s / (proc_ms / 1000), 1) if proc_ms else None,
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
    }


def main():
    paths = [Path(p).resolve() for p in sys.argv[1:]] or sorted((ROOT / "predictions").glob("*/*.given.jsonl"))
    results = [r for p in paths if (r := score_file(p))]
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    if not sys.argv[1:]:
        with (out / "scores.json").open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=1, ensure_ascii=False)
        if results:
            with (out / "scores.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(results[0]))
                w.writeheader()
                w.writerows(results)
    for r in results:
        print(f"{r['dataset']:14} {r['lang']:4} {r['mode']:7} {r['language_param']:5} "
              f"n={r['utterances']:6} fail={r['failed']:4} {r['hours']:6.2f}h  "
              f"WER {r['wer']:6.2f} [{r['wer_ci95_low']:.2f}-{r['wer_ci95_high']:.2f}]  tolerant {r['wer_spelling_tolerant']:6.2f}  CER {r['cer']:6.2f}")


if __name__ == "__main__":
    main()
