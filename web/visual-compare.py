"""Independent legacy visual regression suite; shared reference math lives in visual_reference.py."""
from visual_reference import *

# Full float32 reference sources: never quantize to display bit depth.
fixture_dir=OUT/'sources';fixture_dir.mkdir(exist_ok=True)
for kind in ('ramp','bars','bars75','sine','ramp10','ramp12','excursions','impulse'):
    pixels=source(kind).astype(np.float32);path=fixture_dir/(kind+'.tiff')
    tifffile.imwrite(path,pixels,photometric='rgb',compression='deflate',metadata={'axes':'YXS','signal':'RGB full range, nonlinear code values; no transfer conversion'})
    restored=tifffile.imread(path)
    assert restored.dtype==np.float32 and restored.shape==pixels.shape
    assert np.array_equal(restored.view(np.uint32),pixels.view(np.uint32)), 'TIFF changed float32 bits'
def lossless_page(case,overlay=False):
    page=np.zeros((case['height'],case['width'],3),dtype=np.uint8)
    for i,p in enumerate(case['plots']):
        x,y,w,h=[int(round(p[k])) for k in ('x','y','width','height')]
        pixels=np.array(Image.open(OUT/(case['name']+f'-{i}-'+('overlay' if overlay else 'lossless')+'.png')).convert('RGB'))
        assert pixels.shape==(h,w,3),'Capture dimensions differ from display pixels'
        page[y:y+h,x:x+w]=pixels
    return page

reports=[];tiles=[]
for case in json.loads((OUT/'manifest.json').read_text()):
    c=case['plots'][0]['rendered']['config'];rgb,ycc=source(case['fixture'],c,True);rgb=rgb[c.get('y0',0):c.get('y1'),c.get('x0',0):c.get('x1')];ycc=tuple(v[c.get('y0',0):c.get('y1'),c.get('x0',0):c.get('x1')] for v in ycc) if ycc else None;data=planes(rgb,c,ycc);image=Image.new('RGB',(case['width'],case['height']))
    for i,p in enumerate(case['plots']):
        x,y,w,h=[int(round(p[k])) for k in ('x','y','width','height')]
        actual=np.array(image.crop((x,y,x+w,y+h)));expected,bg=reference(i,data[i],w,h,rgb.shape[0]*rgb.shape[1]);lossless=OUT/(case['name']+f'-{i}-lossless.png');is_lossless=lossless.exists();
        assert is_lossless,'Lossless canvas capture required; JPEG is not a validation input'
        if is_lossless:actual=np.array(Image.open(lossless).convert('RGB'))
        r,diff=compare(actual,expected,bg,tolerance=2 if is_lossless else 12)
        stem=f"{case['name']}-{i}";high,_=reference(i,data[i],w,h,rgb.shape[0]*rgb.shape[1],depth=16);tifffile.imwrite(OUT/(stem+'-expected.tiff'),high,photometric='rgb',compression='deflate',metadata={'axes':'YXS','reference':'independent renderer before 8-bit display quantization'});assert np.array_equal(tifffile.imread(OUT/(stem+'-expected.tiff')),high);Image.fromarray(expected).save(OUT/(stem+'-expected.png'));Image.fromarray(actual).save(OUT/(stem+'-actual.png'));Image.fromarray(np.uint8(np.clip(diff*5,0,255))).save(OUT/(stem+'-diff.png'))
        reports.append({'case':case['name'],'scope':['waveform','parade','histogram','vector'][i],**r})
    # Visible axis values are checked independently of image font rasterization.
    def tick(v):
        if case.get('axisunit')=='ire':return f'{v*100:.1f}'
        if case.get('axisunit')=='code':
            maximum=2**c.get('codeBits',10)-1;factor=2**(c.get('codeBits',10)-8);lo,hi=(16*factor,235*factor) if c.get('range')=='video' else (0,maximum)
            return f'{lo+v*(hi-lo):.1f}'
        return f'{v:.4f}'
    expected_ticks=[tick(c['max']-j/4*(c['max']-c['min'])) for j in range(5)]
    hist_ticks=[f'{int(np.floor(np.expm1((1-j/4)*np.log1p(rgb.shape[0]*rgb.shape[1]))+.5)):,}' for j in range(5)];vector_ticks=[format(Decimal(str((.5-j/4)/c['vectorZoom'])).quantize(Decimal('.001'),rounding=ROUND_HALF_UP),'f') for j in range(5)]
    axes_ok=all(case['axes'][i].split()==expected_ticks for i in (0,1)) and case['axes'][2].split()==hist_ticks and case['axes'][3].split()==vector_ticks
    reports.append({'case':case['name'],'scope':'level axes','pass':axes_ok})
    if 'xaxes' in case:
        first,last=c['x0'],c['x1']-1;expected_axis=f'{first} original source x {last}';ok=' '.join(case['xaxes'][0].split())==expected_axis and f"ROI x [{c['x0']},{c['x1']}), y [{c['y0']},{c['y1']})" in case['roiText'];reports.append({'case':case['name'],'scope':'original source ROI coordinates','pass':ok})
    if case.get('targets'):
        expected_targets=targets(c);actual=[r for r in case['references'] if r['tag']=='rect'];ok=len(actual)==len(expected_targets)
        for target in expected_targets:
            matches=[r for r in actual if r['label'].startswith(target[0]+' ') and int(r['percent'])==target[1]]
            ok=ok and len(matches)==1
            if matches:
                r=matches[0];cx=float(r['x'])+float(r['width'])/2;cy=float(r['y'])+float(r['height'])/2
                ok=ok and abs(cx-(.5+target[2]*c['vectorZoom'])*1000)<1e-7 and abs(cy-(.5-target[3]*c['vectorZoom'])*1000)<1e-7
        reports.append({'case':case['name'],'scope':'calibrated target geometry','pass':bool(ok)})
        overlay=lossless_page(case,True);base=lossless_page(case)
        overlay_ok=check_overlay(base,overlay,case,c)
        reports.append({'case':case['name'],'scope':'calibrated overlay pixels','pass':overlay_ok})
        p=case['plots'][3];x,y,w,h=[int(round(p[k])) for k in ('x','y','width','height')];reference_pixels,_=reference(3,data[3],w,h,rgb.shape[0]*rgb.shape[1]);ref=draw_references(reference_pixels,3,c,case)
        Image.fromarray(ref).save(OUT/(case['name']+'-targets-expected.png'));Image.fromarray(overlay[y:y+h,x:x+w]).save(OUT/(case['name']+'-targets-actual.png'))
