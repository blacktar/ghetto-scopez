#!/usr/bin/env python3
"""Package changed guide files for overlay onto an earlier deployment ZIP."""
import argparse,hashlib,stat,zipfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('baseline',type=Path);p.add_argument('target',type=Path);p.add_argument('output',type=Path)
a=p.parse_args()
def read(path):
 with zipfile.ZipFile(path) as z:
  if z.testzip():raise SystemExit('Invalid ZIP: '+str(path))
  return {i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
old,new=read(a.baseline),read(a.target)
removed=old.keys()-new.keys()
if removed:raise SystemExit('Overlay cannot remove files: '+', '.join(sorted(removed)))
changed={k:v for k,v in new.items() if old.get(k)!=v}
a.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(a.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in sorted({str(parent)+'/' for name in changed for parent in Path(name).parents if str(parent)!='.'}):
  info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=((stat.S_IFDIR|0o755)<<16)|0x10;z.writestr(info,b'')
 for name,data in sorted(changed.items()):
  info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFREG|0o644)<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
# Applying this overlay must reproduce every target file exactly.
assert {**old,**read(a.output)}==new
with zipfile.ZipFile(a.output) as z:
 assert all(stat.S_IMODE(i.external_attr>>16)==(0o755 if i.is_dir() else 0o644) for i in z.infolist())
a.output.chmod(0o644)
sidecar=a.output.with_suffix('.sha256');sidecar.write_text(hashlib.sha256(a.output.read_bytes()).hexdigest()+'  '+a.output.name+'\n');sidecar.chmod(0o644)
print(f'{a.output.resolve()} ({a.output.stat().st_size/1024/1024:.2f} MiB; {len(changed)} changed files; no deletions)')
