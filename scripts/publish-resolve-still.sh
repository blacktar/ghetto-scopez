#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${1:-}" != bt709 && "${1:-}" != bt2020-ncl ]];then echo 'Usage: bash scripts/publish-resolve-still.sh bt709|bt2020-ncl (declare actual output primaries)' >&2;exit 1;fi
frame="$(pwd)/docs/resolve-validation/resolve-current-frame.tif"
python3 host/export-resolve.py "$frame"
probe_python="${VISUAL_PYTHON:-python3}"
export PYTHONPATH="$(pwd)/web/.visual-deps:$(pwd)/../../work/tiff-deps${PYTHONPATH:+:$PYTHONPATH}"
"$probe_python" host/publish-tiff.py "$frame" --matrix "$1"
