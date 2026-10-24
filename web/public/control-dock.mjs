export function dockMayHide({fullscreen,settings,dragging,hovering,keyboardFocus}){return !settings&&!dragging&&!hovering&&!keyboardFocus;}
export function bindControlDock({doc=document,idleMs=3000}={}){
 const body=doc.body,dock=doc.getElementById('fullscreencontrols'),panel=doc.getElementById('panel'),handle=doc.createElement('button');handle.id='controlhandle';handle.className='quiet';handle.type='button';handle.setAttribute('aria-controls','fullscreencontrols');dock.parentElement.append(handle);
 let timer,keyboard=false,hovering=false;const pointers=new Set();
 // Place the disclosure between the two tabs without moving it into the tablist.
 const tabs=doc.querySelector('header>.view-tabs');
 const alignHandle=()=>{if(!tabs)return;const r=tabs.getBoundingClientRect(),h=dock.parentElement.getBoundingClientRect();dock.parentElement.style.setProperty('--control-center',`${r.left+r.width/2-h.left}px`);};
 const resize=new ResizeObserver(alignHandle);resize.observe(dock.parentElement);if(tabs)resize.observe(tabs);alignHandle();

 const full=()=>body.classList.contains('monitor');
 const blocked=()=>!dockMayHide({fullscreen:full(),settings:!panel.hidden,dragging:pointers.size>0,hovering,keyboardFocus:keyboard&&dock.contains(doc.activeElement)});
 function state(hidden){body.classList.toggle('controls-tucked',hidden);dock.inert=hidden;handle.textContent='Controls';handle.setAttribute('aria-expanded',String(!hidden));handle.setAttribute('aria-label',hidden?'Show grading controls':'Hide grading controls');handle.title=hidden?'Show controls':'Hide controls';}
 function hide(){clearTimeout(timer);if(!blocked())state(true);}
 function schedule(){clearTimeout(timer);if(!blocked())timer=setTimeout(hide,idleMs);}
 function reveal(){state(false);schedule();}
 handle.onclick=()=>body.classList.contains('controls-tucked')?reveal():dismiss();
 function dismiss(){clearTimeout(timer);hovering=false;state(true);}
 // Only the explicit Controls button opens the popup. Outside interactions dismiss it.
 doc.addEventListener('pointerdown',event=>{keyboard=false;if(handle.contains(event.target))return;if(dock.contains(event.target))pointers.add(event.pointerId);else dismiss();},{capture:true,passive:true});
 const release=event=>{pointers.delete(event.pointerId);schedule();};for(const type of ['pointerup','pointercancel'])doc.addEventListener(type,release,{capture:true,passive:true});
 dock.addEventListener('pointerenter',event=>{if(event.pointerType==='mouse'){hovering=true;reveal();}});dock.addEventListener('pointerleave',()=>{hovering=false;schedule();});
 doc.addEventListener('keydown',event=>{if(event.key==='Tab'||dock.contains(event.target))keyboard=true;if(event.key==='Escape'&&!body.classList.contains('controls-tucked')){dismiss();handle.focus();}});dock.addEventListener('focusin',reveal);dock.addEventListener('focusout',()=>queueMicrotask(schedule));
 // monitor can be set after fullscreenchange; observe the actual layout state.
 const observer=new MutationObserver(records=>{if(records.some(r=>r.target===panel||r.attributeName==='class'&&r.target===body&&r.oldValue?.includes('monitor')!==body.classList.contains('monitor'))){dismiss();}});
 observer.observe(body,{attributes:true,attributeFilter:['class'],attributeOldValue:true});observer.observe(panel,{attributes:true,attributeFilter:['hidden']});state(true);
 return {reveal,hide};
}
