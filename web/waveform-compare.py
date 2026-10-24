from visual_reference import *
OUT=Path(sys.argv[1]);results=[]
for case in json.loads((OUT/'manifest.json').read_text()):
 c=case['plots'][0]['rendered']['config'];rgb=source(case['fixture'],c).astype(np.float32);tifffile.imwrite(OUT/(case['name']+'-source.tiff'),rgb,photometric='rgb',compression='deflate');planes_all=planes(rgb,c)
 for p in case['plots']:
  scope=p['rendered']['scope'];actual=np.array(Image.open(OUT/f"{case['name']}-{scope}-actual.png").convert('RGB'));h,w=actual.shape[:2];expected,bg=reference(scope,planes_all[scope],w,h,rgb.shape[0]*rgb.shape[1]);high,_=reference(scope,planes_all[scope],w,h,rgb.shape[0]*rgb.shape[1],depth=16)
  if scope==0 and case['wavecolour']!='mono':
   xx,yy=np.meshgrid((np.arange(w)+.5)/w,1-(np.arange(h)+.5)/h);a=planes_all[0];ink=np.ones((h,w,3))
   if case['wavecolour']=='false':
    hue=(1-np.clip(c['min']+yy*(c['max']-c['min']),0,1))*4;x=1-abs(hue%2-1)
    ink=np.stack([np.where(hue<1,1,np.where(hue<2,x,0)),np.where(hue<1,x,np.where(hue<3,1,x)),np.where(hue<2,0,np.where(hue<3,x,1))],axis=2)
   else:
    kr,kg,kb=(.2126,.7152,.0722);r,g,b=np.moveaxis(rgb,2,0);l=(((r*np.float32(kr)).astype(np.float32)+(g*np.float32(kg)).astype(np.float32)).astype(np.float32)+(b*np.float32(kb)).astype(np.float32)).astype(np.float32);valid=np.isfinite(rgb).all(2)&np.isfinite(l)&(l>=c['min'])&(l<=c['max']);ix=np.broadcast_to(np.arange(rgb.shape[1])*512//rgb.shape[1],l.shape);iy=np.floor(((l-np.float32(c['min']))/np.float32(c['max']-c['min'])*(c['levels']-1)).astype(np.float32)+np.float32(.5)).astype(int)
    channels=[]
    for channel in range(3):
     sums=np.zeros_like(a);values=np.floor((np.clip(rgb[:,:,channel],0,1)*np.float32(255)).astype(np.float32)+np.float32(.5));np.add.at(sums,(iy[valid],ix[valid]),values[valid]);channels.append(density(sums,xx,yy,1/w,1/h))
    sums=np.stack(channels,2);peak=sums.max(2,keepdims=True);ink=np.divide(sums,peak,out=np.ones_like(sums),where=peak>0)
   strength=np.minimum(1,np.log1p(density(a,xx,yy,1/w,1/h))*.25)*.82;image=.035+strength[:,:,None]*ink;expected=np.uint8(np.rint(np.clip(image,0,1)*255));high=np.uint16(np.rint(np.clip(image,0,1)*65535))
  stem=f"{case['name']}-{scope}";tifffile.imwrite(OUT/(stem+'-expected.tiff'),high,photometric='rgb',compression='deflate');Image.fromarray(expected).save(OUT/(stem+'-expected.png'));result,diff=compare(actual,expected,bg,tolerance=2);results.append({'case':case['name'],'scope':scope,**result});Image.fromarray(np.uint8(np.clip(diff*20,0,255))).save(OUT/(stem+'-diff.png'))
out={'comparisons':results,'pass':all(r['pass'] for r in results)};(OUT/'results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));sys.exit(0 if out['pass'] else 1)
