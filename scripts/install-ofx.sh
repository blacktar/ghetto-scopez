#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
archive="$(pwd)/build/GTap.ofx.bundle.zip"
[[ -f "$archive" ]] || archive="$(pwd)/release/GTap-v1.2.26.ofx.bundle.zip"
[[ -f "$archive" ]] || bash scripts/build-ofx.sh
target="/Library/OFX/Plugins/SignalLabTap.ofx.bundle"
if [[ -e "$target" ]]; then
 identity="$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$target/Contents/Info.plist")"
 [[ "$identity" == local.signallab.ResolveTap ]] || { echo 'Refusing to replace a different plugin.' >&2;exit 1; }
fi
mkdir -p "/Library/OFX/Plugins"
ditto -x -k "$archive" "/Library/OFX/Plugins"
codesign --verify --deep --strict "$target"
version="$(/usr/libexec/PlistBuddy -c 'Print CFBundleVersion' "$target/Contents/Info.plist")"
echo "Installed GTap v$version. Restart Resolve to load this release."
