import {chromium} from '../../../../frontend/node_modules/playwright-core/index.mjs';
import {writeFileSync} from 'node:fs';
const root='docs/validation/muse-final-audit',base='http://127.0.0.1:5688/';const context=await chromium.launchPersistentContext('.var/muse-final-audit/gui/youtube-profile',{executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,viewport:{width:1440,height:1200}});const page=context.pages()[0];const results=[],responses=[];page.on('response',async r=>{if(r.url().includes('/sources/resolve')||r.url().includes('/sources/')){try{responses.push({url:r.url(),status:r.status(),body:await r.json()})}catch{}}});
try{
await page.goto(base);await page.waitForLoadState('networkidle');if(await page.getByRole('button',{name:'暂时跳过',exact:true}).count())await page.getByRole('button',{name:'暂时跳过',exact:true}).click();
for(const [kind,url] of [['video','https://www.youtube.com/watch?v=aircAruvnKk'],['channel','https://www.youtube.com/@Veritasium']]){
 try{
 await page.goto(base+'#Following');await page.getByRole('button',{name:'添加关注',exact:true}).first().click();await page.locator('input[placeholder*="youtube"]').fill(url);await page.waitForTimeout(1200);await page.screenshot({path:root+`/screenshots/16-youtube-${kind}-dialog.png`});
 console.log(kind,'RECOGNITION',await page.getByRole('dialog').innerText());
 await page.getByRole('dialog').getByRole('button',{name:kind==='channel'?'关注频道':'确认导入',exact:true}).click({timeout:15000});await page.waitForTimeout(1500);
 await page.getByRole('dialog').getByRole('button',{name:'完成',exact:true}).waitFor({timeout:60000});await page.screenshot({path:root+`/screenshots/17-youtube-${kind}-success.png`});await page.getByRole('dialog').getByRole('button',{name:'完成',exact:true}).click();results.push({kind,confirmed:true,url:page.url(),body:(await page.locator('body').innerText()).slice(0,9000)});await page.screenshot({path:root+`/screenshots/17-youtube-${kind}-added.png`,fullPage:true});
 }catch(e){results.push({kind,confirmed:false,error:String(e),body:(await page.locator('body').innerText()).slice(0,9000)});await page.screenshot({path:root+`/screenshots/17-youtube-${kind}-blocked.png`,fullPage:true});const close=page.getByRole('dialog').getByRole('button',{name:/关闭|完成/,exact:true});if(await close.count())await close.first().click();await page.goto(base+'#Following');}
}
if(await page.getByRole('button',{name:'暂停关注',exact:true}).count()){
 await page.getByRole('button',{name:'暂停关注',exact:true}).first().click();await page.getByRole('button',{name:'持续关注',exact:true}).first().waitFor();await page.screenshot({path:root+'/screenshots/18-following-paused.png'});await page.getByRole('button',{name:'持续关注',exact:true}).first().click();await page.getByRole('button',{name:'暂停关注',exact:true}).first().waitFor();results.push({pauseResume:true});await page.screenshot({path:root+'/screenshots/19-following-resumed.png'});
}
await page.getByRole('button',{name:'内容',exact:true}).click();await page.getByRole('heading',{name:'内容',exact:true}).waitFor();await page.waitForTimeout(500);await page.screenshot({path:root+'/screenshots/20-content-list.png',fullPage:true});console.log('CONTENT',await page.locator('body').innerText());
writeFileSync(root+'/gui-youtube.json',JSON.stringify({results,responses},null,2)+'\n');
}finally{writeFileSync(root+'/gui-youtube.json',JSON.stringify({results,responses},null,2)+'\n');await context.close()}
