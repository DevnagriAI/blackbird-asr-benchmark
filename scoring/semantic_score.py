"""Compute Semantic WER from a judged sample.

    python scoring/semantic_score.py results/semantic/indicvoices.hi

Reads <prefix>.sample.jsonl and <prefix>.judgements.txt. Every error span in the
sample must be judged; the script refuses to score an incomplete judgement file.
Errors per span follow jiwer's counting: a substitution or deletion span counts
its reference words, an insertion span its hypothesis words.
"""
from __future__ import annotations

import collections
import json
import random
import sys
from pathlib import Path

MEANING = {"C": "content", "N": "number", "E": "entity", "X": "negation"}
OTHER = {"S": "spelling", "M": "format", "F": "filler", "G": "grammar"}
SEED = 20261028


def main(prefix: str):
    sample = [json.loads(l) for l in Path(prefix + ".sample.jsonl").open(encoding="utf-8")]
    labels = {}
    for line in Path(prefix + ".judgements.txt").open(encoding="utf-8"):
        line = line.split("#")[0].strip()
        for tok in line.split():
            key, cls = tok.split("=")
            u, s = key.split(":")
            labels[(int(u), int(s))] = cls
    per, by_class, missing = [], collections.Counter(), []
    for r in sample:
        sem = err = 0
        for k, sp in enumerate(r["spans"]):
            n = sp["hyp_words"] if sp["type"] == "insert" else sp["ref_words"]
            err += n
            cls = labels.get((r["utt"], k))
            if cls is None:
                missing.append(f"{r['utt']}:{k}")
                continue
            by_class[cls] += n
            if cls in MEANING:
                sem += n
        per.append((sem, err, r["ref_words"]))
    if missing:
        raise SystemExit(f"unjudged spans: {missing[:20]} ... ({len(missing)})")
    N = sum(p[2] for p in per)
    sem = sum(p[0] for p in per)
    err = sum(p[1] for p in per)
    rng = random.Random(SEED)
    boots = sorted(sum(x[0] for x in s) / max(1, sum(x[2] for x in s))
                   for s in ([per[rng.randrange(len(per))] for _ in per] for _ in range(1000)))
    out = {
        "sample": prefix, "utterances": len(per), "ref_words": N,
        "wer_in_sample": round(100 * err / N, 2),
        "semantic_wer": round(100 * sem / N, 2),
        "semantic_ci95": [round(100 * boots[25], 2), round(100 * boots[974], 2)],
        "share_of_errors_meaning_changing": round(100 * sem / err, 1) if err else 0.0,
        "errors_by_class_words": {({**MEANING, **OTHER})[k]: v for k, v in by_class.most_common()},
    }
    Path(prefix + ".semantic.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
