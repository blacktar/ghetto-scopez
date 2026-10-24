"""Export the current Resolve output frame; never moves the playhead or changes grades."""
import sys,json
from pathlib import Path
sys.path.insert(0,'/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules')
import DaVinciResolveScript as d
r=d.scriptapp('Resolve')
if not r:raise SystemExit('Resolve scripting unavailable. Enable local scripting in Resolve if necessary.')
p=r.GetProjectManager().GetCurrentProject();t=p.GetCurrentTimeline() if p else None
if not t:raise SystemExit('Open a Resolve project and timeline first.')
target=Path(sys.argv[1]).resolve();target.parent.mkdir(parents=True,exist_ok=True)
if not p.ExportCurrentFrameAsStill(str(target)):raise SystemExit('Resolve could not export the current frame')
metadata={'resolveVersion':r.GetVersionString(),'project':p.GetName(),'timeline':t.GetName(),'timecode':t.GetCurrentTimecode(),'projectOutput':p.GetSetting('colorSpaceOutput'),'colorScience':p.GetSetting('colorScienceMode'),'timelineWidth':p.GetSetting('timelineResolutionWidth'),'timelineHeight':p.GetSetting('timelineResolutionHeight')}
target.with_suffix('.json').write_text(json.dumps(metadata,indent=2));print(json.dumps(metadata,indent=2))
