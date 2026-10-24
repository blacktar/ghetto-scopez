#!/bin/bash
set -euo pipefail
: "${1:?Usage: bash scripts/usb.sh DEVICE_UDID}"
# -l restricts discovery to USB; never add -n for wired acceptance.
exec iproxy -l -u "$1" -s 127.0.0.1 23456:23456
