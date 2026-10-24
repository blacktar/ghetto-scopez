#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
probe_python="${VISUAL_PYTHON:-python3}"
"$probe_python" -c 'import PIL,numpy' || { echo 'Install web/visual-requirements.txt or set VISUAL_PYTHON.' >&2; exit 1; }
# Optional project-local dependencies; install with:
# python3 -m pip install --target web/.visual-deps -r web/visual-requirements.txt
export PYTHONPATH="$(pwd)/web/.visual-deps:$(pwd)/../../work/tiff-deps${PYTHONPATH:+:$PYTHONPATH}"
"$probe_python" -c 'import tifffile' || { echo 'Install web/visual-requirements.txt before comparison.' >&2; exit 1; }
"$probe_python" "${VISUAL_COMPARATOR:-web/visual-compare.py}" "${1:-docs/visual-validation}"
