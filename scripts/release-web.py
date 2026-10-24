#!/usr/bin/env python3
"""Stamp a web release. No argument increments the patch version."""
import datetime,json,re,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
version_file=root/'web/VERSION'
if len(sys.argv)>1:version=sys.argv[1]
else:
 old=version_file.read_text().strip();a,b,c=map(int,old.split('.'));version=f'{a}.{b}.{c+1}'
if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise SystemExit('Expected major.minor.patch')
from zoneinfo import ZoneInfo
stamp=datetime.datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y%m%d')
version_file.write_text(version+'\n')
release={'version':version,'date':stamp}
(root/'web/public/release.mjs').write_text('export const RELEASE='+json.dumps(release)+';\n')
p=root/'web/public/scopes.html';text=p.read_text();text=re.sub(r'Ghetto Scopez \(v[^,)]+,\s*\d{8}\)',f'Ghetto Scopez (v{version}, {stamp})',text);p.write_text(text)
print(f'Ghetto Scopez v{version} ({stamp})')
