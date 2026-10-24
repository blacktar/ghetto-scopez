// Display raster quality only. Source pixels, analysis configuration and count
// textures never pass through this controller.
export const QUALITY_MODES=['auto','low','medium','high'];
const SCALES=[.5,.75,1],NAMES=['low','medium','high'];
export class RenderQuality {
 constructor(mode='auto'){this.setMode(mode);}
 setMode(mode){if(!QUALITY_MODES.includes(mode))throw Error('Invalid rendering quality');this.mode=mode;this.level=mode==='auto'?2:NAMES.indexOf(mode);this.bad=0;this.good=0;this.lastChange=-Infinity;this.lastSample=null;}
 softwareFallback(){if(this.mode==='auto'){this.level=0;this.bad=0;this.good=0;}}
 get scale(){return SCALES[this.level];}
 get effective(){return NAMES[this.level];}
 observe({drawMs,queuedMs=0,targetFps=60,now,visible=true}){
  if(this.mode!=='auto'||!visible||!Number.isFinite(drawMs)||!Number.isFinite(now))return false;
  if(this.lastSample!==null&&now-this.lastSample>2000){this.bad=0;this.good=0;}
  this.lastSample=now;
  const budget=1000/Math.max(1,Math.min(60,targetFps));
  // Queue delay alone can come from browser scheduling; require meaningful
  // local draw cost too. Never react to a slow source or network frame rate.
  const overloaded=drawMs>budget*.8||(drawMs>budget*.25&&queuedMs>budget*1.5);
  const spare=drawMs<budget*.35&&queuedMs<budget*.75;
  this.bad=overloaded?this.bad+1:0;this.good=spare?this.good+1:0;
  if(now-this.lastChange<1500)return false;
  const next=this.bad>=3?Math.max(0,this.level-1):this.good>=90?Math.min(2,this.level+1):this.level;
  if(next===this.level)return false;this.level=next;this.bad=0;this.good=0;this.lastChange=now;return true;
 }
}
export function rasterSize(width,height,dpr,scale){const ratio=Math.min(Math.max(dpr||1,1),2)*scale;return [Math.max(1,Math.floor(width*ratio)),Math.max(1,Math.floor(height*ratio))];}
