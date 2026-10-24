"""Independent geometric expectations for lossless rendered cube captures."""
import math,itertools,json,sys
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(sys.argv[1]);checks=[]
for entry in json.loads((root/'captures.json').read_text()):
 a=np.asarray(Image.open(root/f"{entry['backend']}-{entry['resolution']}.png").convert('RGB'));h,w=a.shape[:2]
 for rgb in itertools.product([0,1],repeat=3):
  if rgb in [(0,0,0),(1,1,1)]:continue # neutral outline deliberately overlays neutral corners
  x,y,z=[v-.5 for v in rgb];yaw=-.65;pitch=.45
  xx=math.cos(yaw)*x+math.sin(yaw)*z;zz=-math.sin(yaw)*x+math.cos(yaw)*z;yy=math.cos(pitch)*y-math.sin(pitch)*zz
  px=round(w/2+xx*h/2);py=round(h/2-yy*h/2)
  patch=a[max(0,py-4):py+5,max(0,px-4):px+5].astype(float).reshape(-1,3)
  # A chromatic pixel must agree with the expected corner channels, not just a grey edge.
  on=np.array(rgb,dtype=bool);ok=bool(np.any((patch[:,on].min(axis=1)>100)&(patch[:,~on].max(axis=1)<90)))
  assert ok,(entry['backend'],entry['resolution'],rgb,px,py)
  checks.append([entry['backend'],entry['resolution'],rgb,'PASS'])
(root/'visual-results.json').write_text(json.dumps(checks,indent=2));print(f'{len(checks)} independently projected colour-corner checks PASS')
