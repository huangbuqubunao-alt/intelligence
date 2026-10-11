import {chromium} from '../../../../frontend/node_modules/playwright-core/index.mjs';
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
const root='docs/validation/muse-final-audit',base='http://127.0.0.1:5688/';
const ctx=await chromium.launchPersistentContext('.var/muse-final-audit/gui/browser-profile',{executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,viewport:{width:1440,height:1000}});
const page=ctx.pages()[0],requests=[],errors=[];
page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(r.method()==='POST')requests.push({url:r.url(),body:r.postData()})});
try{
await page.goto(base);await page.waitForLoadState('networkidle');
for(let i=0;i<2;i++){if(await page.getByRole('button',{name:'继续',exact:true}).count()){await page.getByRole('button',{name:'继续',exact:true}).click();await page.screenshot({path:`${root}/screenshots/0${i+2}-onboarding.png`});}}
console.log('ONBOARDING',await page.locator('body').innerText());
if(await page.getByRole('button',{name:'添加内容',exact:true}).count())await page.getByRole('button',{name:'添加内容',exact:true}).click();
else if(await page.getByRole('button',{name:'暂时跳过',exact:true}).count())await page.getByRole('button',{name:'暂时跳过',exact:true}).click();
await page.getByRole('button',{name:'关注',exact:true}).click();
console.log('FOLLOWING',await page.locator('body').innerText());
await page.getByRole('button',{name:'添加关注',exact:true}).first().click();
console.log('DIALOG',await page.getByRole('dialog').innerText());
await page.getByRole('button',{name:'导入本地文件',exact:true}).click();
console.log('LOCAL',await page.getByRole('dialog').innerText());
await page.getByRole('button',{name:'选择本地文件',exact:true}).click();
console.log('REAL_APPKIT_PICKER_READY');
await page.getByRole('button',{name:'确认导入',exact:true}).waitFor({timeout:120000});
console.log('SELECTED',await page.getByRole('dialog').innerText());
await page.screenshot({path:`${root}/screenshots/04-native-selected.png`});
await page.getByRole('button',{name:'确认导入',exact:true}).click();
await page.waitForURL(/#Content\//,{timeout:60000});
await page.getByRole('heading',{name:'audit-note.txt',exact:true}).waitFor();
await page.waitForTimeout(500);
assert.ok((await page.locator('body').innerText()).includes('文件已导入'));
await page.screenshot({path:`${root}/screenshots/05-local-content.png`});
const saved=page.url();await page.reload();await page.getByRole('heading',{name:'audit-note.txt',exact:true}).waitFor();
await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('heading',{name:'设置',exact:true}).waitFor();
await page.goBack();await page.getByRole('heading',{name:'audit-note.txt',exact:true}).waitFor();await page.goForward();await page.getByRole('heading',{name:'设置',exact:true}).waitFor();
await page.screenshot({path:`${root}/screenshots/06-settings-zh.png`});
assert.ok(requests.every(r=>!r.url.includes('/local/imports')));
console.log('CONTENT_BACK_FORWARD_REFRESH_PASS',saved);
writeFileSync(`${root}/gui-native.json`,JSON.stringify({realMacOS:true,realAppKit:true,saved,requests,errors,contentBackForwardRefresh:true},null,2));
console.log('SETTINGS',await page.locator('body').innerText());
}finally{await ctx.close()}
