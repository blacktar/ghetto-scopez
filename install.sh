#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
fail(){ printf 'Installation stopped: %s\n' "$*" >&2; exit 1; }
[[ "$(uname -s)" == Darwin ]] || fail 'This release requires macOS.'
[[ "${1:-}" == '' || "${1:-}" == '--check' ]] || fail 'Usage: bash install.sh [--check]'
[[ "$(sw_vers -productVersion | cut -d. -f1)" -ge 27 ]] || fail 'The included GTap 1.2.23 binary requires macOS 27 or later.'
command -v node >/dev/null || fail 'Install Node.js from https://nodejs.org/en/download, then try again.'
command -v npm >/dev/null || fail 'npm is missing. Reinstall the official Node.js macOS package.'
node -e 'if(+process.versions.node.split(".")[0]<20)process.exit(1)' || fail 'Node.js 20 or later is required. Use a current LTS release.'
archive='release/GTap-v1.2.23.ofx.bundle.zip'
[[ -f "$archive" ]] || fail 'Download the complete Ghetto Scopez release ZIP, not just the source archive.'
shasum -a 256 -c release/SHA256SUMS || fail 'The plugin checksum does not match. Download a fresh release.'
if [[ ! -f build/scope-analysis.node ]]; then
 xcrun --find clang++ >/dev/null 2>&1 || fail 'Run xcode-select --install, finish the Apple tools installation, then try again.'
fi
printf 'Requirements and release checksum OK.\n'
[[ "${1:-}" != '--check' ]] || exit 0
pgrep -x Resolve >/dev/null && fail 'Quit DaVinci Resolve before installing GTap.'
npm --prefix web --cache "$PWD/.npm-cache" ci --no-audit --no-fund
if [[ ! -f build/scope-analysis.node ]]; then bash scripts/build-analysis.sh; fi
node -e 'require("./build/scope-analysis.node")' || fail 'The native host component could not load.'
target='/Library/OFX/Plugins/SignalLabTap.ofx.bundle'
if [[ -e "$target" ]]; then
 identity="$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$target/Contents/Info.plist")"
 [[ "$identity" == local.signallab.ResolveTap ]] || fail 'A different plugin is present at the installation path.'
fi
staging="$(mktemp -d "${TMPDIR:-/tmp}/ghetto-scopez-install.XXXXXX")"
trap 'rm -rf "$staging"' EXIT
ditto -x -k "$archive" "$staging"
codesign --verify --deep --strict "$staging/SignalLabTap.ofx.bundle"
printf 'Installing GTap; macOS may ask for your administrator password.\n'
sudo /bin/mkdir -p /Library/OFX/Plugins
# Check again immediately before changing the effect.
pgrep -x Resolve >/dev/null && fail 'Resolve opened during setup. Quit it and rerun the installer.'
sudo /usr/bin/ditto "$staging/SignalLabTap.ofx.bundle" "$target"
codesign --verify --deep --strict "$target"
printf '\nInstalled GTap 1.2.23. Start the host with: bash start.sh\nThen open Resolve and follow web/public/guide/index.html.\n'
