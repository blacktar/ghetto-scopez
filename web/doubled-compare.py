"""Independent display-only DoubleD rotation / colour-guide regression."""
from visual_reference import *
out=Path(sys.argv[1]);entries=json.loads((out/'doubled-manifest.json').read_text());results=[]
for entry in entries:
 c=entry['rendered']['config'];rgb,ycc=source('tonal-casts',c,True);planes,stats,twin=new_planes(rgb,c,ycc)
 actual=np.array(Image.open(out/(entry['name']+'-lossless.png')).convert('RGB'));h,w=actual.shape[:2]
 horizontal=entry['rendered']['twinHorizontal'];colour=entry['rendered']['twinColour']
 expected,bg=reference(4,planes[3],w,h,rgb.shape[0]*rgb.shape[1],twin_horizontal=horizontal,twin_colour=colour)
 result,diff=compare(actual,expected,bg,tolerance=2)
 Image.fromarray(expected).save(out/(entry['name']+'-expected.png'))
 assert len(entry['guides'])==4
 assert sorted(g['stroke'] for g in entry['guides'])==sorted(['#44e65c','#44e65c','#407aff','#ff3830'])
 assert all(g['stroke-width']=='2' for g in entry['guides'])
 # Transform each inset guide back into the original vertical view. Its colour
 # must remain attached to the same original upper/lower left/right edge.
 for g in entry['guides']:
  x=(float(g['x1'])+float(g['x2']))/2000;y=(float(g['y1'])+float(g['y2']))/2000
  if horizontal:x,y=1-y,x
  assert g['stroke']==('#44e65c' if x<.5 else '#407aff' if y<.5 else '#ff3830')
 assert len(set(t['stroke'] for t in entry['targets']))==6
 results.append({'name':entry['name'],'guides_and_targets':True,**result})
assert entries[0]['targets']==entries[1]['targets']==entries[2]['targets']==entries[3]['targets']
(out/'doubled-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2));sys.exit(0 if all(r['pass'] for r in results) else 1)
