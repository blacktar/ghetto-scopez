"""Independent NumPy/Pillow reference renderer and screenshot comparator.
No imports from production scope analysis or shader code. Exit nonzero on any failure.
"""
import json,sys
from collections import deque
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
import numpy as np
import tifffile
from PIL import Image,ImageDraw,JpegImagePlugin
from io import BytesIO
OUT=Path(sys.argv[1] if len(sys.argv)>1 else '../docs/visual-validation')


def source(kind,c=None,with_ycc=False):
    n={'ramp10':1024,'ramp12':4096}.get(kind,256)
    x=np.arange(n); y=np.arange(64)[:,None]
    if kind in ('bars','bars75'):
        colors=np.array([[1,1,1],[1,1,0],[0,1,1],[0,1,0],[1,0,1],[1,0,0],[0,0,1],[0,0,0]])
        rgb=np.broadcast_to(colors[x*8//n]*(.75 if kind=='bars75' else 1),(64,n,3))
    elif kind=='tonal-casts':
        zone=np.minimum(2,x*3//n);l=np.array([.125,.5,.875])[zone];u=np.array([.04,0,-.025])[zone];v=np.array([-.02,0,.035])[zone];kr,kg,kb=(.2627,.6780,.0593) if c and c.get('matrix')=='bt2020-ncl' else (.2126,.7152,.0722)
        r=l+2*(1-kr)*v;b=l+2*(1-kb)*u;rgb=np.broadcast_to(np.stack([r,(l-kr*r-kb*b)/kg,b],axis=1),(64,n,3))
    elif kind=='sine':
        rgb=.5+.49*np.sin(x[None,:,None]/(n-1)*2*np.pi+y[:,:,None]*.01+np.array([0,2*np.pi/3,4*np.pi/3]))
    elif kind=='excursions':
        vals=np.array([-.1,0,1/4095,64/1023,940/1023,1,1.1,np.nan,np.inf,-np.inf])[x%10]
        rgb=np.broadcast_to(vals[None,:,None],(64,n,3))
    elif kind=='impulse':
        rgb=np.zeros((64,n,3));rgb[32,n//2,0]=1
    else: rgb=np.broadcast_to((x/(n-1))[None,:,None],(64,n,3))
    ycc=None
    if c and c.get('range')=='video':
        bits=c.get('codeBits',10);maximum=2**bits-1;factor=2**(bits-8);black,white,center,span=16*factor,235*factor,128*factor,224*factor
        kr,kg,kb=(.2627,.6780,.0593) if c.get('matrix')=='bt2020-ncl' else (.2126,.7152,.0722)
        def level(v):
            result=(v*maximum-black)/(white-black)
            return np.where(v==float(np.float32(black/maximum)),0,np.where(v==float(np.float32(white/maximum)),1,result))
        if c.get('model')=='YCbCr':
            with np.errstate(invalid='ignore'):
                yy=rgb@np.array([kr,kg,kb]);cb=(rgb[:,:,2]-yy)/(2*(1-kb));cr=(rgb[:,:,0]-yy)/(2*(1-kr))
                raw=np.stack([(black+yy*(white-black))/maximum,(center+cb*span)/maximum,(center+cr*span)/maximum],axis=2).astype(np.float32).astype(float)
            def chroma_decode(v):
                result=(v*maximum-center)/span
                for code,value in [(center,0),(center+span/2,.5),(center-span/2,-.5)]:result=np.where(v==float(np.float32(code/maximum)),value,result)
                return result
            yy,cb,cr=level(raw[:,:,0]),chroma_decode(raw[:,:,1]),chroma_decode(raw[:,:,2]);r=yy+2*(1-kr)*cr;b=yy+2*(1-kb)*cb;g=(yy-kr*r-kb*b)/kg;rgb=np.stack([r,g,b],axis=2);ycc=(yy,cb,cr)
        else:rgb=level(((black+rgb*(white-black))/maximum).astype(np.float32).astype(float))
    else:rgb=rgb.astype(np.float32).astype(np.float64)
    return (rgb,ycc) if with_ycc else rgb

def planes(rgb,c,ycc=None):
    h,w,_=rgb.shape;levels=2**c['bits'];lo,hi=c['min'],c['max'];kr,kg,kb=(.2627,.6780,.0593) if c.get('matrix')=='bt2020-ncl' else (.2126,.7152,.0722);luma=ycc[0] if ycc else rgb@np.array([kr,kg,kb])
    wave=np.zeros((levels,512));parade=np.zeros((3,levels,512));hist=np.zeros((3,levels));vec=np.zeros((512,512));xx=np.broadcast_to(np.arange(w)*512//w,(h,w))
    for channel,v in enumerate([*np.moveaxis(rgb,2,0),luma]):
        valid=np.isfinite(v)&(v>=lo)&(v<=hi)
        code=np.floor((v[valid]-lo)/(hi-lo)*(levels-1)+.5).astype(int)
        np.add.at(wave if channel==3 else parade[channel],(code,xx[valid]),1)
        if channel<3:np.add.at(hist[channel],code,1)
    with np.errstate(invalid='ignore'):
        cb=ycc[1] if ycc else (rgb[:,:,2]-luma)/(2*(1-kb));cr=ycc[2] if ycc else (rgb[:,:,0]-luma)/(2*(1-kr))
        half=.5/c['vectorZoom'];valid=np.isfinite(cb)&np.isfinite(cr)&(abs(cb)<=half)&(abs(cr)<=half)
    vx=np.floor((cb[valid]+half)/(2*half)*511+.5).astype(int);vy=np.floor((cr[valid]+half)/(2*half)*511+.5).astype(int)
    np.add.at(vec,(vy,vx),1)
    return wave,parade,hist,vec

def density(a,qx,qy,fx,fy,parade=False):
    # Independent continuous integral of constant-density bin cells. Bilinear
    # evaluation of the summed-area table yields exact fractional cell coverage.
    h,w=a.shape;oh,ow=qx.shape;py,px=np.indices((oh,ow));py=oh-1-py
    if parade:
        channel=(2*px+1)*3//(2*ow);left=px*3-channel*ow;right=(px+1)*3-channel*ow
    else:left=px;right=px+1
    x0=np.clip(left*w/ow,0,w);x1=np.clip(right*w/ow,0,w)
    if h==3:y0=np.clip(np.floor(qy*h),0,h-1);y1=y0+1
    else:y0=py*h/oh;y1=(py+1)*h/oh
    summed=np.pad(a.astype(np.float64),((1,0),(1,0))).cumsum(0).cumsum(1)
    def integral(x,y):
        ix=np.floor(x).astype(int);iy=np.floor(y).astype(int);jx=np.minimum(ix+1,w);jy=np.minimum(iy+1,h);tx=x-ix;ty=y-iy
        return summed[iy,ix]*(1-tx)*(1-ty)+summed[iy,jx]*tx*(1-ty)+summed[jy,ix]*(1-tx)*ty+summed[jy,jx]*tx*ty
    area=(x1-x0)*(y1-y0)
    return (integral(x1,y1)-integral(x0,y1)-integral(x1,y0)+integral(x0,y0))/np.minimum(x1-x0,1)/np.minimum(y1-y0,1)

def reference(mode,a,w,h,samples,depth=8,twin_horizontal=True,twin_colour=False,trace_gain=1,trace_brightness=100,smooth=False,vector_magnification=1):
    x,y=np.meshgrid((np.arange(w)+.5)/w,1-(np.arange(h)+.5)/h)
    bg=np.full((h,w,3),.035);im=bg.copy()
    inks=np.array([[1,.22,.18],[.23,.9,.36],[.25,.48,1]])
    def trace_intensity(d):
        if smooth:
            padded=np.pad(d,3);filtered=np.zeros_like(d)
            for dy,wy in enumerate([1,6,15,20,15,6,1]):
                for dx,wx in enumerate([1,6,15,20,15,6,1]):filtered+=padded[dy:dy+h,dx:dx+w]*(wy*wx/4096)
            d=.25*d+.75*filtered
        return np.clip(np.log1p(d*trace_gain)*.25*(trace_brightness/100),0,1)
    if mode==0:im+=np.minimum(1,np.log1p(density(a,x,y,1/w,1/h))*.25)[:,:,None]*.82
    if mode==1:
        channel=np.minimum(2,(x*3).astype(int));qx=(x*3)%1
        for ch in range(3):im+=np.where(channel==ch,np.minimum(1,np.log1p(density(a[ch],qx,y,3/w,1/h,parade=True))*.25),0)[:,:,None]*inks[ch]
    if mode==2:
        for ch in range(3):
            d=density(a,x,np.full_like(y,(ch+.5)/3),1/w,.00001)
            im+=(y<np.log1p(d)/np.log1p(samples))[:,:,None]*inks[ch]*.5
    if mode==5:
        channel=np.minimum(2,(x*3).astype(int));qx=(x*3)%1
        for ch in range(3):
            d=density(a,qx,np.full_like(y,(ch+.5)/3),3/w,.00001,parade=True)
            v=np.log1p(d)/np.log1p(samples)
            im+=((channel==ch)&(y<v))[:,:,None]*inks[ch]*.5
    if mode==3:
        # Circle/axes are native-resolution SVG overlays, separate from traces.
        # Full rectangular viewport, equal physical scale on both chroma axes.
        bh,bw=a.shape;short=min(w,h)*vector_magnification
        x0=np.clip(((np.arange(w)-w/2)/short+.5)*bw,0,bw);x1=np.clip(((np.arange(w)+1-w/2)/short+.5)*bw,0,bw)
        y0=np.clip(((h/2-np.arange(h)-1)/short+.5)*bh,0,bh);y1=np.clip(((h/2-np.arange(h))/short+.5)*bh,0,bh)
        sat=np.pad(a.astype(float),((1,0),(1,0))).cumsum(0).cumsum(1)
        def at(xs,ys):
            xx,yy=np.meshgrid(xs,ys);ix=np.floor(xx).astype(int);iy=np.floor(yy).astype(int);jx=np.minimum(ix+1,bw);jy=np.minimum(iy+1,bh);tx=xx-ix;ty=yy-iy
            return sat[iy,ix]*(1-tx)*(1-ty)+sat[iy,jx]*tx*(1-ty)+sat[jy,ix]*(1-tx)*ty+sat[jy,jx]*tx*ty
        d=(at(x1,y1)-at(x0,y1)-at(x1,y0)+at(x0,y0))/min(bw/short,1)/min(bh/short,1)
        im+=trace_intensity(d)[:,:,None]*.85
    if mode==4:
        xx=(y-.5)*2.5 if twin_horizontal else (x-.5)*2.5;yy=(.5-x)*5 if twin_horizontal else (y-.5)*5
        edge=np.minimum(abs(abs(xx)+abs(yy-1)-1),abs(abs(xx)+abs(yy+1)-1));t=np.clip((edge-.002)/.012,0,1)
        bg=np.full((h,w,3),.035);im=bg.copy()
        ink=np.full((h,w,3),.85)
        if twin_colour:
            strength=np.clip(abs(xx)/np.maximum(abs(yy),.000001),0,1)
            tint=np.where((xx<0)[:,:,None],inks[1],np.where((yy>=0)[:,:,None],inks[2],inks[0]))
            ink=ink*(1-strength[:,:,None])+tint*strength[:,:,None]
        im+=trace_intensity(density(a.T[:,::-1] if twin_horizontal else a,x,y,1/w,1/h))[:,:,None]*ink
    maximum=2**depth-1;dtype=np.uint16 if depth==16 else np.uint8
    return dtype(np.clip(np.rint(im*maximum),0,maximum)),dtype(np.rint(bg*maximum))

def targets(c):
    kr,kg,kb=(.2627,.6780,.0593) if c.get('matrix')=='bt2020-ncl' else (.2126,.7152,.0722)
    result=[]
    for amplitude in (75,100):
        for name,r,g,b in [('R',1,0,0),('Y',1,1,0),('G',0,1,0),('C',0,1,1),('B',0,0,1),('M',1,0,1)]:
            r,g,b=np.array([r,g,b])*amplitude/100;y=kr*r+kg*g+kb*b;cb=(b-y)/(2*(1-kb));cr=(r-y)/(2*(1-kr))
            if abs(cb*c['vectorZoom'])<=.5 and abs(cr*c['vectorZoom'])<=.5:result.append((name,amplitude,cb,cr))
    return result
def draw_references(a,mode,c,case):
    if not case.get('targets'):return a
    h,w=a.shape[:2];scale=8;overlay=Image.new('RGBA',(w*scale,h*scale));draw=ImageDraw.Draw(overlay)
    if mode in (0,1):
        for value in (0,1):
            if c['min']<=value<=c['max']:
                y=(c['max']-value)/(c['max']-c['min'])*h
                for x in range(0,w,10):draw.rectangle((round(x*scale),round((y-.5)*scale),round((x+6)*scale)-1,round((y+.5)*scale)-1),fill='#777777')
    if mode==3:
        colors={'R':'#ff6050','Y':'#d0c050','G':'#60d080','C':'#60c0d0','B':'#7090ff','M':'#d080d0'}
        for name,amplitude,cb,cr in targets(c):
            x=(.5+cb*c['vectorZoom'])*w;y=(.5-cr*c['vectorZoom'])*h
            draw.rectangle((round((x-3.5)*scale),round((y-3.5)*scale),round((x+3.5)*scale)-1,round((y+3.5)*scale)-1),outline=colors[name],width=scale)
    overlay=overlay.resize((w,h),Image.Resampling.LANCZOS)
    return np.array(Image.alpha_composite(Image.fromarray(a).convert('RGBA'),overlay).convert('RGB'))

def check_overlay(base,overlay,case,c):
    difference=abs(overlay.astype(int)-base.astype(int)).max(2)
    def region(cx,cy,left,right,top,bottom):
        x0,x1=max(0,int(np.floor(left))),min(base.shape[1],int(np.ceil(right)));y0,y1=max(0,int(np.floor(top))),min(base.shape[0],int(np.ceil(bottom)))
        return difference[y0:y1,x0:x1]
    for p in case['plots'][:2]:
        for value in (0,1):
            if c['min']<=value<=c['max']:
                yy=p['y']+(c['max']-value)/(c['max']-c['min'])*p['height'];hits=[]
                for xx in np.arange(p['x']+2,p['x']+p['width']-2,10):
                    a=region(xx,yy,xx-1,xx+2,max(p['y'],yy-1),min(p['y']+p['height'],yy+2));hits.append(a.size>0 and a.max()>6)
                if np.mean(hits)<.9:return False
    p=case['plots'][3]
    for name,amplitude,cb,cr in targets(c):
        x=p['x']+(.5+cb*c['vectorZoom'])*p['width'];y=p['y']+(.5-cr*c['vectorZoom'])*p['height']
        for side in range(4):
            cx,cy=(x-3,y) if side==0 else (x+3,y) if side==1 else (x,y-3) if side==2 else (x,y+3)
            if not(p['x']<=cx<p['x']+p['width'] and p['y']<=cy<p['y']+p['height']):continue
            a=region(cx,cy,cx-1.5,cx+1.5,cy-1.5,cy+1.5)
            if not a.size or a.max()<=10:return False
    return True

def compare(actual,expected,bg,tolerance=12):
    # Match colour within 12/255 and spatial registration within one pixel.
    # Evaluate trace pixels separately: a nearly black image cannot pass by area.
    def distances(a,b):
        p=np.pad(b.astype(int),((1,1),(1,1),(0,0)),mode='edge');h,w=a.shape[:2]
        return np.minimum.reduce([abs(a.astype(int)-p[dy:dy+h,dx:dx+w]).max(2) for dy in range(3) for dx in range(3)])
    forward=distances(expected,actual);reverse=distances(actual,expected)
    expected_ink=(expected.astype(int)-bg.astype(int)).max(2)>10
    actual_ink=(actual.astype(int)-bg.astype(int)).max(2)>10
    recall=float((forward[expected_ink]<=tolerance).mean()) if expected_ink.any() else 1
    precision=float((reverse[actual_ink]<=tolerance).mean()) if actual_ink.any() else 1
    # Require every connected trace feature, not only overall area agreement.
    seen=np.zeros(expected_ink.shape,bool);feature_recalls=[];height,width=seen.shape
    for sy,sx in zip(*np.where(expected_ink)):
        if seen[sy,sx]:continue
        queue=deque([(sy,sx)]);seen[sy,sx]=True;pixels=[]
        while queue:
            yy,xx=queue.popleft();pixels.append((yy,xx))
            for ny in range(max(0,yy-1),min(height,yy+2)):
                for nx in range(max(0,xx-1),min(width,xx+2)):
                    if expected_ink[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;queue.append((ny,nx))
        py,px=np.array(pixels).T
        if (expected.astype(int)-bg.astype(int))[py,px].max()>20:feature_recalls.append(float((forward[py,px]<=tolerance).mean()))
    minimum_feature_recall=min(feature_recalls,default=1.)
    # Also require background agreement, catches blank canvases / mismatched palette.
    bad=float((reverse>tolerance).mean())
    return {'trace_recall':recall,'trace_precision':precision,'bad_pixel_fraction':bad,'minimum_feature_recall':minimum_feature_recall,'pass':minimum_feature_recall>=.8 and recall>=.98 and precision>=.98 and bad<=.01},np.maximum(forward,reverse)


def new_planes(rgb,c,ycc=None):
    kr,kg,kb=(.2627,.6780,.0593) if c['matrix']=='bt2020-ncl' else (.2126,.7152,.0722)
    r,g,b=np.moveaxis(rgb,2,0);l=ycc[0] if ycc else r*kr+g*kg+b*kb
    with np.errstate(invalid='ignore'):
        u=ycc[1] if ycc else (b-l)/(2*(1-kb));v=ycc[2] if ycc else (r-l)/(2*(1-kr))
    finite=np.isfinite(rgb).all(2);half=.5/c['vectorZoom'];inside=finite&(abs(u)<=half)&(abs(v)<=half)
    output=[];stats=[]
    for mask in [l<c['lowCut'],(l>=c['lowCut'])&(l<c['highCut']),l>=c['highCut']]:
        n=c.get("vectorSize",512);a=np.zeros((n,n),dtype=np.uint32);ok=mask&inside
        xx=np.floor((u[ok]+half)/(2*half)*(n-1)+.5).astype(int);yy=np.floor((v[ok]+half)/(2*half)*(n-1)+.5).astype(int)
        np.add.at(a,(yy,xx),1);output.append(a);stats.append({'pixels':int((mask&finite).sum()),'plotted':int(ok.sum()),'outside':int((mask&finite&~inside).sum())})
    a=np.zeros((1024,512),dtype=np.uint32);twin={}
    for name,value,sign in [('upper',b,1),('lower',r,-1)]:
        finite_pair=np.isfinite(value)&np.isfinite(g)
        with np.errstate(invalid='ignore'):xx=value-g;yy=sign*(value+g)
        ok=finite_pair&(abs(xx)<=1.25)&(abs(yy)<=2.5)
        ix=np.floor((xx[ok]+1.25)/2.5*511+.5).astype(int);iy=np.floor((yy[ok]+2.5)/5*1023+.5).astype(int);np.add.at(a,(iy,ix),1)
        twin[name]={'plotted':int(ok.sum()),'outside':int((finite_pair&~ok).sum()),'invalid':int((~finite_pair).sum()),'gamut':int((finite_pair&((value<0)|(value>1)|(g<0)|(g>1))).sum())}
    return output+[a],stats,twin

