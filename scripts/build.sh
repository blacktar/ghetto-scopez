#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec xcodebuild -project ipad/ScopesProbe.xcodeproj -scheme ScopesProbe -sdk iphoneos -configuration Debug -derivedDataPath build CODE_SIGNING_ALLOWED=NO build
