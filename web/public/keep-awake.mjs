// Native Screen Wake Lock where available; NoSleep video fallback for LAN HTTP.
// The first enable is called synchronously by a user tap, as Safari requires.
export function createKeepAwake({doc=document,makeFallback=()=>new globalThis.NoSleep(),native=globalThis.navigator?.wakeLock,onState=()=>{}}={}){
 let wanted=false,sentinel=null,fallback=null,busy=null,epoch=0,state='off';const notify=value=>{state=value;onState(value);};
 async function release(){const old=sentinel;sentinel=null;if(old)try{await old.release();}catch{}fallback?.disable();notify('off');}
 function enable(){if(!wanted||doc.visibilityState!=='visible'||busy||sentinel||fallback?.isEnabled)return busy;const current=epoch;
 // Call enable/play before returning from the initiating gesture.
 let attempt;try{attempt=native?native.request('screen'):(fallback??=makeFallback()).enable();}catch(error){notify('unavailable');return Promise.resolve();}
 busy=Promise.resolve(attempt).then(async lock=>{if(current!==epoch||!wanted||doc.visibilityState!=='visible'){if(lock?.release)await lock.release();else fallback?.disable();return;}if(native){sentinel=lock;lock.addEventListener('release',()=>{if(sentinel===lock){sentinel=null;notify(wanted?'released':'off');}});}notify(native?'native':'video');}).catch(()=>notify('unavailable')).finally(()=>{busy=null;});return busy;
 }
 const visibility=()=>{if(doc.visibilityState==='visible'){if(wanted)enable();}else{epoch++;void release();}};doc.addEventListener('visibilitychange',visibility);
 return {set(value){wanted=Boolean(value);if(wanted)return enable();epoch++;return release();},retry(){return enable();},get state(){return state;},destroy(){wanted=false;epoch++;doc.removeEventListener('visibilitychange',visibility);return release();}};
}
