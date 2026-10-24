#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
fail(){ printf '\nInstallation stopped: %s\n' "$*" >&2; exit 1; }
[[ "$(uname -s)" == Darwin ]] || fail 'This release requires macOS.'
[[ "${1:-}" == '' || "${1:-}" == '--check' ]] || fail 'Usage: bash install.sh [--check]'
[[ "$(sw_vers -productVersion | cut -d. -f1)" -ge 27 ]] || fail 'The included GTap binary requires macOS 27 or later.'
for payload in release/GTap-v1.2.23.ofx.bundle.zip release/scope-analysis.node; do
 [[ -f "$payload" ]] || fail 'Download and unzip the complete Mac release package.'
done
shasum -a 256 -c release/SHA256SUMS || fail 'Release checksum mismatch. Download a fresh package.'
codesign --verify --strict release/scope-analysis.node
node_ready=false
if command -v node >/dev/null && node -e 'if(+process.versions.node.split(".")[0]<20)process.exit(1)' 2>/dev/null; then node_ready=true; fi
printf 'Release files and macOS requirements OK.\n'
if [[ "${1:-}" == '--check' ]]; then
 [[ "$node_ready" == true ]] && echo 'Compatible Node.js is available.' || echo 'Setup will install the official Node.js package automatically.'
 exit 0
fi
# Wait for the user to close Resolve without asking them to run another command.
if pgrep -x Resolve >/dev/null; then
 printf 'Please quit DaVinci Resolve. Setup will continue automatically when it closes.\n'
 while pgrep -x Resolve >/dev/null; do sleep 2; done
fi
staging="$(mktemp -d "${TMPDIR:-/tmp}/ghetto-scopez-install.XXXXXX")"
trap 'rm -rf "$staging"' EXIT
if [[ "$node_ready" != true ]]; then
 printf 'Downloading the official Node.js installer…\n'
 curl --fail --location --proto '=https' --tlsv1.2 --retry 2 https://nodejs.org/dist/v24.22.1/node-v24.22.1.pkg -o "$staging/node.pkg"
 actual="$(shasum -a 256 "$staging/node.pkg" | cut -d' ' -f1)"
 [[ "$actual" == ca7618402754944626787fca386c406a041541f097da172e92348d8b1e44e48b ]] || fail 'Official Node.js package checksum mismatch.'
 signature="$(pkgutil --check-signature "$staging/node.pkg")" || fail 'Node.js installer signature verification failed.'
 [[ "$signature" == *'Developer ID Installer: Node.js Foundation (HX7739G8FX)'* ]] || fail 'Unexpected Node.js installer signer.'
fi
printf 'Enter your Mac administrator password when requested.\n'
sudo -v
if [[ "$node_ready" != true ]]; then sudo /usr/sbin/installer -pkg "$staging/node.pkg" -target /; fi
command -v node >/dev/null || fail 'Node.js did not become available after installation.'
# Release archives include these dependencies; source checkouts can fetch them.
if [[ ! -d web/node_modules/ws || ! -d web/node_modules/nosleep.js || ! -d web/node_modules/three ]]; then
 npm --prefix web --cache "$PWD/.npm-cache" ci --no-audit --no-fund
fi
mkdir -p build
cp release/scope-analysis.node build/scope-analysis.node
node -e 'require("./build/scope-analysis.node")' || fail 'The bundled host component could not load.'
target='/Library/OFX/Plugins/SignalLabTap.ofx.bundle'
if [[ -e "$target" ]]; then
 identity="$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$target/Contents/Info.plist")"
 [[ "$identity" == local.signallab.ResolveTap ]] || fail 'A different plugin is present at the installation path.'
fi
ditto -x -k release/GTap-v1.2.23.ofx.bundle.zip "$staging"
codesign --verify --deep --strict "$staging/SignalLabTap.ofx.bundle"
sudo /bin/mkdir -p /Library/OFX/Plugins
pgrep -x Resolve >/dev/null && fail 'Resolve reopened during setup. Close it and run Install again.'
sudo /usr/bin/ditto "$staging/SignalLabTap.ofx.bundle" "$target"
codesign --verify --deep --strict "$target"
printf '\nInstalled. Starting Ghetto Scopez and opening the guide…\n'
open -a Terminal "$PWD/Start.command"
