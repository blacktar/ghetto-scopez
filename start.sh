#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
command -v node >/dev/null || { echo 'Install Node.js first: https://nodejs.org/en/download' >&2; exit 1; }
exec bash scripts/web.sh
