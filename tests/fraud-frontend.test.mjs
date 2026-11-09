import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
const root=new URL('../mia/mia-fraude/',import.meta.url);
const geometry=await import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('geometry.js',root))).toString('base64'));

test('image coordinates exclude letterboxing and preserve normalized clue hits at any scale',()=>{
  for(const scale of [.4,.8,1,2]) {
    const box={left:25,top:10,width:300*scale,height:300*scale};
    const r=geometry.imageRect(box,900,600);
    assert.equal(r.height,200*scale);
    assert.equal(geometry.imagePoint(25,10,r),null);
    const p=geometry.imagePoint(r.left+r.width*.7,r.top+r.height*.3,r);
    assert(Math.abs(p.x-.7)<1e-9);assert(Math.abs(p.y-.3)<1e-9);
    assert.equal(geometry.imagePoint(r.left+r.width+1,r.top,r),null);
  }
});
test('horizontal intentional swipes only; taps, vertical movements and cancels cannot decide',()=>{
  assert.equal(geometry.swipeDecision(0,0,340),null);
  assert.equal(geometry.swipeDecision(60,0,340),null);
  assert.equal(geometry.swipeDecision(100,120,340),null);
  assert.equal(geometry.swipeDecision(100,20,340),true);
  assert.equal(geometry.swipeDecision(-100,20,340),false);
  assert.equal(geometry.swipeDecision(77,0,300),true);
});

async function apiHarness(fetch) {
  const src=await readFile(new URL('api.js',root),'utf8');
  const sandbox={fetch,AbortController,setTimeout,clearTimeout};vm.createContext(sandbox);
  vm.runInContext(src.replace('export const api =','globalThis.api ='),sandbox);
  return sandbox.api;
}
test('session initialized once, csrf attached to same-origin requests, no client score upload',async()=>{
  const calls=[];
  const api=await apiHarness(async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>url.endsWith('session')?{csrf:'token'}:{ok:true}};});
  await Promise.all([api.post('claim',{tri:'ABC'}),api.post('start',{})]);
  assert.equal(calls.filter(c=>c.url.endsWith('session')).length,1);
  for(const c of calls.filter(c=>c.options.method==='POST')) {
    assert(c.url.startsWith('/fraude/api/'));
    assert.equal(c.options.credentials,'same-origin');assert.equal(c.options.headers['X-CSRF-Token'],'token');
    assert.equal(c.options.cache,'no-store');
  }
});
test('session network failure is retryable; server errors retain codes for appropriate recovery',async()=>{
  let attempts=0;
  const api=await apiHarness(async url=>{
    if(url.endsWith('session')) {if(++attempts===1)throw Error('offline');return {ok:true,json:async()=>({csrf:'new'})};}
    return {ok:false,json:async()=>({error:'taken'})};
  });
  await assert.rejects(api.post('claim',{tri:'ABC'}),e=>e.code==='error');
  await assert.rejects(api.post('claim',{tri:'ABC'}),e=>e.code==='taken');
  assert.equal(attempts,2);
});

test('magnifier keeps clue coordinates correct after zoom and panning',()=>{
  // At ×4, a large part of the document lies outside the visible scroll area.
  const rect=geometry.imageRect({left:-350,top:-640,width:1200,height:1600},900,1200);
  const p=geometry.imagePoint(rect.left+rect.width*.72,rect.top+rect.height*.54,rect);
  assert(Math.abs(p.x-.72)<1e-9);assert(Math.abs(p.y-.54)<1e-9);
});
