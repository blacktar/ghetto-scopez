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
# Keep the deployable guide's visible and structured release information in sync.
guide=root/'web/public/guide/index.html'
if guide.exists():
 text=guide.read_text()
 guide_version_file=root/'web/GUIDE_VERSION'
 guide_version=guide_version_file.read_text().strip() if guide_version_file.exists() else version
 if guide_version.split('-r')[0]!=version:guide_version=version
 guide_version_file.write_text(guide_version+'\n')
 text=re.sub(r'Guide [0-9.]+(?:-r[0-9]+)? · ', '', text)
 text=re.sub(r'Viewer \d+\.\d+\.\d+( · GTap [^<]+? · )\d{8}',lambda m:f'Viewer {version}'+m[1]+stamp,text)
 pattern=r'(<script type="application/ld\+json">\s*)(.*?)(\s*</script>)'
 match=re.search(pattern,text,re.S)
 if match:
  metadata=json.loads(match[2])
  for item in metadata.get('@graph',[]):
   if item.get('@id','').endswith('#software'):
    item['softwareVersion']=version
    item['downloadUrl']=f'https://github.com/blacktar/ghetto-scopez/releases/download/v{version}/Ghetto-Scopez-{version}-mac.pkg'
   if item.get('@type')=='TechArticle':item['version']=guide_version
   if 'dateModified' in item:item['dateModified']=f'{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}'
  text=text[:match.start(2)]+json.dumps(metadata,ensure_ascii=False,indent=2)+text[match.end(2):]
 guide.write_text(text)
print(f'Ghetto Scopez v{version} ({stamp})')
