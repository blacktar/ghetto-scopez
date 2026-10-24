import {selected} from './colour-analysis.mjs';import {MATRICES} from './signal.mjs';
import {decodeSample} from './signal.mjs';
export function cubeDistribution(frame,config,storage,nativeKernel){
 const n=config.cubeResolution,size=n**3,a=storage?.cube?.length===size?storage.cube:new Uint32Array(size);a.fill(0);const indices=[],stats={plotted:0,outside:0,invalid:0,occupied:0};
 const {data,width,signal}=frame,{x0,x1,y0,y1,min,max}=config,scale=(n-1)/(max-min),direct=signal.model==='RGB'&&signal.range==='full';
 if(direct&&nativeKernel){const indices=nativeKernel(data,{...config,sourceWidth:width,sourceHeight:frame.height},a,stats);return {cube:a,indices,stats};}
 for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++){const i=(y*width+x)*3;let r=data[i],g=data[i+1],b=data[i+2];if(!direct)[r,g,b]=decodeSample(r,g,b,signal);const m=MATRICES[signal.matrix];if(!selected(r,g,b,m.kr*r+m.kg*g+m.kb*b,config))continue;if(!Number.isFinite(r)||!Number.isFinite(g)||!Number.isFinite(b)){stats.invalid++;continue;}if(r<min||r>max||g<min||g>max||b<min||b>max){stats.outside++;continue;}const ix=Math.round((r-min)*scale)+n*(Math.round((g-min)*scale)+n*Math.round((b-min)*scale));if(a[ix]===0)indices.push(ix);a[ix]++;stats.plotted++;}
 stats.occupied=indices.length;return {cube:a,indices,stats};
}
export function cubePoints(counts,n,min=0,max=1){let occupied=0;for(const count of counts)if(count)occupied++;const positions=new Float32Array(occupied*3),colours=new Float32Array(occupied*3),weights=new Float32Array(occupied);let point=0;for(let i=0;i<counts.length;i++)if(counts[i]){const r=i%n/(n-1),g=Math.floor(i/n)%n/(n-1),b=Math.floor(i/n/n)/(n-1);positions.set([r-.5,g-.5,b-.5],point*3);colours.set([r,g,b].map(v=>Math.max(0,Math.min(1,min+v*(max-min)))),point*3);weights[point++]=counts[i];}return {positions,colours,weights};}
// A round splat covers the projected voxel footprint, independent of device pixels.
export function cubePointSize(n,span,zoom=1){return Math.max(4,Math.min(48,span*zoom/(2*(n-1))*1.6));}
export function projectCube(p,yaw,pitch){const c=Math.cos(yaw),s=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch),x=c*p[0]+s*p[2],z=-s*p[0]+c*p[2];return [x,cp*p[1]-sp*z,sp*p[1]+cp*z];}
