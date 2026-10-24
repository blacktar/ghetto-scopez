import test from 'node:test';import assert from 'node:assert/strict';import {spawn,execFile} from 'node:child_process';import {once} from 'node:events';import {promisify} from 'node:util';import {WebSocket} from 'ws';
const execute=promisify(execFile);
test('GTap UI status reports device names, listening/stopped, URLs, disconnect and offline',{timeout:15000},async()=>{
 await execute('xcrun',['clang++','-std=c++17','-O2','../ofx/tap-info-test.cpp','-o','../build/tap-info-test']);
 const child=spawn(process.execPath,['server.mjs'],{env:{...process.env,SCOPE_DIAGNOSTICS:'1',PORT:'18766',HOST:'127.0.0.1'},stdio:['ignore','pipe','pipe']});let ws;
 try{await once(child.stdout,'data');const url='http://127.0.0.1:18766/api/tap-info';
 const initial=await(await fetch(url)).text();assert.match(initial,/Scopes host: connected/);assert.match(initial,/localhost:18766\/scopes.html/);assert.match(initial,/Viewers: 0/);
 assert.equal((await fetch(url,{headers:{Origin:'http://evil.invalid'}})).status,403);
 ws=new WebSocket('ws://127.0.0.1:18766');await once(ws,'open');let next=once(ws,'message');ws.send(JSON.stringify({type:'identify',label:'Test iPad'}));await next;
 assert.match(await(await fetch(url)).text(),/Test iPad: connected, stopped/);
 next=once(ws,'message');ws.send(JSON.stringify({type:'scopes',mode:'ramp',config:{activeScopes:[4]}}));await next;
 const online=await execute('../build/tap-info-test',['18766']);assert.match(online.stdout,/Test iPad: listening \(ramp\)/);
 next=once(ws,'message');ws.send(JSON.stringify({type:'stop'}));while(true){const [data,binary]=await next;if(!binary&&JSON.parse(data).type==='stopped')break;next=once(ws,'message');}
 assert.match(await(await fetch(url)).text(),/Test iPad: connected, stopped/);ws.close();await once(ws,'close');let disconnected='';for(let i=0;i<30;i++){disconnected=await(await fetch(url)).text();if(/Viewers: 0/.test(disconnected))break;await new Promise(r=>setTimeout(r,10));}assert.match(disconnected,/Viewers: 0/);
 }finally{ws?.terminate();child.kill();await once(child,'exit');}
 const before=performance.now(),offline=await execute('../build/tap-info-test',['18766']);assert.match(offline.stdout,/host: unavailable/);assert.ok(performance.now()-before<1000);
});
