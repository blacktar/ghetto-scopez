#!/usr/bin/env python3
"""Create a standalone upload-ready guide ZIP and a per-file checksum manifest."""
import json,os,re,stat,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
release=json.loads((root/'web/public/release.mjs').read_text().split('=',1)[1].strip().rstrip(';'))
source=root/'web/public/guide'
guide_version=(root/'web/GUIDE_VERSION').read_text().strip()
if not re.fullmatch(re.escape(release['version'])+r'(?:-r[1-9][0-9]*)?',guide_version):raise SystemExit('Guide revision does not match the current viewer release')
html=(source/'index.html').read_text()
if f'Guide {guide_version} · Viewer {release["version"]} · GTap ' not in html:raise SystemExit('Stamp the visible guide release before packaging')
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'build'
out.mkdir(parents=True,exist_ok=True)
stem=f'ghettoscopes_{release["date"]}_v{guide_version}'
files=sorted(p for p in source.rglob('*') if p.is_file() and p.name!='.DS_Store')
manifest={'version':guide_version,'viewerVersion':release['version'],'date':release['date'],'entrypoint':'index.html','files':[]}
payloads={}
for p in files:
 name=p.relative_to(source).as_posix();data=p.read_bytes();payloads[name]=data
 manifest['files'].append({'path':name,'bytes':len(data)})
payloads['deployment-manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
archive=out/(stem+'.zip')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 # Explicit Unix permissions survive extraction on deployment servers.
 directories=sorted({str(parent)+'/' for name in payloads for parent in Path(name).parents if str(parent)!='.'})
 for name in directories:
  info=zipfile.ZipInfo(name);info.create_system=3
  info.external_attr=((stat.S_IFDIR|0o755)<<16)|0x10
  z.writestr(info,b'')
 for name,data in sorted(payloads.items()):
  info=zipfile.ZipInfo(name);info.create_system=3
  info.external_attr=(stat.S_IFREG|0o644)<<16
  info.compress_type=zipfile.ZIP_DEFLATED
  z.writestr(info,data)
with zipfile.ZipFile(archive) as z:
 for info in z.infolist():
  expected=0o755 if info.is_dir() else 0o644
  if stat.S_IMODE(info.external_attr>>16)!=expected:
   raise RuntimeError(f'Incorrect deployment permissions: {info.filename}')
os.chmod(archive,0o644)
print(f'{archive} ({archive.stat().st_size/1024/1024:.1f} MiB; {len(payloads)} files; index.html at ZIP root)')
