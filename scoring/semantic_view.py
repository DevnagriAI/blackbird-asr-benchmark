"""Render a semantic sample for judging: python scoring/semantic_view.py <prefix>"""
import json, sys
for l in open(sys.argv[1] + ".sample.jsonl", encoding="utf-8"):
    r = json.loads(l)
    if not r["spans"]:
        continue
    print("#%d (%dw) REF: %s" % (r["utt"], r["ref_words"], r["ref"]))
    print("      HYP: %s" % r["hyp"])
    for k, s in enumerate(r["spans"]):
        print("   s%d %s [%s] -> [%s]" % (k, s["type"][0], s["ref"], s["hyp"]))
