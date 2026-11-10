#!/usr/bin/env bash
# Run a list of benchmark jobs one after another.
#   [LANGUAGE=<code>] bash tools/run_queue.sh "<manifest-glob> <mode>" ...
# Each argument is a glob of dataset language folders plus the output mode.
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
for job in "$@"; do
  set -f; set -- $job; set +f
  glob=$1; mode=$2
  for d in $glob; do
    ./.venv/Scripts/python tools/run_blackbird.py "$d/${MANIFEST:-manifest.jsonl}" --mode "$mode" --language "${LANGUAGE:-manifest}" --concurrency 28 2>&1 | grep -E "clips,|finished"
  done
done
echo "QUEUE DONE $(date +%T)"
