"""Critical-token error rates: numbers and negations (Hindi and English sets).

Number error rate  = reference number tokens not recognised exactly (not a
                     "hit" in the strict alignment) / reference number tokens.
                     Number tokens: anything with a digit, plus the number
                     words listed below. A digit-vs-word difference ("5" vs
                     "five") counts as an error here: this is the strict view.
Negation drop rate = negations in the reference missing from the hypothesis /
                     reference negations (per-utterance counts, so it does not
                     depend on alignment).
Negation add rate  = negations in the hypothesis that are not in the
                     reference / reference negations.

    python scoring/critical.py   ->  results/critical.csv
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import jiwer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalizer import normalize  # noqa: E402
from refs import attach_refs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

HI_NUM = set("""शून्य एक दो तीन चार पाँच पांच छह छः छ सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह पन्द्रह
सोलह सत्रह अठारह उन्नीस बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस
चालीस पचास साठ सत्तर अस्सी नब्बे सौ हज़ार हजार लाख करोड़ डेढ़ ढाई सवा साढ़े पौने""".split())
EN_NUM = set("""zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen
fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety
hundred thousand lakh lakhs crore crores million billion first second third half""".split())
HI_NEG = {"नहीं", "नही", "न", "ना", "मत"}
EN_NEG = {"not", "no", "never", "nothing", "none", "nor", "nobody", "dont", "doesnt", "didnt",
          "cant", "cannot", "wont", "isnt", "arent", "wasnt", "werent", "havent", "hasnt",
          "shouldnt", "wouldnt", "couldnt"}
# "don t" / "can t" (the hypothesis-side split contraction) still carries the negation
EN_SPLIT_NEG = re.compile(r"\b(don|doesn|didn|can|won|isn|aren|wasn|weren|haven|hasn|shouldn|wouldn|couldn) t\b")


def is_num(tok: str, lang: str) -> bool:
    return any(c.isdigit() for c in tok) or tok in (HI_NUM if lang == "hi" else EN_NUM)


def neg_count(text: str, lang: str) -> int:
    if lang == "hi":
        return sum(t in HI_NEG for t in text.split())
    n = len(EN_SPLIT_NEG.findall(text))
    return n + sum(t in EN_NEG for t in EN_SPLIT_NEG.sub("", text).split())


def main():
    out = []
    for p in sorted((ROOT / "predictions").glob("*/*.given.jsonl")):
        lang = p.name.split(".")[0]
        if lang not in ("hi", "en"):
            continue
        num_ref = num_err = neg_ref = neg_drop = neg_add = 0
        for r in attach_refs([json.loads(l) for l in p.open(encoding="utf-8") if l.strip()], p):
            ref = normalize(r["ref"], lang)
            hyp = normalize(r["hyp"] or "", lang) if r["status"] == 200 else ""
            if not ref:
                continue
            R = ref.split()
            hits = set()
            if hyp:
                o = jiwer.process_words(ref, hyp)
                for a in o.alignments[0]:
                    if a.type == "equal":
                        hits.update(range(a.ref_start_idx, a.ref_end_idx))
            for i, t in enumerate(R):
                if is_num(t, lang):
                    num_ref += 1
                    num_err += i not in hits
            nr, nh = neg_count(ref, lang), neg_count(hyp, lang)
            neg_ref += nr
            neg_drop += max(0, nr - nh)
            neg_add += max(0, nh - nr)
        out.append({
            "dataset": p.parent.name, "lang": lang, "mode": p.name.split(".")[1],
            "number_tokens": num_ref,
            "number_error_rate": round(100 * num_err / num_ref, 2) if num_ref else None,
            "negations": neg_ref,
            "negation_drop_rate": round(100 * neg_drop / neg_ref, 2) if neg_ref else None,
            "negation_add_rate": round(100 * neg_add / neg_ref, 2) if neg_ref else None,
        })
    with (ROOT / "results" / "critical.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(r)


if __name__ == "__main__":
    main()
