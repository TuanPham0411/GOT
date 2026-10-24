const test=require('node:test');
const assert=require('node:assert/strict');
const Clock=require('../static/js/session-clock.js');
test('one deadline survives changing games and reloading',()=>{
  let now=Date.parse('2026-01-01T00:00:00Z');
  const end='2026-01-01T01:00:00Z';
  const clock=new Clock(end,new Date(now).toISOString(),()=>now);
  assert.equal(clock.remaining(),3600);
  now+=20*60000;
  assert.equal(clock.remaining(),2400);
  // Reopening a game reads the same clock; reloading receives the original expiry.
  const reloaded=new Clock(end,new Date(now).toISOString(),()=>now);
  assert.equal(reloaded.remaining(),2400);
  now+=40*60000;
  assert.equal(clock.remaining(),0);assert.equal(reloaded.remaining(),0);
});
test('server clock offset prevents a slow client clock from granting extra time',()=>{
  let client=0;
  const clock=new Clock('2026-01-01T00:10:00Z','2026-01-01T00:00:00Z',()=>client);
  assert.equal(clock.remaining(),600);
  client+=600001;assert.equal(clock.remaining(),0);
  assert.equal(new Clock('invalid','invalid').remaining(),0);
});
