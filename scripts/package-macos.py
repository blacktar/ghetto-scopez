#!/usr/bin/env python3
"""Build a self-contained universal Developer ID signed macOS installer.
Node archives and official SHASUMS256.txt must be in --downloads (default /tmp).
No installation or publication is performed. Notarize with scripts/notarize-macos.sh.
"""
import argparse, hashlib, json, os, plistlib, shutil, subprocess, tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--downloads',type=Path,default=Path('/tmp'))
p.add_argument('--application-identity',default='Developer ID Application: Vidar Andersen (CMRVMTA2G5)')
p.add_argument('--installer-identity',default='Developer ID Installer: Vidar Andersen (CMRVMTA2G5)')
p.add_argument('--resume',action='store_true',help='Reuse staged payload after a signing-only failure')
a=p.parse_args()
def run(*cmd): subprocess.run([str(c) for c in cmd],check=True,cwd=root)
version=(root/'web/VERSION').read_text().strip()
# Sign outside file-provider folders, which may regenerate FinderInfo on bundles.
work=Path('/private/tmp/ghetto-scopez-macos-installer')
payload=work/'payload';app=payload/'Applications/Ghetto Scopez.app'
contents=app/'Contents';resources=contents/'Resources';host=resources/'host'
plugin=payload/'Library/OFX/Plugins'
if not a.resume:
 if work.exists(): shutil.rmtree(work)
 payload=work/'payload';app=payload/'Applications/Ghetto Scopez.app'
 contents=app/'Contents';resources=contents/'Resources';host=resources/'host'
 for d in [contents/'MacOS',resources/'runtime',host/'web',host/'build',work/'scripts']:d.mkdir(parents=True,exist_ok=True)
 # Verify executable runtime archives against the official Node distribution manifest.
 node_version='24.22.1'
 manifest=(a.downloads/'ghetto-node-shasums.txt').read_text()
 for arch in ['arm64','x64']:
  archive=a.downloads/f'ghetto-node-{arch}.tar.gz'
  name=f'node-v{node_version}-darwin-{arch}.tar.gz'
  expected=next(line.split()[0] for line in manifest.splitlines() if line.split()[-1]==name)
  if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise SystemExit('Node checksum mismatch: '+arch)
  with tarfile.open(archive) as tar:
   for relative in ['bin/node','LICENSE']:
    data=tar.extractfile(f'node-v{node_version}-darwin-{arch}/{relative}').read()
    (work/f'{arch}-{Path(relative).name}').write_bytes(data)
 run('lipo','-create',work/'arm64-node',work/'x64-node','-output',resources/'runtime/node')
 (resources/'runtime/node').chmod(0o755)
 shutil.copy2(work/'arm64-LICENSE',resources/'runtime/LICENSE')
 # Ship production host modules, browser assets and pinned dependencies, not tests/tooling.
 for f in (root/'web').glob('*.mjs'):
  if not f.name.endswith('.test.mjs'):shutil.copy2(f,host/'web'/f.name)
 for f in ['package.json','VERSION']:shutil.copy2(root/'web'/f,host/'web'/f)
 shutil.copytree(root/'web/public',host/'web/public')
 for name in ['ws','nosleep.js','three']:
  source=root/'web/node_modules'/name
  if json.loads((source/'package.json').read_text())['version']!=json.loads((root/'web/package.json').read_text())['dependencies'][name]:raise SystemExit('Dependency mismatch: '+name)
  target=host/'web/node_modules'/name;target.mkdir(parents=True)
  for relative in (['package.json','LICENSE','index.js','wrapper.mjs','lib'] if name=='ws' else ['package.json','LICENSE','dist/NoSleep.min.js'] if name=='nosleep.js' else ['package.json','LICENSE','build/three.core.js','build/three.module.js','build/three.webgpu.js','build/three.tsl.js']):
   src=source/relative
   if not src.exists():continue
   dst=target/relative;dst.parent.mkdir(parents=True,exist_ok=True)
   if src.is_dir():shutil.copytree(src,dst)
   else:shutil.copy2(src,dst)
 shutil.copy2(root/'release/scope-analysis.node',host/'build/scope-analysis.node')
 plugin=payload/'Library/OFX/Plugins';plugin.mkdir(parents=True)
 run('ditto','-x','-k',root/'release/GTap-v1.2.26.ofx.bundle.zip',plugin)
 for name in ['LICENSE','LICENSE-NOTICE.txt','THIRD-PARTY-NOTICES.txt']:shutil.copy2(root/name,resources/name)
 info={'CFBundleIdentifier':'com.vidarandersen.ghettoscopez','CFBundleName':'Ghetto Scopez','CFBundleDisplayName':'Ghetto Scopez','CFBundleExecutable':'GhettoScopez','CFBundleIconFile':'AppIcon.icns','CFBundlePackageType':'APPL','CFBundleShortVersionString':version,'CFBundleVersion':version,'LSMinimumSystemVersion':'27.0','LSUIElement':True,'NSHighResolutionCapable':True,'NSHumanReadableCopyright':'© 2026 Vidar Andersen'}
 shutil.copy2(root/'installer/AppIcon.icns',resources/'AppIcon.icns')
 (contents/'Info.plist').write_bytes(plistlib.dumps(info))
 for arch in ['arm64','x86_64']:
  run('xcrun','swiftc','-O','-target',arch+'-apple-macos27.0','-module-cache-path',work/'swift-cache','-framework','AppKit',root/'installer/HostApp.swift','-o',work/('launcher-'+arch))
 run('lipo','-create',work/'launcher-arm64',work/'launcher-x86_64','-output',contents/'MacOS/GhettoScopez')
 agent=payload/'Library/LaunchAgents/com.vidarandersen.ghettoscopez.plist';agent.parent.mkdir(parents=True,exist_ok=True)
 agent.write_bytes(plistlib.dumps({'Label':'com.vidarandersen.ghettoscopez','ProgramArguments':['/Applications/Ghetto Scopez.app/Contents/MacOS/GhettoScopez'],'RunAtLoad':True,'LimitLoadToSessionType':'Aqua','ProcessType':'Interactive'}))
 (work/'scripts/preinstall').write_text('''#!/bin/bash
 set -euo pipefail
 if /usr/bin/pgrep -x Resolve >/dev/null; then
  echo 'Quit DaVinci Resolve before installing Ghetto Scopez.' >&2
  exit 1
 fi
 if [[ -e /Library/OFX/Plugins/SignalLabTap.ofx.bundle ]]; then
  identity=$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' /Library/OFX/Plugins/SignalLabTap.ofx.bundle/Contents/Info.plist)
  [[ "$identity" == local.signallab.ResolveTap ]] || exit 1
 fi
 uid=$(/usr/bin/stat -f %u /dev/console)
 if [[ "$uid" -ge 501 ]]; then
  /bin/launchctl bootout "gui/$uid/com.vidarandersen.ghettoscopez" 2>/dev/null || true
 fi
 ''')
 (work/'scripts/postinstall').write_text('''#!/bin/bash
 set -euo pipefail
 uid=$(/usr/bin/stat -f %u /dev/console)
 if [[ "$uid" -ge 501 ]]; then
  username=$(/usr/bin/id -nu "$uid")
  /bin/launchctl asuser "$uid" /usr/bin/sudo -H -u "$username" '/Applications/Ghetto Scopez.app/Contents/MacOS/GhettoScopez' --create-desktop-alias || echo 'Desktop shortcut could not be created; open Ghetto Scopez from Applications.'
  /bin/launchctl bootstrap "gui/$uid" /Library/LaunchAgents/com.vidarandersen.ghettoscopez.plist || {
   echo 'Open Ghetto Scopez from Applications to start the server.'
  }
 fi
 exit 0
 ''')
