"""Download the public test sets used in the Blackbird ASR v1 benchmark, at the
exact versions benchmarked, into downloads/.

    python tools/download.py all                 # everything (about 20 GB)
    python tools/download.py svarah lahaja ...   # or selected sets

Hugging Face sets are pinned to the commit that was benchmarked. Four of them
are gated (IndicVoices, Lahaja, Svarah, Vaani): accept each dataset's terms on
its Hugging Face page first, then set HF_TOKEN to a token of that account.
Archives from other hosts are checked against the SHA-256 recorded when they
were benchmarked. After downloading, run the prepare step for each set
(README.md), which writes datasets/<set>/<lang>/ with audio and manifest.jsonl.
"""
from __future__ import annotations

import hashlib
import os
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DL = ROOT / "downloads"

HF = {  # name: (repo, revision, files to fetch, local folder)
    "indicvoices": ("ai4bharat/IndicVoices", "c96f9088f138cf89d419da7e8e643e1f05c00a87",
                    ["*/valid-*.parquet"], "IndicVoices"),
    "lahaja": ("ai4bharat/Lahaja", "d4ffd2ecbdd933e37c917ddcf620eef159ceb3a7",
               ["data/test-*.parquet"], "Lahaja"),
    "svarah": ("ai4bharat/Svarah", "ebbf7777fe771490696a3f7b007097606fa8c924",
               ["data/test-*.parquet"], "Svarah"),
    "vaani": ("ARTPARK-IISc/Vaani-Benchmark-V1.0", "d742f1cca7111ac5e9890bffbc91e6df79517627",
              ["data/test-*.parquet"], "Vaani-Benchmark-V1.0"),
    "hiacc-adult": ("Trelis/hiacc-adult-test-eval", "45782b4752f1e353173cd0b940332a984fc0a249",
                    ["data/*.parquet"], "hiacc-adult-test-eval"),
    "hiacc-child": ("Trelis/hiacc-child-test-eval", "19f4fda91183b889f642e1e16c88c7bbeda64dad",
                    ["data/*.parquet"], "hiacc-child-test-eval"),
}
VISTAAR = "https://indicwhisper.objectstore.e2enetworks.net/vistaar_benchmarks/{}.zip"
ARCHIVES = {  # name: (url, sha256, unpack into)
    "kathbath": (VISTAAR.format("kathbath"),
                 "cb7d4fcdef4d3dc6303bb52cf665cbf567ba4dc0664590041c14a3e9c01d23de", "vistaar"),
    "fleurs": (VISTAAR.format("fleurs"),
               "0e1abc2d687ca78f4dda424bb6595997f23d5417855bd0c9b54739666fc252ed", "vistaar"),
    "commonvoice": (VISTAAR.format("commonvoice"),
                    "3fcd15bcef9e1f46d1402f889ede8b79700c4dd7cb97b95f885811f298359c5f", "vistaar"),
    "mucs-cs-hi": ("https://www.openslr.org/resources/104/Hindi-English_test.tar.gz",
                   "93e358b3bf8233a897fcd353c1f4f98fdda6b8c01b7eed17a70c7dd26e984b37", "mucs_cs"),
    "mucs-cs-bn": ("https://www.openslr.org/resources/104/Bengali-English_test.tar.gz",
                   "2e3604eab0839be8c4e2d92cdd2638a91922fbd7b16ddd08465c0e8e8b64bfe1", "mucs_cs_bn"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch_hf(name: str) -> None:
    from huggingface_hub import snapshot_download
    repo, rev, patterns, folder = HF[name]
    print(f"{name}: {repo} @ {rev[:12]}", flush=True)
    snapshot_download(repo_id=repo, repo_type="dataset", revision=rev, allow_patterns=patterns,
                      local_dir=DL / folder, token=os.environ.get("HF_TOKEN"))


def fetch_archive(name: str) -> None:
    url, digest, into = ARCHIVES[name]
    DL.mkdir(exist_ok=True)
    dest = DL / url.rsplit("/", 1)[1]
    if not dest.exists() or sha256(dest) != digest:
        print(f"{name}: downloading {url}", flush=True)
        urllib.request.urlretrieve(url, dest)
    if sha256(dest) != digest:
        raise SystemExit(f"{dest.name}: SHA-256 does not match the benchmarked archive.")
    print(f"{name}: SHA-256 verified, unpacking into downloads/{into}/", flush=True)
    (DL / into).mkdir(exist_ok=True)
    if dest.suffix == ".zip":
        with zipfile.ZipFile(dest) as z:
            z.extractall(DL / into)
    else:
        with tarfile.open(dest) as t:
            t.extractall(DL / into, filter="data")


def main(names: list[str]) -> None:
    if not names or names == ["all"]:
        names = [*HF, *ARCHIVES]
    for name in names:
        if name in HF:
            fetch_hf(name)
        elif name in ARCHIVES:
            fetch_archive(name)
        else:
            raise SystemExit(f"unknown set {name!r}; choose from: {', '.join([*HF, *ARCHIVES])}")


if __name__ == "__main__":
    main(sys.argv[1:])
