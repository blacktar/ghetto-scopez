export const initialView=()=>({scale:1,x:0,y:0});
const bounded=v=>({scale:v.scale,x:Math.max(1-v.scale,Math.min(0,v.x)),y:Math.max(1-v.scale,Math.min(0,v.y))});
export function zoomView(view,scale,anchor){scale=Math.max(1,Math.min(8,scale));const ratio=scale/view.scale;return bounded({scale,x:anchor.x-(anchor.x-view.x)*ratio,y:anchor.y-(anchor.y-view.y)*ratio});}
export function panView(view,delta){return bounded({...view,x:view.x+delta.x,y:view.y+delta.y});}
export function pinchView(view,start,end,ratio){return panView(zoomView(view,view.scale*ratio,start),{x:end.x-start.x,y:end.y-start.y});}
export function displayView(view,magnification=1){return {scale:view.scale*magnification,x:.5-(.5-view.x)*magnification,y:.5-(.5-view.y)*magnification};}
export function bindScopeZoom(canvas,onChange,{lockOrigin=false,displayScale=()=>1}={}){
 const plot=canvas.parentElement,card=canvas.closest('.scope');let view=initialView(),gesture=null;const pointers=new Map();
 const reset=document.createElement('button');reset.className='scope-zoom-reset';reset.hidden=true;reset.setAttribute('aria-label','Reset zoom for '+card.querySelector('.scopehead>span').textContent);card.querySelector('.scopehead').append(reset);
 const point=e=>{const r=plot.getBoundingClientRect();return {x:(e.clientX-r.left-canvas.offsetLeft)/Math.max(1,canvas.clientWidth),y:(e.clientY-r.top-canvas.offsetTop)/Math.max(1,canvas.clientHeight)};};
 const update=(notify=true)=>{const drawn=displayView(view,displayScale());canvas.style.transformOrigin='0 0';canvas.style.transform=(lockOrigin&&Number(card.dataset.scope)>=3&&Number(card.dataset.scope)<=6)||drawn.scale===1?'':`matrix(${drawn.scale},0,0,${drawn.scale},${drawn.x*parseFloat(getComputedStyle(canvas).width)},${drawn.y*parseFloat(getComputedStyle(canvas).height)})`;plot.classList.toggle('scope-zoomed',drawn.scale>1);plot.dataset.localZoom=String(view.scale);reset.hidden=view.scale===1;reset.textContent=`${view.scale.toFixed(1)}× · Reset`;if(notify)onChange?.();};
 const pair=()=>{const [a,b]=[...pointers.values()];return a&&b?{middle:{x:(a.x+b.x)/2,y:(a.y+b.y)/2},distance:Math.hypot((a.x-b.x)*canvas.clientWidth,(a.y-b.y)*canvas.clientHeight)}:null;};
 const begin=()=>{const p=pair();gesture=p?{view:{...view},...p}:pointers.size===1?{view:{...view},point:[...pointers.values()][0]}:null;};
 reset.onclick=()=>{view=initialView();update();};plot.addEventListener('dblclick',e=>{e.preventDefault();view=initialView();update();});
 plot.addEventListener('wheel',e=>{e.preventDefault();const pixels=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?canvas.clientHeight:1);view=zoomView(view,view.scale*Math.exp(-Math.max(-400,Math.min(400,pixels))*.0025),lockOrigin?{x:.5,y:.5}:point(e));update();},{passive:false});
 plot.addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'&&e.button!==0)return;pointers.set(e.pointerId,point(e));plot.setPointerCapture(e.pointerId);begin();});
 plot.addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId)||!gesture)return;pointers.set(e.pointerId,point(e));const p=pair();if(p&&gesture.distance>0)view=lockOrigin?zoomView(gesture.view,gesture.view.scale*p.distance/gesture.distance,{x:.5,y:.5}):pinchView(gesture.view,gesture.middle,p.middle,p.distance/gesture.distance);else if(!lockOrigin&&pointers.size===1&&gesture.point)view=panView(gesture.view,{x:point(e).x-gesture.point.x,y:point(e).y-gesture.point.y});update();});
 const end=e=>{pointers.delete(e.pointerId);begin();};for(const type of ['pointerup','pointercancel','lostpointercapture'])plot.addEventListener(type,end);
 return {apply:()=>update(false),get view(){return {...view};}};
}
