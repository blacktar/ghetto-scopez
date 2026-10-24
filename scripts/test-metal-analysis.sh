#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/embed-metal.py
xcrun clang++ -std=c++17 -O2 -fobjc-arc -fblocks ofx/metal-analysis-test.mm ofx/MetalAnalysis.mm -framework Metal -framework Foundation -lz -o build/metal-analysis-test
node web/metal-validation.mjs prepare
build/metal-analysis-test "${METAL_VALIDATION_DIR:-docs/metal-analysis-19}/manifest.json"
node web/metal-validation.mjs compare
