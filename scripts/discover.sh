#!/bin/bash
set -u
xcode-select -p
xcodebuild -version
xcodebuild -showsdks
idevice_id -l
# Run ideviceinfo -u UDID to verify ProductType and ProductVersion locally.
xcrun devicectl list devices
system_profiler SPUSBDataType -detailLevel mini
