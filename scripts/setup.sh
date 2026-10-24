#!/bin/bash
set -euo pipefail
# Apple presents its license for you to review and accept.
sudo xcodebuild -license
sudo xcodebuild -runFirstLaunch
brew install libusbmuxd libimobiledevice
xcodebuild -version
iproxy --help
