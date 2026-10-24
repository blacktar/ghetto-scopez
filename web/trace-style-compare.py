"""Regression guard: density gain must not become output brightness."""
from visual_reference import *
out=Path(sys.argv[1]);case=next(c for c in json.loads((out/'manifest.json').read_text()) if c['name']=='gain4');c=case['plots'][0]['rendered']['config'];rgb=source('sine',c);data,_,_=new_planes(rgb,c);results=[]
for k,p in enumerate(case['plots']):
 scope=p['rendered']['scope'];actual=np.array(Image.open(out/f'gain4-{scope}-actual.png').convert('RGB'));h,w=actual.shape[:2]
 expected,bg=reference(3 if k<3 else 4,data[k],w,h,rgb.shape[0]*rgb.shape[1],trace_gain=4)
 wrong,_=reference(3 if k<3 else 4,data[k],w,h,rgb.shape[0]*rgb.shape[1],trace_brightness=400)
 results.append({'scope':scope,'gain_is_not_brightness':not compare(wrong,expected,bg,tolerance=2)[0]['pass']})
(out/'gain-distinction.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2));assert all(r['gain_is_not_brightness'] for r in results)
