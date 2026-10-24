import {unpackMean,WAVE_COLOUR_ENCODING} from './wave-colour-codec.mjs';
import {falseColour,sourceInk} from './waveform-colour.mjs';
import {smoothDensity} from './trace-style.mjs';
// Exact-count Canvas fallback when Safari cannot supply a working GPU context.
// Summed-area integration visits every covered bin; there is no source sampling.
const clamp=x=>Math.max(0,Math.min(1,x));
const inks=[[1,.22,.18],[.23,.9,.36],[.25,.48,1]];
function summed(values,w,h){const stride=w+1,a=new Float64Array((w+1)*(h+1));for(let y=0;y<h;y++){let row=0;for(let x=0;x<w;x++){row+=values[y*w+x];a[(y+1)*stride+x+1]=a[y*stride+x+1]+row;}}return {a,w,h,stride};}
function integral(s,x,y){x=Math.max(0,Math.min(s.w,x));y=Math.max(0,Math.min(s.h,y));const ix=Math.floor(x),iy=Math.floor(y),jx=Math.min(ix+1,s.w),jy=Math.min(iy+1,s.h),tx=x-ix,ty=y-iy,a=s.a,k=s.stride;return a[iy*k+ix]*(1-tx)*(1-ty)+a[iy*k+jx]*tx*(1-ty)+a[jy*k+ix]*(1-tx)*ty+a[jy*k+jx]*tx*ty;}
function area(s,x0,y0,x1,y1){x0=Math.max(0,Math.min(s.w,x0));x1=Math.max(x0,Math.min(s.w,x1));return (integral(s,x1,y1)-integral(s,x0,y1)-integral(s,x1,y0)+integral(s,x0,y0))/Math.min(x1-x0||1,1)/Math.min(y1-y0||1,1);}
function smoothstep(a,b,x){const t=clamp((x-a)/(b-a));return t*t*(3-2*t);}
function density(s,x,y,w,h,rotate=false){return rotate?area(s,(h-1-y)*s.w/h,(w-1-x)*s.h/w,(h-y)*s.w/h,(w-x)*s.h/w):area(s,x*s.w/w,(h-1-y)*s.h/h,(x+1)*s.w/w,(h-y)*s.h/h);}
function traceMap(s,w,h,style,rotate,magnification=null){let a=new Float64Array(w*h);for(let y=0;y<h;y++)for(let x=0;x<w;x++)a[y*w+x]=magnification===null?density(s,x,y,w,h,rotate):area(s,((x-w/2)/(Math.min(w,h)*magnification)+.5)*s.w,((h/2-y-1)/(Math.min(w,h)*magnification)+.5)*s.h,((x+1-w/2)/(Math.min(w,h)*magnification)+.5)*s.w,((h/2-y)/(Math.min(w,h)*magnification)+.5)*s.h);if(style.smooth)a=smoothDensity(a,w,h);for(let i=0;i<a.length;i++)a[i]=clamp(Math.log1p(a[i]*style.gain)*.25*style.brightness/100);return a;}

