"""Draw the fixed random sample for Semantic WER judging.

For each prediction file given, sample N utterances uniformly at random
(seed 20261028, errors or not; error-free utterances still count in the
denominator) and list every error span after strict normalisation.

    python scoring/semantic_sample.py 100 predictions/indicvoices/hi.native.given.jsonl ...

Writes results/semantic/<dataset>.<lang>.sample.jsonl
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import jiwer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalizer import normalize  # noqa: E402
from refs import attach_refs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261028


def spans(ref: str, hyp: str):
    o = jiwer.process_words(ref, hyp)
    R, H = o.references[0], o.hypotheses[0]
    out = []
    for a in o.alignments[0]:
        if a.type == "equal":
            continue
        out.append({
            "type": a.type,
            "ref": " ".join(R[a.ref_start_idx:a.ref_end_idx]),
            "hyp": " ".join(H[a.hyp_start_idx:a.hyp_end_idx]),
            "ref_words": a.ref_end_idx - a.ref_start_idx,
            "hyp_words": a.hyp_end_idx - a.hyp_start_idx,
        })
    # merge adjacent spans so one misrecognised phrase is one judgement
    merged = []
    for s in out:
        merged.append(s)
    return merged, len(R)


def main(n: int, paths: list[str]):
    outdir = ROOT / "results" / "semantic"
    outdir.mkdir(parents=True, exist_ok=True)
    for p in paths:
        p = Path(p)
        dataset, lang = p.parent.name, p.name.split(".")[0]
        rows = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
        rows = attach_refs([r for r in rows if r["status"] == 200], p)
        rows.sort(key=lambda r: r["id"])
        sample = random.Random(SEED).sample(rows, min(n, len(rows)))
        with (outdir / f"{dataset}.{lang}.sample.jsonl").open("w", encoding="utf-8") as f:
            for i, r in enumerate(sample):
                ref, hyp = normalize(r["ref"], lang), normalize(r["hyp"] or "", lang)
                if not ref:
                    continue
                sp, nref = spans(ref, hyp)
                f.write(json.dumps({"utt": i, "id": r["id"], "ref_words": nref, "ref": ref,
                                    "hyp": hyp, "spans": sp}, ensure_ascii=False) + "\n")
        print(f"{dataset}/{lang}: {len(sample)} sampled")


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2:])
