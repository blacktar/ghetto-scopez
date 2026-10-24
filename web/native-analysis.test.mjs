import test from 'node:test';import assert from 'node:assert/strict';
import {analyzeFrame,makeFixture,KINDS} from './scopes.mjs';import {analyzeFrame as reference} from './scopes-reference.mjs';import {nativeRGB,nativeCRC} from './native-analysis.mjs';import {crc32} from './public/protocol.mjs';import {FIELDS} from './public/scope-wire.mjs';
function same(f,c){const expected=reference(f,c),actual=analyzeFrame(f,c);for(const name of FIELDS.filter(name=>name!=='cube')){if(!c.activeScopes||c.activeScopes.includes(FIELDS.indexOf(name)))assert.deepEqual(actual[name],expected[name],name);else assert.equal(actual[name].some(Boolean),false);}for(const name of ['stats','rawStats','splitStats','twinStats','vectorOutside','clipped','samples'])assert.deepEqual(actual[name],expected[name],name);return actual;}
test('native CPU kernel is available and matches independent JS counts, stats and excursions for every fixture',()=>{assert.ok(nativeRGB,'Build native kernel before running this test');for(const kind of KINDS)for(const bits of [10,12])for(const matrix of ['bt709','bt2020-ncl'])same(makeFixture(kind,.37,4,{model:'RGB',range:'full',matrix,codeBits:12}),{bits});});
test('native parallel selected scopes preserve every pixel and exact bin edge decisions, including nonfinite and signed zero',()=>{const width=1024,height=384,data=new Float32Array(width*height*3);let seed=42;for(let i=0;i<data.length;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;data[i]=(seed/2**32)*1.5-.25;}data.set([-0,0,-0,NaN,Infinity,-Infinity]);const f={width,height,data,signal:{model:'RGB',range:'full',matrix:'bt709',codeBits:10}};for(const c of [{bits:12,activeScopes:[4,5,6,7]},{bits:10,vectorZoom:2,twinZoom:2,activeScopes:[3,7]},{bits:12,min:-.125,max:1.125,x0:13,x1:997,y0:7,y1:383,activeScopes:[0,1,2,4,7]}])same(f,c);const small={...f,width:6,height:1,data:new Float32Array([-0,-0,-0,0,0,0,1,1,1,NaN,0,0,Infinity,-Infinity,0,.5,.5,.5])};same(small,{bits:12});});
test('native CRC32 matches JS for edge lengths and unaligned slices',()=>{assert.ok(nativeCRC);for(const n of [0,1,31,32,4096,100001]){const b=Uint8Array.from({length:n+7},(_,i)=>(i*71)&255).subarray(3,n+3);assert.equal(nativeCRC(b),crc32(b));}});

test('3x magnification preserves exact native/independent JS vector bins and statistics',()=>{for(const matrix of ['bt709','bt2020-ncl'])for(const kind of ['sine','tonal-casts','excursions','impulse'])same(makeFixture(kind,.37,4,{model:'RGB',range:'full',matrix,codeBits:12}),{bits:12,vectorZoom:3});});

test('SIMD default layout preserves signed zeros, subnormals, odd row tails, excursions and viewport statistics',()=>{
 const width=257,height=7,data=new Float32Array(width*height*3);let seed=19;
 for(let i=0;i<data.length;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;data[i]=seed/2**32;}
 data.set([-0,-0,-0,0,0,0,1e-45,-1e-45,0,NaN,Infinity,-Infinity,-.125,1.125,.5],(width-5)*3);
 for(const matrix of ['bt709','bt2020-ncl'])for(const vectorDisplayScale of [1,4])for(const range of [[0,1],[.125,.875],[-.125,1.125]]){
  const f={width,height,data,signal:{model:'RGB',range:'full',matrix,codeBits:10}};
  same(f,{activeScopes:[4,5,6,7],vectorDisplayScale,min:range[0],max:range[1],x0:2,x1:255,y0:1,y1:7});
 }
});
