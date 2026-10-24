#!/usr/bin/env python3
"""Package tracked source and pinned browser/host dependencies for Mac users."""
import hashlib,json,os,stat,subprocess,sys,zipfile
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
 directories=sorted({'Ghetto-Scopez/'}|{'Ghetto-Scopez/'+str(parent)+'/' for rel in files for parent in Path(rel).parents if str(parent)!='.'})
 for name in directories:
  info=zipfile.ZipInfo(name);info.create_system=3
  info.external_attr=((stat.S_IFDIR|0o755)<<16)|0x10;z.writestr(info,b'')
 for rel in files:
  path=root/rel;info=zipfile.ZipInfo.from_file(path,'Ghetto-Scopez/'+rel)
  mode=0o755 if path.stat().st_mode&0o111 or path.suffix in ['.command','.sh'] else 0o644
  info.create_system=3;info.external_attr=(stat.S_IFREG|mode)<<16;info.compress_type=zipfile.ZIP_DEFLATED
  z.writestr(info,path.read_bytes())
with zipfile.ZipFile(out) as z:
 for info in z.infolist():
  mode=stat.S_IMODE(info.external_attr>>16)
  if mode not in ([0o755] if info.is_dir() else [0o644,0o755]):raise RuntimeError('Invalid release permissions: '+info.filename)
 if z.testzip():raise RuntimeError('Archive CRC validation failed')
os.chmod(out,0o644)
out.with_suffix('.sha256').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n')
print(f'{out} ({out.stat().st_size/1024/1024:.1f} MiB, {len(files)} files)')
