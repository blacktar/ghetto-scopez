#!/usr/bin/env python3
"""Fast guide-only deployment: changed files, revision, permissions; no hashes."""
import argparse,datetime,json,re,stat,time,zipfile
from pathlib import Path
from zoneinfo import ZoneInfo
started=time.perf_counter()
root=Path(__file__).resolve().parents[1]
guide=root/'web/public/guide'; version_file=root/'web/GUIDE_VERSION'
state_file=root/'docs/guide-deployment-state.json'
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--init',action='store_true',help='Record current local state; pending HTML changes remain pending')
p.add_argument('--deployed',metavar='REVISION',help='Record a deployment explicitly confirmed by the user')
p.add_argument('--note',default='Guide content update')
a=p.parse_args()
def scan():
 return {f.relative_to(guide).as_posix():[f.stat().st_size,f.stat().st_mtime_ns] for f in guide.rglob('*') if f.is_file() and f.name!='.DS_Store'}
def save(state):
 state_file.parent.mkdir(parents=True,exist_ok=True);state_file.write_text(json.dumps(state,indent=2)+'\n')
current=scan();version=version_file.read_text().strip()
if a.init:
 if state_file.exists():raise SystemExit('State already exists; refusing to replace pending deployment history')
 save({'revision':version,'files':current,'pending':['index.html'],'confirmed':None,'snapshots':{version:current}})
 print('Local baseline recorded; no deployment assumed.');raise SystemExit()
if not state_file.exists():raise SystemExit('Initialise the local guide state once with --init')
state=json.loads(state_file.read_text())
if a.deployed:
 if a.deployed not in state['snapshots']:raise SystemExit('Unknown prepared revision')
 confirmed=state['snapshots'][a.deployed]
 state['confirmed']=a.deployed
 state['pending']=[name for name,sig in state['files'].items() if confirmed.get(name)!=sig]
 save(state);print('Recorded user-confirmed deployment:',a.deployed);raise SystemExit()
changed={name for name,sig in current.items() if state['files'].get(name)!=sig}
removed=state['files'].keys()-current.keys()
if not changed and not removed:
 print('No new guide changes; latest diff:',state.get('archive','not yet packaged'));raise SystemExit()
base,_,revision=version.partition('-r');version=base+'-r'+str(int(revision or '1')+1)
stamp=datetime.datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y%m%d')
html=(guide/'index.html').read_text()
html=re.sub(r'Guide [0-9.]+(?:-r[0-9]+)?',f'Guide {version}',html,count=1)
html=re.sub(r'(Guide [^<]+ · )\d{8}',lambda m:m[1]+stamp,html,count=1)
m=re.search(r'(<script type="application/ld\+json">\s*)(.*?)(\s*</script>)',html,re.S)
if m:
 data=json.loads(m[2])
 for item in data.get('@graph',[]):
  if item.get('@type')=='TechArticle':item['version']=version
  if 'dateModified' in item:item['dateModified']=f'{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}'
 html=html[:m.start(2)]+json.dumps(data,ensure_ascii=False,indent=2)+html[m.end(2):]
(guide/'index.html').write_text(html);version_file.write_text(version+'\n')
current=scan();pending=(set(state['pending'])|changed|{'index.html'})&current.keys()
# Pending changes remain in subsequent diffs until the user confirms deployment.
payload={name:(guide/name).read_bytes() for name in pending}
manifest={'version':version,'viewerVersion':base,'date':stamp,'entrypoint':'index.html','files':[{'path':name,'bytes':sig[0]} for name,sig in sorted(current.items())]}
payload['deployment-manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
out=root.parent/f'ghettoscopes_{stamp}_v{version}_diff.zip'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
 for name in sorted({str(parent)+'/' for name in payload for parent in Path(name).parents if str(parent)!='.'}):
  info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=((stat.S_IFDIR|0o755)<<16)|16;z.writestr(info,b'')
 for name,data in sorted(payload.items()):
  info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFREG|0o644)<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
out.chmod(0o644)
with zipfile.ZipFile(out) as z:
 assert all(stat.S_IMODE(i.external_attr>>16)==(0o755 if i.is_dir() else 0o644) for i in z.infolist())
state.update(revision=version,files=current,pending=sorted(pending),archive=str(out))
state['snapshots'][version]=current;save(state)
log=root/'docs/GUIDE-DEPLOYMENTS.md'
with log.open('a') as f:f.write(f'\n{version}: {a.note}; diff prepared, awaiting deployment confirmation.\n')
print(f'{out} | {len(payload)} files | {out.stat().st_size} bytes | {time.perf_counter()-started:.3f}s')
