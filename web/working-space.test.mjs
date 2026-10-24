import test from 'node:test';
import assert from 'node:assert/strict';
import {signalSpec,decodeSample} from './public/signal.mjs';
import {inputPacket,decodeInput} from './resolve-input.mjs';
import {analyzeFrame} from './scopes.mjs';
import {analyzeFrame as reference} from './scopes-reference.mjs';
import {scopePacket,unpackScope} from './public/scope-wire.mjs';
import {snapshotCompatibility,captureSnapshot} from './public/snapshots.mjs';
const signal=()=>signalSpec({model:'RGB',range:'full',matrix:'bt709',codeBits:10,domain:'working',primaries:'unknown',transfer:'unknown'});
const frame=data=>({width:data.length/3,height:1,data,signal:signal(),producer:'resolve-ofx',instanceId:'working-tap-test',time:1,renderScale:{x:1,y:1}});
test('working tap transports original float32 bits including excursions, signed zero, NaN payloads and subnormals',()=>{
 const words=Uint32Array.of(0x80000000,0,1,0x7fc01234,0x7f800000,0xff800000,0xbe800000,0x40800000,0x3f000001);
 const f=frame(new Float32Array(words.buffer)),got=decodeInput(inputPacket(f).buffer);
 assert.deepEqual(new Uint32Array(got.data.buffer,got.data.byteOffset,got.data.length),words);
 assert.equal(got.signal.domain,'working');assert.equal(got.signal.primaries,'unknown');
 assert.equal(got.signal.representation,'raw float');
 assert.deepEqual(decodeSample(-.25,4,.5,got.signal),[-.25,4,.5]);
});
test('working tap rejects implicit signal interpretations and range decoding',()=>{
 for(const patch of [{model:'YCbCr'},{range:'video'},{matrix:'bt2020-ncl'},{primaries:'bt709'},{transfer:'bt709'},{representation:'code/maxCode'}])assert.throws(()=>signalSpec({...signal(),...patch}));
});
test('working measurements retain raw extrema and numeric bins; reference and native CPU agree',()=>{
 const f=frame(Float32Array.of(-.25,4,.5,0,0,0,1,1,1,.5,.5,.5)),c={min:-1,max:4,bits:10,activeScopes:[0,1,2,3,4,5,6,7,8,9,10]};
 const a=analyzeFrame(f,c),b=reference(f,c);
 for(const name of ['wave','parade','hist','vector','low','mid','high','twin'])assert.deepEqual(a[name],b[name],name);
 assert.equal(a.stats[0].min,-.25);assert.equal(a.stats[1].max,4);assert.equal(a.stats[3].name,'Weighted RGB');
 assert.equal(a.hist.reduce((a,b)=>a+b,0),12);assert.equal(a.targets.length,0);
 const out=unpackScope(scopePacket(a,1,1).buffer);assert.equal(out.source.signal.domain,'working');assert.match(out.measurement.domain,/raw working-space/);assert.deepEqual(out.targets,[]);
 const encoded={...a,source:{...a.source,signal:{...a.source.signal,domain:'encoded'}}};assert.equal(snapshotCompatibility(captureSnapshot(a,3).data,encoded),false);
});
