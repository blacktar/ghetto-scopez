#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../web"
if [[ ! -d node_modules/three || ! -d node_modules/ws ]]; then
  npm --cache ../.npm-cache ci --no-audit --no-fund
fi
if [[ ! -f ../build/scope-analysis.node || ../web/native-analysis.cpp -nt ../build/scope-analysis.node || ../web/native-ingest.hpp -nt ../build/scope-analysis.node || ../scripts/build-analysis.sh -nt ../build/scope-analysis.node ]]; then
  bash ../scripts/build-analysis.sh
fi
# Explicit LAN binding so Safari on the iPad can reach the local scope viewer.
HOST=0.0.0.0 exec node server.mjs
