import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {chromium} from '../../../frontend/node_modules/playwright-core/index.mjs';
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const output=new URL('.',import.meta.url).pathname, results=[];
try {
 for(const language of ['en','zh-CN']) {
  const page=await browser.newPage({viewport:{width:320,height:1000}}), mutations=[], errors=[];
  await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
  await page.route('**/*',async route=>{
   if(route.request().method()!=='GET') {mutations.push(route.request().method());await route.abort();}
   else await route.continue();
  });
  page.on('pageerror',error=>errors.push(String(error)));
  await page.goto('http://127.0.0.1:18968/');
  await page.getByText(language==='en'
   ? 'Open Following to check your saved sources or add something new. Content is organized first; generating Intelligence is optional.'
   : '打开关注，检查已保存的来源或添加新内容。系统先整理内容；是否进一步生成洞察，由你选择。',{exact:true}).waitFor();
  await page.waitForLoadState('networkidle');
  assert.equal(await page.getByText(/You have a Following|你已添加关注|FIRST RUN/).count(),0);
  assert.deepEqual(mutations,[]);assert.deepEqual(errors,[]);
  for(const width of [320,1440]) {
   await page.setViewportSize({width,height:1000});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   await page.screenshot({path:output+`owner-copy-home-${language}-${width}.png`});
   results.push({language,width,truthful_saved_source:true,no_false_tracking_claim:true,no_onboarding_replay:true,GET_only:true,no_overflow:true});
  }
  await page.close();
 }
 writeFileSync(output+'browser-owner-home.json',JSON.stringify({results},null,2));
 console.log('Owner-copy Home bilingual/320px/desktop, truthful legacy source and GET-only validation passed');
} finally {await browser.close();}
