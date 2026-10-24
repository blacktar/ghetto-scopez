import test from 'node:test';import assert from 'node:assert/strict';import {spawn} from 'node:child_process';import {once} from 'node:events';import {WebSocket} from 'ws';import {inputPacket} from './resolve-input.mjs';import {makeFixture,analyzeFrame} from './scopes.mjs';import {scopePacket,unpackScope} from './public/scope-wire.mjs';
test('normal server streams exact Resolve frames with diagnostics disabled', {timeout:15000}, async()=>{
 const port=18774,base=`http://127.0.0.1:${port}`,child=spawn(process.execPath,['server.mjs'],{env:{...process.env,SCOPE_DIAGNOSTICS:'0',HOST:'127.0.0.1',PORT:String(port)},stdio:['ignore','pipe','pipe']});let ws;
 try{await once(child.stdout,'data');for(const route of ['/api/results','/api/resolve/status','/api/resolve/snapshot'])assert.equal((await fetch(base+route)).status,404);
 ws=new WebSocket(`ws://127.0.0.1:${port}`);await once(ws,'open');const frames=[];ws.on('message',(b,binary)=>{if(binary){const frame=unpackScope(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength));frames.push(frame);ws.send(JSON.stringify({type:'scope_ack',generation:frame.generation,seq:frame.seq}));}});ws.send(JSON.stringify({type:'scopes',mode:'resolve',config:{activeScopes:[4,5,6,7]}}));
 const source={...makeFixture('tonal-casts',0,4),producer:'resolve-ofx',instanceId:'production-test',time:1,renderScale:{x:1,y:1}};
 assert.equal((await fetch(base+'/api/resolve/input',{method:'POST',body:inputPacket(source,1)})).status,202);
 for(let i=0;i<100&&!frames.length;i++)await new Promise(r=>setTimeout(r,20));assert.equal(frames.length,1);assert.equal(frames[0].samples,source.width*source.height);assert.equal(frames[0].processing.total_ms,undefined);assert.equal(frames[0].source.capture.sequence,1);
 assert.deepEqual((await(await fetch(base+'/api/fps')).json()).reports,[]);
 ws.send(JSON.stringify({type:'viewer_fps',fps:19.5,render_fps:19,elapsed:2,frames:39,draws:38,debug:false,visible:true}));
 let fps;for(let i=0;i<50;i++){fps=await(await fetch(base+'/api/fps')).json();if(fps.reports.length)break;await new Promise(r=>setTimeout(r,10));}
 assert.equal(fps.reports[0].render_fps,19);assert.equal(fps.reports[0].debug,false);assert.equal(fps.source_revision,1);assert.equal((await fetch(base+'/api/results')).status,404);
 ws.send(JSON.stringify({type:'scopes',mode:'resolve',config:{activeScopes:[0],waveColour:true}}));
 const coloured={...makeFixture('sine',.37,128),producer:'resolve-ofx',instanceId:'colour-compression',time:2,renderScale:{x:1,y:1}};
 assert.equal((await fetch(base+'/api/resolve/input',{method:'POST',body:inputPacket(coloured,2)})).status,202);
 for(let i=0;i<150&&!frames.some(f=>f.config.waveColour&&f.source.capture.sequence===2);i++)await new Promise(r=>setTimeout(r,20));
 const actual=frames.find(f=>f.config.waveColour&&f.source.capture.sequence===2),expected=analyzeFrame(coloured,{activeScopes:[0],waveColour:true});assert.ok(actual);assert.deepEqual(actual.wave,expected.wave);assert.deepEqual(actual.waveColour,unpackScope(scopePacket(expected,0,1).buffer).waveColour);
 const before=(await(await fetch(base+'/api/tap-info')).text());assert.match(before,/Scopes host: connected/);assert.equal((await fetch(base+'/api/client-errors')).status,200);
 }finally{ws?.terminate();child.kill();await once(child,'exit');}
});
