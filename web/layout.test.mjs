import test from 'node:test';import assert from 'node:assert/strict';
import {arrangeLayout,LAYOUT_MODES} from './public/layout.mjs';
const tracks=s=>s.startsWith('repeat(')?Number(s.match(/^repeat\((\d+)/)[1]):s.match(/minmax/g).length;
test('all arrangements fill occupied screen tracks without gaps or overlapping scopes',()=>{
 for(let mask=0;mask<16;mask++)for(const mode of LAYOUT_MODES)for(const share of [20,40,80]){
  const layout=[4,5,6,7].map((x,i)=>mask&(1<<i)?x:-1),g=arrangeLayout(layout,mode,share),w=tracks(g.columns),h=tracks(g.rows),cells=new Uint8Array(w*h);
  assert.equal(Object.keys(g.positions).length,mode==='two'?Math.min(2,layout.filter(x=>x>=0).length):mode==='single'?Math.min(1,layout.filter(x=>x>=0).length):layout.filter(x=>x>=0).length);
  for(const [slot,p]of Object.entries(g.positions)){assert.ok(['single','two'].includes(mode)?layout.some(v=>v>=0):layout[slot]>=0);const xs=p.column==='1 / -1'?[0,w]:[Number(p.column)-1,Number(p.column)],ys=p.row==='1 / -1'?[0,h]:[Number(p.row)-1,Number(p.row)];for(let y=ys[0];y<ys[1];y++)for(let x=xs[0];x<xs[1];x++){assert.ok(x>=0&&x<w&&y>=0&&y<h);cells[y*w+x]++;}}
  if(mask)assert.ok(cells.every(v=>v===1),`${mode} mask ${mask} share ${share}`);
 }
});

test('vertical vector stacks place highs above mids above lows and collapse empty slots',()=>{for(const mode of ['left','right','column']){const g=arrangeLayout([4,5,6,7],mode);assert.equal(g.positions[2].row,'1');assert.equal(g.positions[1].row,'2');assert.equal(g.positions[0].row,'3');const two=arrangeLayout([4,-1,6,7],mode);assert.equal(two.positions[2].row,'1');assert.equal(two.positions[0].row,'2');}assert.equal(arrangeLayout([4,5,6,7],'top').positions[0].column,'1');});

test('separate histogram can coexist with overlay and shares its exact analysis plane',async()=>{
 const {validLayout,assignSlot,analysisScopes,SCOPE_NAMES}=await import('./public/layout.mjs');
 assert.equal(SCOPE_NAMES[8],'RGB histogram · Separate');assert.ok(validLayout([2,8,6,7]));
 assert.deepEqual(assignSlot([4,5,6,7],0,8),[8,5,6,7]);assert.deepEqual(analysisScopes([8,-1,-1,-1]),[2]);assert.deepEqual(analysisScopes([2,8,6,7]),[2,6,7]);
 const {analyzeFrame,makeFixture}=await import('./scopes.mjs');const source=makeFixture('tonal-casts');
 const full=analyzeFrame(source,{bits:12});const selected=analyzeFrame(source,{bits:12,activeScopes:analysisScopes([8,-1,-1,-1])});
 assert.deepEqual(selected.hist,full.hist);assert.equal(selected.hist.length,3*4096);assert.equal(selected.samples,full.samples);
});

test('High Mid Low strip occupies one slot and requests original split planes once',async()=>{const {assignSlot,analysisScopes,validLayout}=await import('./public/layout.mjs');assert.deepEqual(assignSlot([4,5,6,7],0,9),[9,-1,-1,7]);assert.ok(validLayout([9,8,-1,7]));assert.deepEqual(analysisScopes([9,8,-1,7]),[2,4,5,6,7]);assert.deepEqual(assignSlot([9,8,-1,7],2,4),[-1,8,4,7]);for(const mode of LAYOUT_MODES){const g=arrangeLayout([9,8,-1,7],mode);assert.equal(Object.keys(g.positions).length,mode==='single'?1:mode==='two'?2:3);}});

test('individual RGB histograms are independently selectable and share exact analysis',async()=>{const {validLayout,analysisScopes,assignSlot}=await import('./public/layout.mjs');assert.ok(validLayout([10,11,12,8]));assert.deepEqual(analysisScopes([10,11,12,8]),[2]);assert.deepEqual(assignSlot([4,5,6,7],0,10),[10,5,6,7]);});

test('single scope keeps OG or main or first occupied scope in a full panel',async()=>{const {singleLayout}=await import('./public/layout.mjs');assert.deepEqual(singleLayout([4,5,6,7]),[-1,-1,-1,7]);assert.deepEqual(singleLayout([16,5,6,7]),[-1,-1,-1,16]);assert.deepEqual(singleLayout([4,-1,-1,-1]),[-1,-1,-1,4]);assert.deepEqual(singleLayout([-1,-1,-1,-1]),[-1,-1,-1,-1]);assert.deepEqual(arrangeLayout([4,5,6,7],'single').positions,{3:{column:'1',row:'1'}});});

test('two scopes are equal-width side by side and retain OG',async()=>{const {twoLayout}=await import('./public/layout.mjs');assert.deepEqual(twoLayout([4,5,6,7]),[4,-1,-1,7]);assert.deepEqual(twoLayout([4,16,6,7]),[16,-1,-1,7]);assert.deepEqual(twoLayout([-1,-1,-1,16]),[-1,-1,-1,16]);const g=arrangeLayout([4,5,6,7],'two');assert.equal(g.columns,'repeat(2,minmax(0,1fr))');assert.equal(g.rows,'minmax(0,1fr)');assert.deepEqual(g.positions,{0:{column:'1',row:'1'},3:{column:'2',row:'1'}});});
