#!/usr/bin/env python3
"""Back up Resolve's cache and forget only this tap's stale scan result."""
import datetime
import pathlib
import re
import shutil
import subprocess

running = subprocess.run(['pgrep', '-x', 'Resolve'], capture_output=True)
if running.returncode == 0:
    raise SystemExit('Quit Resolve fully before repairing its OFX cache.')
if running.returncode != 1:
    raise SystemExit('Cannot verify that Resolve is closed; no cache changes made.')
root = pathlib.Path.home() / 'Library/Application Support/Blackmagic Design/DaVinci Resolve'
for name in ('OFXPluginCacheV2.xml', 'OFXPluginCache.xml'):
    path = root / name
    if not path.exists():
        continue
    text = path.read_text()
    pattern = r'<bundle\b[^>]*>.*?</bundle>'
    def keep_other_bundle(match):
        block = match.group(0)
        return '' if '/SignalLabTap.ofx.bundle' in block else block
    updated = re.sub(pattern, keep_other_bundle, text, flags=re.S)
    if updated == text:
        print(f'No tap entry in {name}')
        continue
    backup = path.with_name(name + '.ghetto-tap-backup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(path, backup)
    path.write_text(updated)
    print(f'Removed only tap entry from {name}; backup: {backup}')
print('Start Resolve to rescan Ghetto Tap.')
