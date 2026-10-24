#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/embed-metal.py
sdk="${OFX_SDK:-/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/OpenFX}"
staging="$(mktemp -d "${TMPDIR:-/tmp}/signallab-ofx.XXXXXX")"
bundle="$staging/SignalLabTap.ofx.bundle"
# Keep the bundle/identifier stable so saved Resolve projects find their tap.
release="$(cat ofx/VERSION)"
[[ "$release" =~ ^[0-9]+\.[0-9]+$ ]] || { echo 'Invalid OFX release version' >&2; exit 1; }
major="${release%.*}"; minor="${release#*.}"
mkdir -p build
build_number=0
[[ ! -f build/ofx-build-number ]] || build_number="$(cat build/ofx-build-number)"
[[ "$build_number" =~ ^[0-9]+$ ]] || exit 1
build_number=$((build_number + 1))
version="$release.$build_number"
cat > "$staging/TapVersion.hpp" <<VERSION
#define GHETTO_TAP_MAJOR $major
#define GHETTO_TAP_MINOR $minor
#define GHETTO_TAP_BUILD $build_number
#define GHETTO_TAP_VERSION "$version"
#define GHETTO_TAP_LABEL "GTap v$version"
VERSION
mkdir -p "$bundle/Contents/MacOS" build/ofx-objects
flags=(-I"$staging" -std=c++17 -O2 -fvisibility=hidden -arch arm64 -arch x86_64 -I"$sdk/OpenFX-1.4/include" -I"$sdk/Support/include")
objects=()
for name in ofxsCore ofxsImageEffect ofxsInteract ofxsLog ofxsMultiThread ofxsParams ofxsProperty ofxsPropertyValidation; do
 object="build/ofx-objects/$name.o"
 if [[ ! -f "$object" ]]; then xcrun clang++ "${flags[@]}" -c "$sdk/Support/Library/$name.cpp" -o "$object"; fi
 objects+=("$object")
done
xcrun clang++ "${flags[@]}" -fobjc-arc -fblocks -bundle ofx/SignalLabTap.cpp ofx/MetalTap.mm ofx/MetalAnalysis.mm ofx/TapPanel.mm "${objects[@]}" -framework AppKit -framework Metal -framework Foundation -lz -o "$bundle/Contents/MacOS/SignalLabTap.ofx"
cat > "$bundle/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>CFBundleIdentifier</key><string>local.signallab.ResolveTap</string><key>CFBundleName</key><string>GTap</string><key>CFBundleExecutable</key><string>SignalLabTap.ofx</string><key>CFBundleVersion</key><string>$version</string><key>CFBundleShortVersionString</key><string>$version</string><key>CFBundlePackageType</key><string>BNDL</string></dict></plist>
PLIST
mkdir -p "$bundle/Contents/Resources"
cp ofx/THIRD-PARTY-NOTICES.txt "$bundle/Contents/Resources/THIRD-PARTY-NOTICES.txt"
xattr -d com.apple.FinderInfo "$bundle" 2>/dev/null || true
codesign --force --sign - "$bundle"
codesign --verify --deep --strict "$bundle"
ditto -c -k --norsrc --keepParent "$bundle" "build/GTap-v$version.ofx.bundle.zip"
cp "build/GTap-v$version.ofx.bundle.zip" build/GTap.ofx.bundle.zip
printf '%s\n' "$build_number" > build/ofx-build-number
printf '%s\n' "$version" > build/ofx-release-version
printf 'Built and signed GTap v%s\nArchive: %s/build/GTap-v%s.ofx.bundle.zip\n' "$version" "$(pwd)" "$version"
