import {activeScopeBins} from './scope-wire.mjs';
import {calibratedTargets} from './signal.mjs';
// OG's state machine consumes exact vectorscope counts; display gain never scores.
export const OG_SCOPE=16;
export const OG_MAGNIFICATION=2;
export function ogDisplaySettings(saved){return {zoom:[1,2,3,4].includes(saved?.zoom)?saved.zoom:2,detail:[1,2,3,4].includes(saved?.detail)?saved.detail:4};}
export const OG_ORDER=['R','M','B','C','G','Y'];
export const OG_INK={R:'#ff453a',M:'#ff35ed',B:'#368bff',C:'#39f5ff',G:'#67ff57',Y:'#ffe74d'};
export const OG_END='End this game? Progress will be lost, like tears in the rain.';
export function clock(ms){const seconds=Math.max(0,Math.floor(ms/1000));return [Math.floor(seconds/3600),Math.floor(seconds/60)%60,seconds%60].map(v=>String(v).padStart(2,'0')).join(':');}
export function ogTargets(data){const targets=data.targets?.length?data.targets:calibratedTargets(data.source?.signal?.domain==='working'?'bt709':data.config?.matrix||'bt709');return OG_ORDER.map(label=>targets.find(t=>t.label===label&&t.percent===75)).filter(Boolean);}
export function strongestTarget(data,collected=[],magnification=OG_MAGNIFICATION){
 const bins=data.vector,n=data.config?.vectorSize,zoom=(data.config?.vectorZoom||1)/magnification,targets=ogTargets(data);
 if(!bins||!n||targets.length!==6)return null;
 const clusters=targets.map(t=>({...t,ux:t.cb/Math.hypot(t.cb,t.cr),uy:t.cr/Math.hypot(t.cb,t.cr),mass:0,inside:0}));let chromatic=0,total=0;
 // Chroma sectors classify the colour cluster; only mass in the visible square scores.
 const active=activeScopeBins(bins);for(let at=0;at<(active?.length??bins.length);at++){const i=active?active[at]:at,count=bins[i];if(!count)continue;total+=count;const cb=(i%n/(n-1)-.5)/zoom,cr=(Math.floor(i/n)/(n-1)-.5)/zoom,r=Math.hypot(cb,cr);if(r<.06)continue;chromatic+=count;
  let closest=null,distance=-Infinity;for(const t of clusters){const dot=cb*t.ux+cr*t.uy;if(dot>distance){distance=dot;closest=t;}}
  if(!closest)continue;closest.mass+=count;if(Math.abs(cb-closest.cb)<=.025&&Math.abs(cr-closest.cr)<=.025)closest.inside+=count;
 }
 const remaining=clusters.filter(t=>!collected.includes(t.label)).sort((a,b)=>b.mass-a.mass);const first=remaining[0],second=remaining[1];if(!first)return null;chromatic=remaining.reduce((sum,t)=>sum+t.mass,0);
 if(first.mass<Math.max(16,total*.02)||first.mass<chromatic*.35||first.mass<(second?.mass??0)*1.15||first.inside<Math.max(16,total*.02))return null;
 return first.label;
}
export class OGGame{
 constructor({best=null,save=()=>{},event=()=>{}}={}){this.best=Number.isFinite(best)&&best>=0?best:null;this.save=save;this.event=event;this.collected=[];this.started=null;this.finished=null;this.ended=false;this.candidate=null;this.since=null;}
 get inProgress(){return !this.ended&&this.started!==null&&this.finished===null;}
 elapsed(now){return this.started===null?0:(this.finished??now)-this.started;}
 clearHold(){this.candidate=null;this.since=null;}
 feed(label,now){if(this.ended||this.finished!==null)return;if(!label||this.collected.includes(label)){this.clearHold();return;}
  if(this.candidate!==label){this.candidate=label;this.since=now;return;}if(now-this.since<1000)return;this.clearHold();
  if(label!==OG_ORDER[this.collected.length]){if(this.collected.length){const old=[...this.collected];this.collected=[];this.event({type:'reset',labels:old,time:now});}return;}
  if(this.started===null)this.started=now;this.collected.push(label);this.event({type:'capture',label,index:this.collected.length-1,time:now});
  if(this.collected.length===6){this.finished=now;const score=this.elapsed(now);if(this.best===null||score<this.best){this.best=score;this.save(score);}this.event({type:'complete',time:now});}
 }
 end(){this.ended=true;this.started=null;this.finished=null;this.collected=[];this.clearHold();}
}
