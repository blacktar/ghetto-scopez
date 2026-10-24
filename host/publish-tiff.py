"""Publish a real Resolve exported TIFF through the same checksummed float32 input as OFX."""
import argparse,json,struct,zlib,time,urllib.request
from pathlib import Path
import numpy as np
import tifffile
p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('--matrix',choices=['bt709','bt2020-ncl'],required=True);p.add_argument('--port',type=int,default=8765);args=p.parse_args()
a=tifffile.imread(args.path)
if a.ndim!=3 or a.shape[2] not in (3,4):raise SystemExit('Expected RGB/RGBA TIFF')
original_dtype=str(a.dtype)
if a.dtype==np.uint16:codebits=16;rgb=a[:,:,:3].astype(np.float32)/np.float32(65535)
elif a.dtype==np.float32:codebits=10;rgb=np.ascontiguousarray(a[:,:,:3])
else:raise SystemExit('Refusing a low-depth or unsupported TIFF: '+original_dtype)
context=json.loads(args.path.with_suffix('.json').read_text()) if args.path.with_suffix('.json').exists() else {}
meta={'producer':'resolve-still','instanceId':'current-frame-export','time':args.path.stat().st_mtime,'renderScale':{'x':1,'y':1},'orientation':'top-down','inputPrecision':original_dtype+' TIFF rendered output; normalized to float32','exportContext':context,'signal':{'model':'RGB','range':'full','matrix':args.matrix,'primaries':'bt709' if args.matrix=='bt709' else 'bt2020','transfer':'unknown','codeBits':codebits,'measurementStage':'Resolve ExportCurrentFrameAsStill output; explicitly declared encoded RGB'}}
m=json.dumps(meta).encode();raw=np.ascontiguousarray(rgb,dtype='<f4').tobytes();body=m+raw;packet=struct.pack('<4s7I',b'RIF1',int(time.time())&0xffffffff,a.shape[1],a.shape[0],len(m),len(raw),zlib.crc32(body),0)+body
req=urllib.request.Request('http://127.0.0.1:'+str(args.port)+'/api/resolve/input',data=packet,headers={'Content-Type':'application/octet-stream'})
with urllib.request.urlopen(req,timeout=30) as response:print(response.read().decode())
print(json.dumps({'width':a.shape[1],'height':a.shape[0],'TIFF_dtype':original_dtype,'float32_bytes':len(raw),'matrix':args.matrix,'source':'real Resolve exported output; not a live playback stream'},indent=2))
