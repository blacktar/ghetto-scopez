import {SMOOTH_KERNEL} from './trace-style.mjs';
import {createShoutScroller} from './og-scroller.mjs';
import {createGalaxy} from './og-galaxy.mjs';
import {activeScopeBins} from './scope-wire.mjs';
import {OGGame,OG_MAGNIFICATION,OG_ORDER,OG_INK,ogTargets,strongestTarget,clock} from './og-game.mjs';
// Procedural GPU nebula/starfield with a bounded Canvas particle fallback. No additional library or external network asset is loaded.
export function createOGView(canvas){
 let galaxy=null,galaxyAttempted=false,benchCost=[];const bench=new URLSearchParams(location.search).has('ogbench'),effects=new URLSearchParams(location.search).get('ogeffects')!=='0';
 let scroller=null,magnification=OG_MAGNIFICATION;
 const trace=document.createElement('canvas'),smoothBase=document.createElement('canvas'),smoothPass=document.createElement('canvas'),smoothTrace=document.createElement('canvas');let traceKey=null,tracePixels=null,smoothKey=null;
 function filteredTrace(size){const dim=Math.max(1,Math.min(1024,Math.round(size)));if(smoothKey?.[0]===data&&smoothKey[1]===dim)return smoothTrace;for(const layer of [smoothBase,smoothPass,smoothTrace]){if(layer.width!==dim||layer.height!==dim){layer.width=dim;layer.height=dim;}else layer.getContext('2d').clearRect(0,0,dim,dim);}const base=smoothBase.getContext('2d');base.imageSmoothingEnabled=true;base.drawImage(trace,0,0,dim,dim);const pass=smoothPass.getContext('2d'),out=smoothTrace.getContext('2d');pass.globalCompositeOperation='lighter';out.globalCompositeOperation='lighter';for(let k=-3;k<=3;k++){pass.globalAlpha=SMOOTH_KERNEL[k+3]/64;pass.drawImage(smoothBase,k,0);}out.globalAlpha=.25;out.drawImage(smoothBase,0,0);for(let k=-3;k<=3;k++){out.globalAlpha=.75*SMOOTH_KERNEL[k+3]/64;out.drawImage(smoothPass,0,k);}smoothKey=[data,dim];return smoothTrace;}
 const context=canvas.getContext('2d',{alpha:false});let game=null,data=null,candidate=null,key='',transitions=[],lastDraw=0,audio=null,sound=null,completeAt=null;
 const art=document.createElement('img');art.alt='';art.setAttribute('aria-hidden','true');art.decoding='async';art.style.cssText='position:absolute;display:none;pointer-events:none;image-rendering:pixelated;object-fit:contain;z-index:1;opacity:0';canvas.parentElement.append(art);
 let artReadyAt=null;art.onload=()=>{artReadyAt=performance.now();};
 const floaters=OG_ORDER.map(label=>{const el=document.createElementNS('http://www.w3.org/2000/svg','svg');el.setAttribute('viewBox','0 0 20 28');el.setAttribute('aria-hidden','true');el.style.cssText='position:absolute;left:0;top:0;width:20px;height:28px;pointer-events:none;z-index:2;opacity:0;will-change:transform;display:none';
  const edge=document.createElementNS(el.namespaceURI,'path');edge.setAttribute('d','M10 1L19 14L10 27L1 14Z M10 1V27 M1 14H19');edge.setAttribute('fill',OG_INK[label]+'55');edge.setAttribute('stroke',OG_INK[label]);edge.setAttribute('stroke-width','1.3');el.append(edge);canvas.parentElement.append(el);return el;});
 function hideCelebration(){art.style.display='none';art.removeAttribute('src');artReadyAt=null;for(const el of floaters)el.style.display='none';}

 let best=null;try{const value=JSON.parse(localStorage.getItem('scopeOGBestV1'));if(value?.version===1&&Number.isFinite(value.milliseconds)&&value.milliseconds>=0)best=value.milliseconds;}catch{}
 const stars=Array.from({length:180},(_,i)=>({r:((i*73+17)%101)/101,a:i*2.39996323,z:.4+(i%7)/10}));
 let musicBuffer=null;
 function loadMusic(){if(!audio)return Promise.resolve(null);return musicBuffer??=fetch(new URL('./assets/random-voice-monday.m4a',import.meta.url)).then(response=>{if(!response.ok)throw new Error('Monday audio unavailable');return response.arrayBuffer();}).then(bytes=>audio.decodeAudioData(bytes)).catch(()=>{musicBuffer=null;return null;});}
 function armAudio(){try{audio??=new(window.AudioContext||window.webkitAudioContext)();void audio.resume();void loadMusic();}catch{}}
 async function chime(){if(!audio)return;const run=game,buffer=await loadMusic();if(!buffer||game!==run||game.ended||game.finished===null||audio.state!=='running')return;
  sound?.stop();sound=audio.createBufferSource();sound.buffer=buffer;sound.loop=true;const gain=audio.createGain();gain.gain.value=.5;sound.connect(gain).connect(audio.destination);sound.start();}
 function begin(){hideCelebration();transitions=[];completeAt=null;data=null;candidate=null;key='';game=new OGGame({best,save:value=>{best=value;try{localStorage.setItem('scopeOGBestV1',JSON.stringify({version:1,milliseconds:value}));}catch{}},event:e=>{if(e.type==='capture')transitions.push({...e,returning:false});if(e.type==='reset'){transitions=e.labels.map((label,index)=>({type:'capture',label,index,time:e.time,returning:true}));}if(e.type==='complete'){completeAt=e.time;art.src=new URL('./assets/og-celebration.webp',import.meta.url).href;chime();}}});}
 function ingest(value){if(!game||game.ended||game.finished!==null)return;const live=value?.source?.capture?.producer==='resolve-ofx';if(!live){candidate=null;game.clearHold();return;}data=value;const nextKey=JSON.stringify([value.config.vectorSize,value.config.vectorZoom,value.targets]);if(key!==nextKey){game.clearHold();key=nextKey;}candidate=strongestTarget(value,game.collected,magnification);}
 function render(now,visible,qualityScale=1,smooth=false){if(!game||!visible){game?.clearHold();art.style.display='none';for(const el of floaters)el.style.display='none';return;}if(now-lastDraw<1000/30)return;lastDraw=now;if(document.visibilityState==='visible'&&data&&!game.ended)game.feed(candidate,now);else game.clearHold();
  const costStart=bench?performance.now():0;const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2)*qualityScale,w=Math.max(1,Math.round(rect.width*dpr)),h=Math.max(1,Math.round(rect.height*dpr));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}const c=context;c.setTransform(dpr,0,0,dpr,0,0);const width=w/dpr,height=h/dpr,side=Math.min(width,height)*.84,cx=width/2,cy=height/2;
  c.fillStyle='#02030b';c.fillRect(0,0,width,height);const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches,t=reduced?0:now*.0001;
  if(effects&&!galaxyAttempted){galaxyAttempted=true;galaxy=createGalaxy();}
  const gpuBackground=galaxy?.draw(c,width,height,now,reduced);
  if(effects&&!gpuBackground){ // Quiet particle fallback on devices without WebGL2.
   c.save();c.globalCompositeOperation='screen';for(const star of stars){const a=star.a+t*.08,r=star.r*Math.hypot(width,height)*.55,x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r*.7;c.globalAlpha=.25+.5*(.5+.5*Math.sin(star.a+t*star.z*10));c.fillStyle=star.z>.7?'#57dcff':'#ffc8ff';c.fillRect(x,y,star.z*2,star.z*2);}c.restore();}
  const fade=completeAt===null||artReadyAt===null?0:reduced?1:Math.min(1,Math.max(0,(now-artReadyAt)/1200));
  const point=target=>[cx+target.cb*side,cy-target.cr*side];
  c.save();c.globalAlpha=1-fade;
  // Recreate the artwork's instrument rim and graduated ring as vector geometry.
  const radius=side*.45,rim=c.createLinearGradient(cx-radius,cy-radius,cx+radius,cy+radius);
  for(const [at,ink]of [[0,'#3b8cff'],[.18,'#e0faff'],[.36,'#fff6ff'],[.53,'#d471ff'],[.72,'#78e8ff'],[1,'#eefaff']])rim.addColorStop(at,ink);
  c.save();c.shadowColor='#4ccfff';c.shadowBlur=9;c.strokeStyle=rim;c.lineWidth=1.6;c.beginPath();c.arc(cx,cy,radius,0,Math.PI*2);c.stroke();c.shadowBlur=0;
  c.strokeStyle='#d7ecff50';c.lineWidth=.7;c.beginPath();c.arc(cx,cy,radius+4,0,Math.PI*2);c.arc(cx,cy,radius-4,0,Math.PI*2);c.stroke();
  for(let tick=0;tick<120;tick++){const angle=tick*Math.PI/60,major=tick%10===0,length=major?11:tick%5===0?7:3.5;c.strokeStyle=major?'#f0f6ffb0':'#d6e9ff60';c.lineWidth=major?1.1:.65;c.beginPath();c.moveTo(cx+Math.cos(angle)*(radius-7),cy+Math.sin(angle)*(radius-7));c.lineTo(cx+Math.cos(angle)*(radius-7-length),cy+Math.sin(angle)*(radius-7-length));c.stroke();}
  // Distinct inner instrument ring, with the artwork's diagonal radial guides.
  const innerRadius=side*.34;
  c.strokeStyle=rim;c.lineWidth=1;c.globalAlpha=.65*(1-fade);c.beginPath();c.arc(cx,cy,innerRadius,0,Math.PI*2);c.stroke();c.globalAlpha=1-fade;
  c.strokeStyle='#64cfff40';c.lineWidth=.7;c.beginPath();c.arc(cx,cy,side*.225,0,Math.PI*2);c.stroke();
  c.strokeStyle='#aedbff65';c.lineWidth=.8;
  for(const angle of [Math.PI/4,3*Math.PI/4,5*Math.PI/4,7*Math.PI/4]){c.beginPath();c.moveTo(cx,cy);c.lineTo(cx+Math.cos(angle)*radius,cy+Math.sin(angle)*radius);c.stroke();}
  c.strokeStyle='#a4edff70';c.beginPath();c.moveTo(cx-side*.5,cy);c.lineTo(cx+side*.5,cy);c.moveTo(cx,cy-side*.5);c.lineTo(cx,cy+side*.5);c.stroke();
  c.fillStyle='#dcfaff';c.shadowColor='#69dfff';c.shadowBlur=9;c.beginPath();c.arc(cx,cy,1.7,0,Math.PI*2);c.fill();c.restore();
  // Counts are plotted directly in Cb/Cr coordinates; ambient effects never enter scoring.
  if(data?.vector&&fade<1){const n=data.config.vectorSize,z=data.config.vectorZoom||1;
   if(traceKey!==data){if(trace.width!==n||trace.height!==n){trace.width=n;trace.height=n;tracePixels=trace.getContext('2d').createImageData(n,n);}const pixels=tracePixels.data;pixels.fill(0);const bins=data.vector,active=activeScopeBins(bins),m=data.config.matrix==='bt2020'?{kr:.2627,kb:.0593}:{kr:.2126,kb:.0722};
    for(let at=0;at<(active?.length??bins.length);at++){const i=active?active[at]:at,count=bins[i];if(!count)continue;const cb=(i%n/(n-1)-.5)/z,cr=(Math.floor(i/n)/(n-1)-.5)/z,r=2*(1-m.kr)*cr,b=2*(1-m.kb)*cb,g=-(m.kr*r+m.kb*b)/(1-m.kr-m.kb),lo=Math.min(r,g,b),range=Math.max(.001,Math.max(r,g,b)-lo),p=((n-1-Math.floor(i/n))*n+i%n)*4;
     pixels[p]=Math.round(100+155*(r-lo)/range);pixels[p+1]=Math.round(100+155*(g-lo)/range);pixels[p+2]=Math.round(100+155*(b-lo)/range);pixels[p+3]=Math.round(255*Math.min(1,.2+Math.log1p(count)*.15));}
    trace.getContext('2d').putImageData(tracePixels,0,0);traceKey=data;}
   const span=side*magnification/z;c.save();c.globalCompositeOperation='screen';c.imageSmoothingEnabled=true;c.drawImage(smooth?filteredTrace(span*dpr):trace,cx-span/2,cy-span/2,span,span);c.restore();}

  c.restore();
  if(bench){benchCost.push(performance.now()-costStart);if(benchCost.length>600)benchCost.shift();if(benchCost.length%30===0){const sorted=[...benchCost].sort((a,b)=>a-b);canvas.dataset.ogCost=JSON.stringify({samples:sorted.length,median:sorted[Math.floor(sorted.length*.5)],p95:sorted[Math.floor(sorted.length*.95)],effects});}}
  if(new URLSearchParams(location.search).has('visual')||bench){canvas.dataset.ogCollected=game.collected.join('');canvas.dataset.ogComplete=String(game.finished!==null);canvas.dataset.ogElapsed=String(Math.round(game.elapsed(now)));canvas.dataset.ogEnded=String(game.ended);}
  const targets=ogTargets(data||{}); // Nominal 75% BT.709 fallback while awaiting live input.
  if(!targets.length){const kr=.2126,kb=.0722;for(const label of OG_ORDER){const rgb={R:[.75,0,0],M:[.75,0,.75],B:[0,0,.75],C:[0,.75,.75],G:[0,.75,0],Y:[.75,.75,0]}[label],y=kr*rgb[0]+(1-kr-kb)*rgb[1]+kb*rgb[2];targets.push({label,cb:(rgb[2]-y)/(2*(1-kb)),cr:(rgb[0]-y)/(2*(1-kr))});}}
  // Neon-edged square and centre light match the reference artwork, not a texture.
  function targetBox(x,y,label,alpha=1){const half=side*.025,ink=OG_INK[label];c.save();c.globalAlpha=alpha;c.strokeStyle=ink;c.lineWidth=2;c.shadowColor=ink;c.shadowBlur=9;c.strokeRect(x-half,y-half,half*2,half*2);c.shadowBlur=0;c.globalAlpha=alpha*.65;c.strokeStyle='#f4fcff';c.lineWidth=.65;c.strokeRect(x-half+1.5,y-half+1.5,half*2-3,half*2-3);c.globalAlpha=alpha;c.shadowColor=ink;c.shadowBlur=7;c.fillStyle='#fff';c.beginPath();c.arc(x,y,Math.max(1,Math.min(2.5,side*.003)),0,Math.PI*2);c.fill();c.restore();}
  for(const target of targets){const [x,y]=point(target);if(game.collected.includes(target.label)||transitions.some(e=>e.returning&&e.label===target.label&&now-e.time<800))continue;targetBox(x,y,target.label);c.fillStyle=OG_INK[target.label];c.font='10px system-ui';c.fillText(target.label,x+side*.034,y+3);}
  function diamond(x,y,label,angle=0,scale=1){c.save();c.translate(x,y);c.rotate(angle);c.scale(scale,scale);c.shadowColor=OG_INK[label];c.shadowBlur=12;c.strokeStyle=OG_INK[label];c.fillStyle=OG_INK[label]+'55';c.beginPath();c.moveTo(0,-11);c.lineTo(8,0);c.lineTo(0,11);c.lineTo(-8,0);c.closePath();c.fill();c.stroke();c.beginPath();c.moveTo(0,-11);c.lineTo(0,11);c.moveTo(-8,0);c.lineTo(8,0);c.stroke();c.restore();}
  transitions=transitions.filter(e=>!e.returning||now-e.time<800);
  const labels=new Set([...game.collected,...transitions.filter(e=>e.returning).map(e=>e.label)]);
  c.save();c.globalAlpha=1-fade;
  for(const label of labels){const e=transitions.findLast(e=>e.label===label),index=e?.index??game.collected.indexOf(label),target=targets.find(t=>t.label===label);if(!target)continue;const from=point(target),to=[20,27+index*31],elapsed=e?Math.min(1,(now-e.time)/800):1,progress=reduced?1:1-(1-elapsed)**3,q=e?.returning?1-progress:progress,x=from[0]+(to[0]-from[0])*q,y=from[1]+(to[1]-from[1])*q;if(e?.returning&&elapsed>.7){targetBox(x,y,label,(elapsed-.7)/.3);}diamond(x,y,label,reduced?0:now*.003,Math.max(.1,e?.returning?1-elapsed:Math.min(1,elapsed*4)));}
  c.restore();
  c.font='12px ui-monospace,monospace';c.fillStyle='#eff8ff';c.textAlign='right';c.fillText(clock(game.elapsed(now)),width-12,20);c.fillStyle='#c2d8e9';c.fillText('Highscore: '+(game.best===null?'--:--:--':clock(game.best)),width-12,height-12);c.textAlign='left';
  if(completeAt!==null){const scrollHeight=Math.min(50,Math.max(24,height*.065)),size=Math.max(16,Math.min(width*.72,height*.68,height-scrollHeight-70)),artCy=Math.max(24+size/2,(height-scrollHeight-24)/2);
   // Native animated WebP playback avoids copying/decoding its96frames in JS.
   if(artReadyAt!==null){Object.assign(art.style,{display:'block',left:(canvas.offsetLeft+cx-size/2)+'px',top:(canvas.offsetTop+artCy-size/2)+'px',width:size+'px',height:size+'px',opacity:String(fade)});
    const age=(now-artReadyAt)/1000;
    floaters.forEach((el,index)=>{const phase=index*Math.PI/3,move=reduced?1:Math.max(0,Math.min(1,(age-.3-index*.09)/1.6)),ease=1-(1-move)**3,orbitTime=reduced?0:age;
     const tx=cx+Math.cos(phase+orbitTime*.12)*width*.39,ty=height*.42+Math.sin(phase+orbitTime*.15)*height*.29,x=20+(tx-20)*ease,y=27+index*31+(ty-27-index*31)*ease;
     Object.assign(el.style,{display:'block',opacity:String(fade),transform:`translate(${canvas.offsetLeft+x-10}px,${canvas.offsetTop+y-14}px) rotate(${reduced?0:now*.06+index*60}deg)`});});
   }
   c.save();c.globalAlpha=fade;(scroller??=createShoutScroller()).draw(c,{x:12,y:artCy+size/2+12,width:width-24,height:scrollHeight,elapsed:now-completeAt,reduced});c.restore();
  }

 }
 return {begin,ingest,render,setMagnification(value){if(value===magnification)return;magnification=value;game?.clearHold();if(data&&game)candidate=strongestTarget(data,game.collected,magnification);},armAudio,clearSignal(){candidate=null;data=null;traceKey=null;game?.clearHold();},get game(){return game;},end(){sound?.stop();sound=null;hideCelebration();game?.end();candidate=null;data=null;transitions=[];completeAt=null;if(audio)void audio.suspend();},dispose(){sound?.stop();sound=null;art.remove();for(const el of floaters)el.remove();galaxy?.dispose();if(audio)void audio.close();}};
}
