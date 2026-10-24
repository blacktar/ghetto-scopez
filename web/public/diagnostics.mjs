import {RELEASE} from './release.mjs';
export function reportClientError(error,phase='page'){
 const message=String(error?.message||error||'Unknown page error');
 document.documentElement.dataset.pageError=message;
 const status=document.getElementById('signalstate');if(status)status.textContent=' · '+phase+' error: '+message;
 const entry={release:RELEASE.version,viewport:[innerWidth,innerHeight,devicePixelRatio],phase,message,stack:String(error?.stack||'').slice(0,2500),agent:navigator.userAgent};
 fetch('/api/client-errors',{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify(entry),keepalive:true}).catch(()=>{});
}
