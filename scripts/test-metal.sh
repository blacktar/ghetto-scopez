#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build
xcrun clang++ -std=c++17 -O2 -fobjc-arc -fblocks ofx/metal-test.mm ofx/MetalTap.mm -framework Metal -framework Foundation -lz -o build/metal-test
build/metal-test
