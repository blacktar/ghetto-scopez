#!/usr/bin/env python3
"""Package tracked source and pinned browser/host dependencies for Mac users."""
import hashlib,json,subprocess,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
version=(root/'web/VERSION').read_text().strip()
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'build'/f'Ghetto-Scopez-{version}-mac.zip'
out.parent.mkdir(parents=True,exist_ok=True)
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
required=json.loads((root/'web/package.json').read_text())['dependencies']
extra=[]
for name,expected in required.items():
 package=root/'web/node_modules'/name
 actual=json.loads((package/'package.json').read_text())['version']
 if actual!=expected:raise SystemExit(f'{name}: expected {expected}, found {actual}')
 # Ship runtime files and their licences, excluding examples and source tooling.
 paths=[package/'package.json',package/'LICENSE']
 if name=='ws':paths += [package/'index.js',package/'wrapper.mjs',*(package/'lib').glob('*.js')]
 elif name=='nosleep.js':paths += [package/'dist/NoSleep.min.js']
 elif name=='three':paths += list((package/'build').glob('*.js'))
 extra += [str(p.relative_to(root)) for p in paths if p.is_file()]
files=sorted(set(filter(None,tracked+extra)))
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for rel in files:z.write(root/rel,'Ghetto-Scopez/'+rel)
out.with_suffix('.sha256').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n')
print(f'{out} ({out.stat().st_size/1024/1024:.1f} MiB, {len(files)} files)')
