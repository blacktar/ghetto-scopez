#!/usr/bin/env python3
"""Create a standalone upload-ready guide ZIP and a per-file checksum manifest."""
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
release=json.loads((root/'web/public/release.mjs').read_text().split('=',1)[1].strip().rstrip(';'))
source=root/'web/public/guide'
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'build'
out.mkdir(parents=True,exist_ok=True)
stem=f'ghettoscopes_{release["date"]}_v{release["version"]}'
files=sorted(p for p in source.rglob('*') if p.is_file() and p.name!='.DS_Store')
manifest={'version':release['version'],'date':release['date'],'entrypoint':'index.html','files':[]}
payloads={}
for p in files:
 name=p.relative_to(source).as_posix();data=p.read_bytes();payloads[name]=data
 manifest['files'].append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
payloads['deployment-manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
payloads['SHA256SUMS']=(''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in sorted(payloads.items()))).encode()
archive=out/(stem+'.zip')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,data in sorted(payloads.items()):z.writestr(name,data)
archive.with_suffix('.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print(f'{archive} ({archive.stat().st_size/1024/1024:.1f} MiB; {len(payloads)} files; index.html at ZIP root)')
