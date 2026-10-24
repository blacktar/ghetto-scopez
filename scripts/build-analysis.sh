#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build
node_prefix_headers="$(node -p 'require("path").resolve(process.execPath,"../../include/node")')"
node_headers="${NODE_HEADERS:-$node_prefix_headers}"
if [[ ! -f "$node_headers/node_api.h" && -z "${NODE_HEADERS:-}" ]]; then node_headers=/usr/local/include/node; fi
test -f "$node_headers/node_api.h" || { echo 'Set NODE_HEADERS to the installed Node.js include directory.' >&2; exit 1; }
xcrun clang++ -std=c++17 -O3 -fno-fast-math -ffp-contract=off -fPIC -shared -undefined dynamic_lookup -I "$node_headers" web/native-analysis.cpp -lz -o build/scope-analysis.node
echo 'Built native exact-count CPU analysis kernel.'
