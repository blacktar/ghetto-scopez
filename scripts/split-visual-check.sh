#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
VISUAL_COMPARATOR=web/split-compare.py bash scripts/visual-check.sh "${1:-docs/split-validation/visual}"
