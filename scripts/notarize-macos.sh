#!/bin/bash
set -euo pipefail
package="${1:?Usage: notarize-macos.sh path/to/installer.pkg}"
profile="${NOTARY_PROFILE:-ghetto-scopez-notary}"
xcrun notarytool submit "$package" --keychain-profile "$profile" --wait --output-format json > "$package.notary.json"
cat "$package.notary.json"
id=$(/usr/bin/plutil -extract id raw -o - "$package.notary.json")
xcrun notarytool log "$id" --keychain-profile "$profile" "$package.notary-log.json"
status=$(/usr/bin/plutil -extract status raw -o - "$package.notary.json")
[[ "$status" == Accepted ]] || { echo 'Notarization not accepted; inspect the log.' >&2; exit 1; }
xcrun stapler staple "$package"
xcrun stapler validate "$package"
spctl --assess --type install --verbose=2 "$package"
