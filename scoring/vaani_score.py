"""Score Vaani Benchmark V1.0 (Hindi) with the dataset's own official method.

    python scoring/vaani_score.py [predictions/vaani-benchmark/hi.native.given.jsonl]

Vaani gives three independent human transcriptions per clip, written with
code-switch glosses (`टाइम {time}`) and event tags (`<noise>`, `[breathing]`).
Our single-reference Vistaar normaliser does not know these conventions, so the
generic number in results/scores.csv is not meaningful for Vaani. This script
is the reported Vaani number.

It uses the official toolkit (tools/third_party/vaani-toolkit, ARTPARK-IISc,
commit a15e24e) unchanged:
  1. transliteration: a Latin word in the hypothesis becomes Devanagari only if
     the exact lowercase word is in the toolkit's corpus-mined lookup;
  2. clean_text() on references and hypothesis;
  3. approach3_wer(): the 3-reference "Hindi_WER".

The 95% interval is a bootstrap over clips. For that we need per-clip counts,
which the toolkit does not return, so `_clip_counts` restates its counting
rule; the script asserts that the summed counts reproduce the official
approach3_wer exactly before it reports anything.

Writes results/vaani_official.json.
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLKIT = ROOT / "tools" / "third_party" / "vaani-toolkit"
sys.path.insert(0, str(TOOLKIT))
from run_eval import approach3_wer, clean_text  # noqa: E402
from jiwer import process_words  # noqa: E402

BOOTSTRAP = 1000
SEED = 20261028
LOOKUP = json.loads((TOOLKIT / "vaani_en_deva_lookup.json").read_text(encoding="utf-8"))
WORD_RE = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")  # as transliterate_predictions.py


def transliterate(text: str) -> str:
    return WORD_RE.sub(lambda m: LOOKUP.get(m.group(0).lower(), m.group(0)), text)


def _clip_counts(r1: str, r2: str, r3: str, hyp: str) -> tuple[int, int]:
    """(errors, reference length) for one clip, by the approach3_wer rule."""
    word_errors: dict[int, list[str]] = {}
    deleted_per_ref = []
    hyp_words = hyp.split()
    for ref in (r1, r2, r3):
        out = process_words(ref, hyp)
        hyp_words = out.hypotheses[0]
        ref_words = out.references[0]
        deleted = set()
        for c in out.alignments[0]:
            if c.type == "delete":
                deleted.update(ref_words[c.ref_start_idx:c.ref_end_idx])
            else:
                label = {"equal": "correct", "insert": "insert", "substitute": "substitute"}[c.type]
                for i in range(c.hyp_start_idx, c.hyp_end_idx):
                    word_errors.setdefault(i, []).append(label)
        deleted_per_ref.append(deleted)
    dels = len(set.intersection(*deleted_per_ref))
    subs = sum(1 for v in word_errors.values() if "correct" not in v and "substitute" in v)
    ins = sum(1 for v in word_errors.values()
              if "correct" not in v and "substitute" not in v and "insert" in v)
    return subs + ins + dels, dels - ins + len(hyp_words)


def main():
    pred_path = Path(sys.argv[1]).resolve() if sys.argv[1:] else ROOT / "predictions/vaani-benchmark/hi.native.given.jsonl"
    manifest = ROOT / "datasets/vaani-benchmark/hi/manifest.jsonl"
    refs = {}
    with manifest.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            refs[r["id"]] = r["refs"]
    hyps = {}
    with pred_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r["id"] not in hyps or r["status"] == 200:
                    hyps[r["id"]] = (r["hyp"] or "") if r["status"] == 200 else ""

    ids = sorted(refs)
    missing = sum(1 for i in ids if i not in hyps)
    r1, r2, r3, hy, hy_raw = [], [], [], [], []
    for i in ids:
        a, b, c = (clean_text(x) for x in refs[i])
        raw = clean_text(hyps.get(i, ""))
        r1.append(a); r2.append(b); r3.append(c)
        hy_raw.append(raw)
        hy.append(clean_text(transliterate(hyps.get(i, ""))))

    official = approach3_wer(r1, r2, r3, hy)
    official_no_translit = approach3_wer(r1, r2, r3, hy_raw)
    counts = [_clip_counts(a, b, c, h) for a, b, c, h in zip(r1, r2, r3, hy)]
    mirrored = sum(e for e, _ in counts) / sum(n for _, n in counts)
    assert abs(mirrored - official) < 1e-12, (mirrored, official)

    rng = random.Random(SEED)
    boots = []
    for _ in range(BOOTSTRAP):
        s = [counts[rng.randrange(len(counts))] for _ in counts]
        boots.append(sum(e for e, _ in s) / sum(n for _, n in s))
    boots.sort()

    out = {
        "dataset": "vaani-benchmark", "lang": "hi", "clips": len(ids), "missing_predictions": missing,
        "method": "official ARTPARK-IISc toolkit: transliterate_predictions + clean_text + approach3_wer",
        "hindi_wer": round(100 * official, 2),
        "hindi_wer_ci95": [round(100 * boots[int(0.025 * BOOTSTRAP)], 2),
                           round(100 * boots[int(0.975 * BOOTSTRAP) - 1], 2)],
        "hindi_wer_without_transliteration": round(100 * official_no_translit, 2),
        "predictions": str(pred_path.relative_to(ROOT)).replace("\\", "/"),
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/vaani_official.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
