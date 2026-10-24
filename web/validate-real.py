"""Compare every server count bin to independent NumPy analysis of the real Resolve TIFF."""
from visual_reference import *
import urllib.request,struct,zlib
out=Path('docs/resolve-validation');snapshot=urllib.request.urlopen('http://127.0.0.1:8765/api/resolve/snapshot',timeout=15).read();magic,seq,gen,skip,ml,bl,crc,reserved=struct.unpack_from('<4s7I',snapshot)
assert magic==b'SCB3' and len(snapshot)==32+ml+bl and zlib.crc32(snapshot[32:])==crc
meta=json.loads(snapshot[32:32+ml]);(out/'actual-metadata.json').write_text(json.dumps(meta,indent=2));(out/'actual-scopes.scb').write_bytes(snapshot)
actual={};offset=32+ml
for p in meta['planes']:
    mode,count=struct.unpack_from('<II',snapshot,offset);offset+=8;n=p['width']*p['height'];a=np.zeros(n,dtype=np.uint32)
    if mode:
        values=np.frombuffer(snapshot,dtype='<u4',count=count*2,offset=offset).reshape(-1,2);a[values[:,0]]=values[:,1];offset+=count*8
    else:a[:]=np.frombuffer(snapshot,dtype='<u4',count=count,offset=offset);offset+=count*4
    actual[p['name']]=a.reshape(p['height'],p['width'])
assert offset==len(snapshot)
c=meta['config'];image=tifffile.imread(out/'resolve-current-frame.tif');assert image.dtype==np.uint16 and image.shape[:2]==(meta['source']['height'],meta['source']['width']);assert c['x0']==c['y0']==0 and c['x1']==image.shape[1] and c['y1']==image.shape[0]
expected={name:np.zeros(a.shape,dtype=np.uint64) for name,a in actual.items()}
for y in range(0,image.shape[0],64):
    rgb=(image[y:y+64].astype(np.float32)/np.float32(65535)).astype(np.float64)
    old=planes(rgb,c);new,stats,twin=new_planes(rgb,c)
    for name,a in zip(['wave','parade','hist','vector'],old):
        if name=='parade':a=a.reshape(-1,c['waveWidth'])
        expected[name]+=a.astype(np.uint64)
    for name,a in zip(['low','mid','high','twin'],new):expected[name]+=a
checks=[{'plane':name,'bins':a.size,'equal':bool(np.array_equal(a,expected[name])),'differentBins':int(np.count_nonzero(a!=expected[name])),'count':int(a.sum(dtype=np.uint64))} for name,a in actual.items()]
visual=[]
for scope,name,mode in [(4,'low',3),(5,'mid',3),(6,'high',3),(7,'twin',4)]:
    captured=np.array(Image.open(out/f'actual-visual/density-{scope}.png').convert('RGB'));h,w=captured.shape[:2]
    ref,bg=reference(mode,expected[name],w,h,meta['samples']);high,_=reference(mode,expected[name],w,h,meta['samples'],depth=16)
    tifffile.imwrite(out/f'actual-visual/reference-{scope}.tiff',high,photometric='rgb',compression='deflate')
    r,diff=compare(captured,ref,bg,tolerance=2);visual.append({'scope':scope,**r})
result={'source':'actual Resolve TIFF output','width':image.shape[1],'height':image.shape[0],'pixels':image.shape[0]*image.shape[1],'inputBits':16,'analysisBits':c['bits'],'sourceFrame':meta['source']['frameId'],'compute_ms':meta['compute_ms'],'checks':checks,'visual':visual,'pass':all(v['equal'] for v in checks) and all(v['pass'] for v in visual)};(out/'real-pixel-validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));sys.exit(0 if result['pass'] else 1)
