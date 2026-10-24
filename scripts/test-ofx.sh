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

xcrun clang++ -std=c++17 -O2 ofx/tap-signal-test.cpp -o build/tap-signal-test
build/tap-signal-test > build/tap-signals.jsonl
node --input-type=module -e 'import fs from "node:fs";import assert from "node:assert/strict";import {signalSpec} from "./web/public/signal.mjs";const s=fs.readFileSync("build/tap-signals.jsonl","utf8").trim().split("\n").map(v=>signalSpec(JSON.parse(v)));assert.deepEqual(s.map(v=>v.domain),["encoded","encoded","working"]);assert.equal(s[2].primaries,"unknown");assert.equal(s[2].matrix,"bt709");console.log("PASS GTap choice metadata and JS signal parser agree");'