# Negative controls ensure the comparator actually rejects rendering faults.
a,bg=reference(0,planes(source('ramp12'),{'bits':12,'min':0,'max':1,'vectorZoom':1})[0],423,215,262144)
controls={}
for name,wrong in {'blank':bg,'vertical_flip':a[::-1],'shifted_10px':np.roll(a,10,axis=1),'wrong_colour':np.stack([a[:,:,0],np.zeros_like(a[:,:,0]),np.zeros_like(a[:,:,0])],axis=2)}.items():controls[name]=not compare(wrong,a,bg)[0]['pass']
impulse_case=next(c for c in json.loads((OUT/'manifest.json').read_text()) if c['name']=='impulse')
p=impulse_case['plots'][0];w,h=int(p['width']),int(p['height'])
imp,bg=reference(0,planes(source('impulse'),{'bits':12,'min':0,'max':1,'vectorZoom':1})[0],w,h,16384)
missing=imp.copy()
px=int(.5*w);py=int((1-.2126)*h);missing[max(0,py-5):py+6,px-5:px+6]=bg[max(0,py-5):py+6,px-5:px+6]
controls['missing_isolated_impulse']=not compare(missing,imp,bg)[0]['pass']
overlay_case=next(v for v in json.loads((OUT/'manifest.json').read_text()) if v.get('targets')) if any(v.get('targets') for v in json.loads((OUT/'manifest.json').read_text())) else None
if overlay_case:
    base=lossless_page(overlay_case);overlay=lossless_page(overlay_case,True);conf=overlay_case['plots'][0]['rendered']['config']
    controls['missing_calibration_overlay']=not check_overlay(base,base,overlay_case,conf)
    controls['displaced_calibration_overlay']=not check_overlay(base,np.roll(overlay,15,axis=1),overlay_case,conf)
if any(v['name']=='roi-native-512' for v in json.loads((OUT/'manifest.json').read_text())):
    full=source('ramp12');conf={'bits':12,'min':0,'max':1,'vectorZoom':1};full_image,_=reference(0,planes(full,conf)[0],423,215,262144)
    wrong=np.array(Image.fromarray(full_image).crop((106,0,159,215)).resize((423,215),Image.Resampling.NEAREST));correct,bg=reference(0,planes(full[17:18,1024:1536],conf)[0],423,215,512)
    controls['bitmap_zoom_instead_of_source_reanalysis']=not compare(wrong,correct,bg,tolerance=2)[0]['pass']
result={'comparisons':reports,'negative_controls':controls,'pass':all(r['pass'] for r in reports) and all(controls.values())}
(OUT/'results.json').write_text(json.dumps(result,indent=2))
for r in reports:print(('PASS' if r['pass'] else 'FAIL'),r)
print('Negative controls:',controls)
sys.exit(0 if result['pass'] else 1)
