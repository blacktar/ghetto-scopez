#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${1:-}" == "" ]]; then
  echo 'Available virtual iPads (requires installed simulator runtime):'
  xcrun simctl list devices available
  echo 'Usage: bash scripts/simulator.sh SIMULATOR_UDID'
  exit 0
fi
UDID="$1"
xcrun simctl boot "$UDID" 2>/dev/null || true
xcrun simctl bootstatus "$UDID" -b
xcodebuild -project ipad/ScopesProbe.xcodeproj -scheme ScopesProbe -sdk iphonesimulator -configuration Debug -derivedDataPath build-simulator CODE_SIGNING_ALLOWED=NO SWIFT_OPTIMIZATION_LEVEL=-Onone build
xcrun simctl install "$UDID" build-simulator/Build/Products/Debug-iphonesimulator/ScopesProbe.app
xcrun simctl launch "$UDID" org.resolveipad.ScopesProbe
echo 'Tap Start listener in the simulator, then run bash scripts/probe.sh directly (no iproxy).'
