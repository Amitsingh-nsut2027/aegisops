import test from 'node:test';
import assert from 'node:assert/strict';
import {createDataClient} from '../data-client.js';

const fixture = {kind:'aegisops-portfolio-v1', events:[
  {event_id:'a'.repeat(64),source:'simulator',received_at:'2026-10-18T00:00:00Z'},
  {event_id:'b'.repeat(64),source:'simulator',received_at:'2026-10-19T00:00:00Z'},
], runs:Array.from({length:26},(_,i)=>({run_id:i.toString(16).padStart(32,'0'),event_id:(i%2?'a':'b').repeat(64),started_at:`2026-10-19T00:${String(i).padStart(2,'0')}:00Z`}))};
test('portfolio requests use only one static fixture fetch, never /api or AWS',async()=>{
  const paths=[];const api=createDataClient({mode:'portfolio',fetcher:async path=>{paths.push(path);return {ok:true,json:async()=>fixture}}});
  const [events,runs]=await Promise.all([api('/events?limit=25'),api('/investigations?limit=25')]);
  assert.deepEqual(paths,['/demo-data.json']);assert.equal(events.items[0].event_id,'b'.repeat(64));assert.equal(runs.items.length,25);assert.equal(runs.has_more,true);
  assert.equal((await api('/investigations?limit=25&offset=25')).returned,1);
});
test('exact history filter, detail identity, missing rows and invalid pages',async()=>{
  const api=createDataClient({mode:'portfolio',fetcher:async()=>({ok:true,json:async()=>fixture})});
  const page=await api('/investigations?event_id='+'a'.repeat(64));assert.equal(page.returned,13);
  const detail=await api('/investigations/'+fixture.runs[0].run_id);assert.equal(detail.run_id,fixture.runs[0].run_id);
  detail.event_id='changed';assert.notEqual((await api('/investigations/'+detail.run_id)).event_id,'changed');
  await assert.rejects(api('/events/'+'0'.repeat(64)),{status:404});
  await assert.rejects(api('/events?limit=0'),{status:422});await assert.rejects(api('/events?offset=-1'),{status:422});
  assert.equal((await api('/events?source=unknown')).returned,0);
});
test('failed static fetch retries rather than caching a failed promise',async()=>{
  let calls=0;const api=createDataClient({mode:'portfolio',fetcher:async()=>++calls===1?{ok:false,status:503}:{ok:true,json:async()=>fixture}});
  await assert.rejects(api('/events'),{status:503});assert.equal((await api('/events')).returned,2);
});
test('local mode retains JWT bridge behavior and error status',async()=>{
  let path;const api=createDataClient({mode:'local',fetcher:async value=>{path=value;return {ok:false,status:401}}});
  await assert.rejects(api('/events?limit=25'),{status:401});assert.equal(path,'/api/events?limit=25');
  assert.throws(()=>createDataClient({mode:'other'}));
});
