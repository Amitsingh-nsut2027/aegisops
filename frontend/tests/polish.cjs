const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
const page=await browser.newPage({viewport:{width:1280,height:960}});await page.goto('http://127.0.0.1:5173');await page.locator('.event-row').first().waitFor();await page.evaluate(()=>document.fonts.ready);
const result=await page.evaluate(()=>{
  function rgb(value){const m=value.match(/[\d.]+/g);return m?m.slice(0,3).map(Number):null}
  function luminance(c){const v=c.map(x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4});return v[0]*.2126+v[1]*.7152+v[2]*.0722}
  function background(el){for(let p=el;p;p=p.parentElement){const c=getComputedStyle(p).backgroundColor;if(c!=='rgba(0, 0, 0, 0)'&&c!=='transparent')return rgb(c)}return [17,19,19]}
  const checks=[];
  for(const el of document.querySelectorAll('h1,h2,h3,p,span,button,label,code,kbd,th,td,input,select,summary')){
    if(el.closest('[hidden],.sr-only')||el.matches(':disabled')||el.closest(':disabled')||!el.getBoundingClientRect().width)continue;
    if(![...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&!el.matches('input,select'))continue;
    const css=getComputedStyle(el);const fg=rgb(css.color),bg=background(el);if(!fg||!bg)continue;
    const l=[luminance(fg),luminance(bg)].sort((a,b)=>b-a);const ratio=(l[0]+.05)/(l[1]+.05);
    checks.push({text:(el.textContent||el.placeholder||'input').trim().slice(0,60),ratio:Number(ratio.toFixed(2)),pass:ratio>=4.5});
  }
  return {contrast:checks,fontFaces:[...document.fonts].map(f=>({family:f.family,status:f.status})),bodyFont:getComputedStyle(document.querySelector('h1')).fontFamily,dataFont:getComputedStyle(document.querySelector('.row-select')).fontFamily,alignments:{toolbar:document.querySelector('.table-toolbar').getBoundingClientRect().left,heading:document.querySelector('.page-heading').getBoundingClientRect().left+parseInt(getComputedStyle(document.querySelector('.page-heading')).paddingLeft),observation:document.querySelector('.observation').getBoundingClientRect().left+parseInt(getComputedStyle(document.querySelector('.observation')).paddingLeft)}};
});
assert.equal(result.contrast.filter(c=>!c.pass).length,0,JSON.stringify(result.contrast.filter(c=>!c.pass)));
assert.equal(result.alignments.toolbar,result.alignments.heading);assert.equal(result.alignments.toolbar,result.alignments.observation);
const states=[];
for(const selector of ['.refresh-button','.copy-button','#tab-trace','.row-select','.command-trigger']){
  const el=page.locator(selector).first();await el.hover();const hover=await el.evaluate(el=>({color:getComputedStyle(el).color,background:getComputedStyle(el).backgroundColor}));
  await page.keyboard.press('Tab');await el.focus();
  const focus=await el.evaluate(el=>({outline:getComputedStyle(el).outlineStyle,width:getComputedStyle(el).outlineWidth}));
  assert.equal(focus.outline,'solid',selector+' focus outline');assert.equal(focus.width,'2px',selector+' focus width');
  await el.hover();await page.mouse.down();const active=await el.evaluate(el=>getComputedStyle(el).backgroundColor);await page.mouse.move(0,0);await page.mouse.up();
  states.push({selector,hover,focus,active});
}
assert.equal(await page.getByRole('button',{name:'Next event page'}).isDisabled(),true);
await page.locator('.event-row').first().click();await page.getByRole('tab',{name:'Evidence',exact:true}).click();
const options=await page.locator('#run-select option').count();if(options>1){const value=await page.locator('#run-select option').last().getAttribute('value');await page.locator('#run-select').selectOption(value);assert.equal(await page.locator('#run-select').inputValue(),value);await page.locator('#run-select').selectOption({index:0});}
await page.route('**/api/events?**',route=>route.fulfill({status:503,json:{detail:'offline'}}));await page.getByRole('button',{name:/Refresh/}).click();await page.getByText('Snapshot is stale',{exact:true}).waitFor();assert.equal(await page.locator('.event-row').count(),4);await page.screenshot({path:'docs/design/review/13-stale-snapshot.png',fullPage:true});
await page.unroute('**/api/events?**');
result.controls=states;result.disabledPagination=true;result.savedRunSelection=true;result.staleSnapshotRetained=true;result.scope='Screen-one polish. Token contrast does not by itself establish full WCAG conformance.';
fs.writeFileSync('docs/design/review/polish-audit.json',JSON.stringify(result,null,2));
console.log(`PASS ${result.contrast.length} rendered text contrast checks, alignment anchors, control-state samples, saved-run selection and stale-data retention.`);
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