for f in payload.rglob('*'):
 if f.is_dir():f.chmod(0o755)
 elif f.name in ['node','GhettoScopez','SignalLabTap.ofx']:f.chmod(0o755)
 else:f.chmod(0o644)
for f in (work/'scripts').iterdir():f.chmod(0o755)
# Strip Finder metadata from staging only; preserve quarantine/security attributes.
for name in ['com.apple.FinderInfo','com.apple.ResourceFork']:
 subprocess.run(['xattr','-dr',name,str(payload)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def sign(path,entitlements=None):
 for name in ['com.apple.FinderInfo','com.apple.ResourceFork']:
  subprocess.run(['/usr/bin/xattr','-d',name,str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 cmd=['codesign','--force','--timestamp','--options','runtime','--sign',a.application_identity]
 if entitlements:cmd+=['--entitlements',entitlements]
 run(*cmd,path)
sign(resources/'runtime/node',root/'installer/node-entitlements.plist')
sign(host/'build/scope-analysis.node')
sign(plugin/'SignalLabTap.ofx.bundle')
sign(app)
run('codesign','--verify','--deep','--strict',app)
run('codesign','--verify','--strict',plugin/'SignalLabTap.ofx.bundle')
component=work/'component.pkg'
components=work/'components.plist'
run('pkgbuild','--analyze','--root',payload,components)
entries=plistlib.loads(components.read_bytes())
for entry in entries:
 entry['BundleIsRelocatable']=False
components.write_bytes(plistlib.dumps(entries))
run('pkgbuild','--root',payload,'--component-plist',components,'--scripts',work/'scripts','--identifier','com.vidarandersen.ghettoscopez.installer','--version',version+'.1','--install-location','/','--ownership','recommended',component)
# Disable bundle relocation: app and launch agent must agree on a fixed path.
# The Distribution also enforces the same macOS minimum as the shipped binaries.
dist=work/'Distribution.xml'
dist.write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
<title>Ghetto Scopez</title>
<options customize="never" require-scripts="false" hostArchitectures="arm64,x86_64"/>
<domains enable_localSystem="true" enable_currentUserHome="false" enable_anywhere="false"/>
<allowed-os-versions><os-version min="27.0"/></allowed-os-versions>
<welcome file="welcome.html"/>
<license file="LICENSE.txt"/>
<conclusion file="conclusion.html"/>
<choices-outline><line choice="default"><line choice="com.vidarandersen.ghettoscopez.installer"/></line></choices-outline>
<choice id="default"/>
<choice id="com.vidarandersen.ghettoscopez.installer" visible="false"><pkg-ref id="com.vidarandersen.ghettoscopez.installer"/></choice>
<pkg-ref id="com.vidarandersen.ghettoscopez.installer" version="{version}.1" onConclusion="none">component.pkg</pkg-ref>
</installer-gui-script>''')
ui=work/'ui';ui.mkdir(exist_ok=True)
shutil.copy2(root/'LICENSE',ui/'LICENSE.txt')
(ui/'welcome.html').write_text('<html><body><h1>Ghetto Scopez</h1><p>Install GTap for DaVinci Resolve and the Ghetto Scopez menu-bar app, including its server and runtime.</p><p><b>Quit DaVinci Resolve before continuing.</b> macOS 27 or later required.</p><p>The server starts after installation and at login. It serves scopes on your local network on port 8765.</p></body></html>')
(ui/'conclusion.html').write_text('<html><body><h1>Ghetto Scopez is installed</h1><p>Double-click the desktop Ghetto Scopez icon to open the app and server controls. Use <b>GS</b> in the menu bar to open the viewer or guide, and start or stop the server. Open Ghetto Scopez in Applications if the menu is absent.</p><p>Quit an older Terminal-based host before starting this server. Allow local network access if macOS asks. Open DaVinci Resolve and add GTap.</p></body></html>')
out=root.parent/f'Ghetto-Scopez-{version}-mac.pkg'
run('productbuild','--distribution',dist,'--package-path',work,'--resources',ui,'--sign',a.installer_identity,'--timestamp',out)
out.chmod(0o644)
run('pkgutil','--check-signature',out)
print(out)
