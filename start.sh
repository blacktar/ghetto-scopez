#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
command -v node >/dev/null || { echo 'Double-click Install.command first.' >&2; exit 1; }
# A second launch opens the existing host instead of replacing it.
if curl --fail --silent --max-time 1 http://127.0.0.1:8765/api/tap-info | /usr/bin/grep -q 'Scopes host: connected'; then
 open http://127.0.0.1:8765/guide/index.html
 echo 'Ghetto Scopez is already running.'
 exit 0
fi
SCOPE_DIAGNOSTICS=0 HOST=0.0.0.0 node web/server.mjs &
host_pid=$!
trap 'kill "$host_pid" 2>/dev/null || true' EXIT
trap 'exit 0' INT TERM
for attempt in {1..100}; do
 kill -0 "$host_pid" 2>/dev/null || { echo 'The host could not start. Review the message above.' >&2; exit 1; }
 if curl --fail --silent --max-time 1 http://127.0.0.1:8765/api/tap-info >/dev/null; then
  open http://127.0.0.1:8765/guide/index.html
  echo 'Keep this window open while using the scopes. Press Control-C to stop.'
  wait "$host_pid"
  exit $?
 fi
 sleep .1
done
echo 'The host did not become ready.' >&2
exit 1
