"""Break IndicVoices WER down by real recording condition, using the human
annotators' own labels shipped with the dataset (no synthetic noise anywhere):

  scenario : Read / Extempore / Conversation
  noise    : clean / noisy  (noisy = annotators flagged persistent or
             intermittent background noise or chatter)

    python scoring/slices.py      -> results/slices_indicvoices.csv

Corpus-level strict WER per cell, same normaliser as scoring/score.py.
"""
from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalizer import normalize  # noqa: E402
from score import word_errors  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows_out = []
    for pred in sorted((ROOT / "predictions" / "indicvoices").glob("*.native.given.jsonl")):
        lang = pred.name.split(".")[0]
        man = {}
        with (ROOT / "datasets" / "indicvoices" / lang / "manifest.jsonl").open(encoding="utf-8") as f:
            for l in f:
                r = json.loads(l)
                man[r["id"]] = r
        cells = collections.defaultdict(lambda: [0, 0, 0, 0.0])   # errors, ref words, clips, seconds
        with pred.open(encoding="utf-8") as f:
            for l in f:
                p = json.loads(l)
                m = man.get(p["id"])
                if not m:
                    continue
                ref = normalize(p["ref"] if "ref" in p else m["text"], lang)
                hyp = normalize(p["hyp"] or "", lang) if p["status"] == 200 else ""
                s, d, i, n = word_errors(ref, hyp)
                noise = "noisy" if m.get("noisy") else "clean"
                for key in ((m.get("scenario"), noise), (m.get("scenario"), "all"), ("all", noise), ("all", "all")):
                    c = cells[key]
                    c[0] += s + d + i; c[1] += n; c[2] += 1; c[3] += float(m.get("duration") or 0)
        for (scen, noise), (e, n, k, sec) in sorted(cells.items()):
            rows_out.append({"lang": lang, "scenario": scen, "noise": noise, "clips": k,
                             "hours": round(sec / 3600, 2), "ref_words": n,
                             "wer": round(100 * e / n, 2) if n else None})
    out = ROOT / "results" / "slices_indicvoices.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0]))
        w.writeheader()
        w.writerows(rows_out)
    # compact console view: WER for clean vs noisy and per scenario
    by = collections.defaultdict(dict)
    for r in rows_out:
        by[r["lang"]][(r["scenario"], r["noise"])] = r["wer"]
    print(f"{'lang':5} {'all':>6} {'clean':>6} {'noisy':>6} {'Read':>6} {'Extemp':>6} {'Conv':>6}")
    for lang, d in by.items():
        g = lambda k: f"{d.get(k, float('nan')):6.2f}" if d.get(k) is not None else "     -"
        print(f"{lang:5} {g(('all','all'))} {g(('all','clean'))} {g(('all','noisy'))} "
              f"{g(('Read','all'))} {g(('Extempore','all'))} {g(('Conversation','all'))}")


if __name__ == "__main__":
    main()
