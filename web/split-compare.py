"""Independent split-vector / standard double-diamond reference and lossless capture validation."""
from visual_reference import *
OUT=Path(sys.argv[1] if len(sys.argv)>1 else 'docs/split-validation/visual')

def overlay_checks(actual,overlay,p,c,scope):
    h,w=actual.shape[:2];short=min(w,h);delta=abs(actual.astype(int)-overlay.astype(int)).max(2);refs=p['refs'];ok=True;points=[]
    if scope==7:
        diamonds=[v for v in refs if v['tag']=='polyline'];ok=len(diamonds)==2
        for i,sign in enumerate([1,-1]):
            vertices=np.array([[0,0],[1,sign],[0,2*sign],[-1,sign],[0,0]],float)
            expected=np.stack([(2.5-vertices[:,1])/5*1000,(1.25-vertices[:,0])/2.5*1000],axis=1)
            if len(diamonds)>i:ok=ok and np.allclose(np.array([list(map(float,v.split(','))) for v in diamonds[i]['points'].split()]),expected,atol=1e-9)
            for start,end in zip(vertices[:-1],vertices[1:]):
                for t in np.linspace(.1,.9,9):
                    x,y=start*(1-t)+end*t;points.append(((2.5-y)/5*w,(1.25-x)/2.5*h))
    else:
        calibrated=targets({**c,'vectorZoom':1});rects=[r for r in refs if r['tag']=='rect'];ok=len(rects)==len(calibrated)
        # Outline presence and raster coverage must survive every quality preset.
        circles=[r for r in refs if r['label']=='Vectorscope outline circle'];ok=ok and len(circles)==1
        for angle in np.linspace(0,2*np.pi,64,endpoint=False):points.append((w/2+.45*np.cos(angle)*short,h/2+.45*np.sin(angle)*short))
        for name,percent,u,v in calibrated:
            matches=[r for r in rects if r['label'].startswith(f'{name} {percent}%')]
            # Magnification changes the trace; calibrated guides stay anchored.
            x=w/2+u*short;y=h/2-v*short
            if len(matches)!=1:ok=False
            else:
                r=matches[0];ok=ok and abs(w/2+((float(r['x'])+float(r['width'])/2)/1000-.5)*short-x)<1e-8 and abs(h/2+((float(r['y'])+float(r['height'])/2)/1000-.5)*short-y)<1e-8
            if len(matches)==1:
                dx=float(matches[0]['width'])/1000*short/2;dy=float(matches[0]['height'])/1000*short/2
                points.extend([(x-dx,y),(x+dx,y),(x,y-dy),(x,y+dy)])
    hits=[]
    for x,y in points:
        if 0<=x<w and 0<=y<h:
            patch=delta[max(0,int(y)-2):min(h,int(y)+3),max(0,int(x)-2):min(w,int(x)+3)]
            hits.append(bool(patch.size and patch.max()>6))
    return bool(ok and (not hits or np.mean(hits)>.95))

results=[];negative={};sources=OUT/'sources';sources.mkdir(exist_ok=True)
for case in json.loads((OUT/'manifest.json').read_text()):
    c=case['plots'][0]['rendered']['config'];rgb,ycc=source(case['fixture'],c,True)
    # Archive high-depth decoded reference signal and verify bitwise TIFF round trip.
    path=sources/(case['name']+'.tiff');pixels=rgb.astype(np.float32);tifffile.imwrite(path,pixels,photometric='rgb',compression='deflate',metadata={'axes':'YXS','signal':'decoded encoded RGB reference','config':c})
    assert np.array_equal(tifffile.imread(path).view(np.uint32),pixels.view(np.uint32))
    # The reference analysis uses its independent decoded values (float64 for math).
    rgb=rgb[c['y0']:c['y1'],c['x0']:c['x1']];ycc=tuple(v[c['y0']:c['y1'],c['x0']:c['x1']] for v in ycc) if ycc else None
    planes,stats,twin=new_planes(rgb,c,ycc)
    for k,p in enumerate(case['plots']):
        scope=p['rendered']['scope'];actual=np.array(Image.open(OUT/f"{case['name']}-{scope}-actual.png").convert('RGB'));overlay=np.array(Image.open(OUT/f"{case['name']}-{scope}-overlay.png").convert('RGB'));h,w=actual.shape[:2]
        style=dict(trace_gain=case.get('tracegain',1),trace_brightness=case.get('brightness',100),smooth=bool(case.get('smooth',0)),vector_magnification=case.get('vectorzoom',1))
        expected,bg=reference(3 if k<3 else 4,planes[k],w,h,rgb.shape[0]*rgb.shape[1],**style);high,_=reference(3 if k<3 else 4,planes[k],w,h,rgb.shape[0]*rgb.shape[1],depth=16,**style)
        stem=f"{case['name']}-{scope}";tifffile.imwrite(OUT/(stem+'-expected.tiff'),high,photometric='rgb',compression='deflate');assert np.array_equal(tifffile.imread(OUT/(stem+'-expected.tiff')),high)
        r,diff=compare(actual,expected,bg,tolerance=2);results.append({'case':case['name'],'scope':scope,'check':'density pixels',**r});Image.fromarray(expected).save(OUT/(stem+'-expected.png'));Image.fromarray(np.uint8(np.clip(diff*20,0,255))).save(OUT/(stem+'-diff.png'))
        results.append({'case':case['name'],'scope':scope,'check':'calibrated overlay geometry and lossless pixels','pass':overlay_checks(actual,overlay,p,c,scope)})
        if k<3:ok=all(p['rendered']['splitStats'][k][key]==stats[k][key] for key in stats[k]);ok=ok and 'Y′' in p['band']
        else:ok=p['rendered']['twinStats']==twin
        results.append({'case':case['name'],'scope':scope,'check':'independent populations / excursions','pass':bool(ok)})
        if case['name']=='tonal-casts' and k==0:
            negative['blank_low_trace']=not compare(bg,expected,bg,tolerance=2)[0]['pass']
            wrong,_=reference(3,planes[2],w,h,rgb.shape[0]*rgb.shape[1]);negative['swapped_low_high']=not compare(wrong,expected,bg,tolerance=2)[0]['pass']
        if case['name']=='tonal-casts' and k==3:
            negative['vertically_flipped_diamonds']=not compare(actual[::-1],expected,bg,tolerance=2)[0]['pass']
            negative['missing_diamond_overlay']=not overlay_checks(actual,actual,p,c,scope)
    # Both tonal extremes have intentionally different colours; generic full vectors repeated three times must fail.
    if case['name']=='tonal-casts':
        p=case['plots'][0];actual=np.array(Image.open(OUT/f"{case['name']}-4-actual.png"));h,w=actual.shape[:2];wrong,_=reference(3,sum(planes[:3]),w,h,rgb.shape[0]*rgb.shape[1]);right,bg=reference(3,planes[0],w,h,rgb.shape[0]*rgb.shape[1]);negative['unsplit_vector_repeated']=not compare(wrong,right,bg,tolerance=2)[0]['pass']
result={'comparisons':results,'negative_controls':negative,'pass':all(v['pass'] for v in results) and all(negative.values())}
(OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));sys.exit(0 if result['pass'] else 1)
