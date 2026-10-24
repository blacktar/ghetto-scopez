import test from 'node:test';import assert from 'node:assert/strict';import {renderSoftware} from './public/software-renderer.mjs';import {analyzeFrame,makeFixture} from './scopes.mjs';import {FIELDS} from './public/scope-wire.mjs';import {createHash} from 'node:crypto';
const digest=d=>createHash('sha256').update(Buffer.concat(FIELDS.map(k=>Buffer.from(d[k].buffer,d[k].byteOffset,d[k].byteLength)))).digest('hex');
test('software presentation covers every scope without changing original counts, including smoothing and gain',()=>{const d=analyzeFrame(makeFixture('sine',.37),{bits:10}),before=digest(d);for(const scope of [0,1,2,3,4,5,6,7,8]){const a=renderSoftware(d,scope,127,63,{gain:4,brightness:50,smooth:true},{vectorColour:true,twinColour:true,twinHorizontal:true});assert.equal(a.length,127*63*4);assert.ok(a.some((v,i)=>i%4!==3&&v>30));for(let i=3;i<a.length;i+=4)assert.equal(a[i],255);}assert.equal(digest(d),before);});
test('software DoubleD horizontal image is the exact counterclockwise rotation of its vertical image',()=>{const d=analyzeFrame(makeFixture('tonal-casts'),{bits:10}),style={gain:1,brightness:100,smooth:true};const v=renderSoftware(d,7,64,128,style,{twinHorizontal:false,twinColour:true}),h=renderSoftware(d,7,128,64,style,{twinHorizontal:true,twinColour:true});for(let y=0;y<128;y++)for(let x=0;x<64;x++)for(let c=0;c<4;c++)assert.equal(h[((63-x)*128+y)*4+c],v[(y*64+x)*4+c]);});

test('usable smoothing conserves interior density, spreads fine traces and reduces spatial noise',async()=>{
 const {smoothDensity}=await import('./public/trace-style.mjs');const w=31,h=31,a=new Float64Array(w*h);a[15*w+15]=100;const b=smoothDensity(a,w,h);
 assert.ok(Math.abs(b.reduce((x,y)=>x+y,0)-100)<1e-10);assert.ok(b[15*w+15]>=25);assert.ok(b[15*w+18]>0);assert.equal(b[15*w+19],0);assert.equal(a[15*w+15],100);
 const noise=Float64Array.from({length:w*h},(_,i)=>((i%w+Math.floor(i/w))%2)*100);const filtered=smoothDensity(noise,w,h);let before=0,after=0;for(let y=4;y<h-4;y++)for(let x=4;x<w-4;x++){before+=(noise[y*w+x]-50)**2;after+=(filtered[y*w+x]-50)**2;}assert.ok(after<before*.1);
});

test('individual histograms display only their selected channel without modifying counts',()=>{const d=analyzeFrame(makeFixture('tonal-casts'),{bits:12}),before=digest(d);for(const scope of [10,11,12]){const original=renderSoftware(d,scope,150,90);const hist=d.hist.slice();for(let ch=0;ch<3;ch++)if(ch!==scope-10)hist.fill(0,ch*4096,(ch+1)*4096);assert.deepEqual(renderSoftware({...d,hist},scope,150,90),original);assert.ok(original.some((v,i)=>i%4!==3&&v>40));}assert.equal(digest(d),before);});

test('trace rasters contain no baked diamonds or guide grid when the signal is empty',()=>{const d=analyzeFrame(makeFixture('ramp'),{bits:10});for(const field of FIELDS)d[field]=new Uint32Array(d[field].length);for(const scope of [0,1,2,3,4,5,6,7,8,10,11,12]){const image=renderSoftware(d,scope,160,96);for(let i=0;i<image.length;i+=4){assert.equal(image[i],9,`scope ${scope} raster has baked decoration`);assert.equal(image[i+1],9);assert.equal(image[i+2],9);}}});

test('rectangular vectorscope retains equal axis scale and magnified traces beyond former square boundary',()=>{
 const d=analyzeFrame(makeFixture('ramp'),{bits:10});d.vector.fill(0);const n=d.config.vectorSize;
 // Chroma x=+0.2 moves outside the old centred square at 4x, inside a wide card.
 const x=Math.round(.7*(n-1)),y=Math.round(.5*(n-1));d.vector[y*n+x]=10000;
 const wide=renderSoftware(d,3,400,100,undefined,{vectorMagnification:4});let xs=[],ys=[];
 for(let j=0;j<100;j++)for(let i=0;i<400;i++)if(wide[(j*400+i)*4]>20){xs.push(i);ys.push(j);}
 assert.ok(xs.length);assert.ok(Math.min(...xs)>250,'trace must cross former square edge');assert.ok(Math.max(...xs)<400);assert.ok(Math.abs((Math.min(...ys)+Math.max(...ys))/2-49.5)<2);
 const tall=renderSoftware(d,3,100,400,undefined,{vectorMagnification:1});const neutral=renderSoftware({...d,vector:new Uint32Array(n*n)},3,100,400);assert.ok(tall.some((v,i)=>v>neutral[i]));
});
