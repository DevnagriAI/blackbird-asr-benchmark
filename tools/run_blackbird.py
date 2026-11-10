"""Send every clip in a manifest to the hosted Blackbird ASR API and record
exactly what came back.

    python tools/run_blackbird.py datasets/kathbath/hi/manifest.jsonl --mode native

Output: predictions/<dataset>/<lang>.<mode>.<langparam>.jsonl, one line per
clip. The run resumes: clips already in the output file are skipped. Nothing is
post-processed here. Scoring happens separately (scoring/score.py), so the raw
API output is always available for inspection.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
API = os.environ.get("BLACKBIRD_API", "https://blackbird.devnagri.com/v1/transcribe")
KEY = os.environ.get("BLACKBIRD_API_KEY", "")  # your own key: blackbird.devnagri.com


def load_manifest(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


async def transcribe(session, item, audio_path, mode, lang_param, sem, retries=6):
    for attempt in range(retries):
        async with sem:
            form = aiohttp.FormData()
            form.add_field("file", audio_path.read_bytes(), filename=audio_path.name)
            form.add_field("mode", mode)
            if lang_param != "auto":
                form.add_field("language", lang_param)
            t0 = time.perf_counter()
            try:
                async with session.post(API, data=form) as resp:
                    body = await resp.text()
                    wall = time.perf_counter() - t0
                    if resp.status == 200:
                        return resp.status, json.loads(body), wall
                    if resp.status not in (429, 500, 502, 503, 504):
                        return resp.status, {"error": body[:500]}, wall
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                body, wall = repr(exc), time.perf_counter() - t0
        await asyncio.sleep(min(30, 2 ** attempt))
    return -1, {"error": f"gave up after {retries} attempts: {body[:300]}"}, wall


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--mode", default="native", choices=["native", "mixed", "romanized"])
    ap.add_argument("--language", default="manifest",
                    help="'manifest' = pass each clip's own language; 'auto' = let the model detect it")
    ap.add_argument("--concurrency", type=int, default=12)
    args = ap.parse_args()

    manifest = args.manifest.resolve()
    ds_dir = manifest.parent
    dataset, lang = ds_dir.parent.name, ds_dir.name
    tag = "auto" if args.language == "auto" else "given"
    out = ROOT / "predictions" / dataset / f"{lang}.{args.mode}.{tag}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    items = load_manifest(manifest)
    done = set()
    if out.exists():
        with out.open(encoding="utf-8") as f:
            done = {json.loads(l)["id"] for l in f if l.strip() and json.loads(l).get("status") == 200}
    todo = [it for it in items if it["id"] not in done]
    print(f"{dataset}/{lang} mode={args.mode} lang={tag}: {len(items)} clips, {len(todo)} to do -> {out.relative_to(ROOT)}",
          flush=True)
    if not todo:
        return

    sem = asyncio.Semaphore(args.concurrency)
    timeout = aiohttp.ClientTimeout(total=300)
    headers = {"Authorization": f"Bearer {KEY}", "User-Agent": "blackbird-benchmark/1.0"}
    t_start, n_ok, n_err = time.time(), 0, 0
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async def one(it):
            lang_param = "auto" if args.language == "auto" else it.get("lang", lang)
            status, body, wall = await transcribe(session, it, ds_dir / it["audio"], args.mode, lang_param, sem)
            rec = {
                "id": it["id"], "status": status, "ref": it["text"],
                "hyp": body.get("text") if status == 200 else None,
                "lang_param": lang_param, "mode": args.mode,
                "detected_language": body.get("language"),
                "language_source": body.get("language_source"),
                "low_confidence_language": body.get("low_confidence_language"),
                "language_candidates": body.get("language_candidates"),
                "duration_s": it.get("duration"),
                "api_duration_ms": body.get("duration_ms"),
                "processing_ms": body.get("processing_ms"),
                "queue_ms": body.get("queue_ms"),
                "wall_s": round(wall, 4),
                "request_id": body.get("id"),
                "error": body.get("error"),
            }
            return rec

        with out.open("a", encoding="utf-8") as f:
            for fut in asyncio.as_completed([one(it) for it in todo]):
                rec = await fut
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if rec["status"] == 200:
                    n_ok += 1
                else:
                    n_err += 1
                if (n_ok + n_err) % 500 == 0:
                    f.flush()
                    rate = (n_ok + n_err) / max(1e-6, time.time() - t_start)
                    print(f"  {n_ok + n_err}/{len(todo)}  ok={n_ok} err={n_err}  {rate:.1f} clips/s", flush=True)
    print(f"  finished: ok={n_ok} err={n_err} in {time.time() - t_start:.0f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
