#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build
xcrun clang++ -std=c++17 -O2 ofx/core-test.cpp -lz -o build/ofx-core-test
build/ofx-core-test build/native-unit-frame.rif
node web/check-native-packet.mjs build/native-unit-frame.rif

xcrun clang++ -std=c++17 -O2 -pthread ofx/bounded-capture-test.cpp -o build/bounded-capture-test
build/bounded-capture-test

xcrun clang++ -std=c++17 -O2 ofx/panel-test.cpp -o build/panel-test
build/panel-test