export function renderSoftware(data,scope,w,h,style={gain:1,brightness:100,smooth:false},options={}){
 const c=data.config,vector=scope===3||scope>=4&&scope<=6,twin=scope===7,hist=scope===2||scope===8||scope>=10;
 const name=vector?['vector','low','mid','high'][scope===3?0:scope-3]:twin?'twin':scope===0?'wave':scope===1?'parade':'hist';
 const bw=vector?c.vectorSize:twin?c.twinWidth:hist?c.histBins:c.waveWidth,bh=vector?c.vectorSize:twin?c.twinHeight:hist?1:c.levels;
 const channels=hist||scope===1?3:1,planes=[];for(let ch=0;ch<channels;ch++)planes.push(summed(data[name].subarray(ch*bw*bh,(ch+1)*bw*bh),bw,bh));
 let sourceColours=null;if(scope===0&&options.waveColourMode==='source'&&c.waveColour){if(data.waveColourEncoding===WAVE_COLOUR_ENCODING){const values=Array.from({length:3},()=>new Float64Array(bw*bh));for(let i=0;i<bw*bh;i++){const mean=unpackMean(data.waveColour[i]);for(let ch=0;ch<3;ch++)values[ch][i]=mean[ch]*data.wave[i];}sourceColours=values.map(a=>summed(a,bw,bh));}else sourceColours=Array.from({length:3},(_,ch)=>summed(data.waveColour.subarray(ch*bw*bh,(ch+1)*bw*bh),bw,bh));}
 const horizontal=options.twinHorizontal!==false,trace=vector||twin?traceMap(planes[0],w,h,style,twin&&horizontal,vector?(options.vectorMagnification??1):null):null,pixels=new Uint8ClampedArray(w*h*4);
 const matrix=data.measurement.matrix==='bt2020-ncl'?[.2627,.0593]:[.2126,.0722],kr=matrix[0],kb=matrix[1],kg=1-kr-kb;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const u=(x+.5)/w,v=1-(y+.5)/h;let bg=.035,r=bg,g=bg,b=bg;
  if(vector){let ink=[.85,.85,.85];if(options.vectorColour){const cx=(u-.5)*w/Math.min(w,h)/(options.vectorMagnification??1)/c.vectorZoom,cy=(v-.5)*h/Math.min(w,h)/(options.vectorMagnification??1)/c.vectorZoom,rr=2*(1-kr)*cy,bb=2*(1-kb)*cx,gg=-(kr*rr+kb*bb)/kg,lo=Math.min(rr,gg,bb),range=Math.max(rr,gg,bb)-lo,sat=clamp(Math.hypot(cx,cy)*4);ink=[rr,gg,bb].map(z=>.85*(1-sat+(z-lo)/Math.max(range,.000001)*sat));}const t=trace[y*w+x];r+=ink[0]*t;g+=ink[1]*t;b+=ink[2]*t;
  }else if(twin){const xx=(horizontal?v-.5:u-.5)*2*c.twinX,yy=(horizontal?.5-u:v-.5)*2*c.twinY,edge=Math.min(Math.abs(Math.abs(xx)+Math.abs(yy-1)-1),Math.abs(Math.abs(xx)+Math.abs(yy+1)-1));bg=.035;let ink=[.85,.85,.85];if(options.twinColour){const strength=clamp(Math.abs(xx)/Math.max(Math.abs(yy),.000001)),tint=xx<0?inks[1]:yy>=0?inks[2]:inks[0];ink=tint.map(z=>.85*(1-strength)+z*strength);}const t=trace[y*w+x];r=bg+ink[0]*t;g=bg+ink[1]*t;b=bg+ink[2]*t;
  }else if(hist){const ch=Math.min(2,Math.floor(u*3)),split=scope===8;for(let j=0;j<3;j++){if((split&&j!==ch)||(scope>=10&&j!==scope-10))continue;const x0=(split?x*3-ch*w:x)*bw/w,x1=(split?(x+1)*3-ch*w:x+1)*bw/w,d=area(planes[j],x0,0,x1,1);if(v<Math.log1p(d)/Math.log1p(data.samples)){r+=inks[j][0]*.5;g+=inks[j][1]*.5;b+=inks[j][2]*.5;}}
  }else if(scope===1){const ch=Math.min(2,Math.floor(u*3)),d=area(planes[ch],(x*3-ch*w)*bw/w,(h-1-y)*bh/h,((x+1)*3-ch*w)*bw/w,(h-y)*bh/h),t=clamp(Math.log1p(d)*.25);r+=inks[ch][0]*t;g+=inks[ch][1]*t;b+=inks[ch][2]*t;
  }else{const t=clamp(Math.log1p(density(planes[0],x,y,w,h))*.25)*.82,ink=sourceColours?sourceInk(sourceColours.map(p=>density(p,x,y,w,h))):options.waveColourMode==='false'?falseColour(c.min+v*(c.max-c.min)):[1,1,1];r+=t*ink[0];g+=t*ink[1];b+=t*ink[2];}
  const at=(y*w+x)*4;pixels[at]=Math.round(clamp(r)*255);pixels[at+1]=Math.round(clamp(g)*255);pixels[at+2]=Math.round(clamp(b)*255);pixels[at+3]=255;
 }
 return pixels;
}
