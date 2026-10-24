from visual_reference import *
import colorsys
OUT=Path(sys.argv[1]);rows=[]
for case in json.loads((OUT/'manifest.json').read_text()):
 c=case['plots'][0]['rendered']['config'];rgb=source(case['fixture'],c);tifffile.imwrite(OUT/(case['name']+'-source.tiff'),rgb.astype(np.float32),photometric='rgb',compression='deflate');r,g,b=np.moveaxis(rgb,2,0);hi=rgb.max(2);lo=rgb.min(2);d=hi-lo;sat=np.divide(d,hi,out=np.zeros_like(d),where=hi>0);hue=np.zeros_like(hi);nonzero=d>0
 for mask,numer,offset in [(nonzero&(hi==r),g-b,0),(nonzero&(hi!=r)&(hi==g),b-r,2),(nonzero&(hi!=r)&(hi!=g),r-g,4)]:hue[mask]=(numer[mask]/d[mask]+offset)%6/6
 l=r*.2126+g*.7152+b*.0722;sel=np.ones_like(l,dtype=bool)
 if c['isolation']!='off':
  dist=abs(hue*360-c['hueCenter'])%360;sel=(np.minimum(dist,360-dist)<=c['hueWidth'])&(sat>=c['satMin'])&(sat<=c['satMax'])&(l>=c['lumaMin'])&(l<=c['lumaMax'])
 a=np.zeros((256,256));valid=sel&(l>=c['min'])&(l<=c['max'])&(sat>=0)&(sat<=1);np.add.at(a,(np.floor((l[valid]-c['min'])/(c['max']-c['min'])*255+.5).astype(int),np.floor(sat[valid]*255+.5).astype(int)),1)
 hist=np.zeros(360);valid=sel&(sat>=.02)&(hi>1e-6)&(hi<=1)&(lo>=0);np.add.at(hist,np.minimum(359,np.floor(hue[valid]*360).astype(int)),1)
 for scope in [14,15]:
  actual=np.array(Image.open(OUT/f"{case['name']}-{scope}-actual.png").convert('RGB'));h,w=actual.shape[:2]
  if scope==14:
   values=np.uint8(np.rint(np.maximum(9,np.minimum(255,np.log1p(a[::-1])*40))));base=np.repeat(values[:,:,None],3,2);expected=np.array(Image.fromarray(base).resize((w,h),Image.Resampling.NEAREST))
  else:
   expected=np.full((h,w,3),9,dtype=np.uint8);maximum=max(1,hist.max())
   for x in range(w):
    count=hist[int(np.floor(x*360/w)):min(360,int(np.ceil((x+1)*360/w)))].max();height=int(np.floor(np.log1p(count)/np.log1p(maximum)*h+.5));expected[h-height:,x]=np.floor(np.array(colorsys.hsv_to_rgb((x+.5)/w,1,1))*255+.5).astype(np.uint8)
  stem=f"{case['name']}-{scope}";tifffile.imwrite(OUT/(stem+'-expected.tiff'),expected.astype(np.uint16)*257,photometric='rgb',compression='deflate');Image.fromarray(expected).save(OUT/(stem+'-expected.png'));result,diff=compare(actual,expected,np.full_like(expected,9),tolerance=3);rows.append({'case':case['name'],'scope':scope,**result});Image.fromarray(np.uint8(np.clip(diff*20,0,255))).save(OUT/(stem+'-diff.png'))
out={'comparisons':rows,'pass':all(r['pass'] for r in rows)};(OUT/'results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));sys.exit(0 if out['pass'] else 1)
