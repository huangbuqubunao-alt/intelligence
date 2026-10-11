import {chromium} from '../../../frontend/node_modules/playwright-core/index.mjs';
const final=process.env.WAITING_MODEL_FINAL_GUI==='1',base=final?'http://127.0.0.1:5798/':'http://127.0.0.1:5788/';
const c=await chromium.launchPersistentContext('.var/waiting-model-final-fix/'+(final?'gui-final':'gui')+'/chrome-profile',{executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:false,viewport:{width:1440,height:1080}}),p=c.pages()[0];
try{
await p.goto(base+'#Following');await p.waitForLoadState('networkidle');
for(let i=0;i<2;i++)if(await p.getByRole('button',{name:'继续',exact:true}).count())await p.getByRole('button',{name:'继续',exact:true}).click();
if(await p.getByRole('button',{name:'暂时跳过',exact:true}).count())await p.getByRole('button',{name:'暂时跳过',exact:true}).click();
await p.getByRole('button',{name:'添加关注',exact:true}).first().click();await p.locator('input[placeholder*="youtube"]').fill('https://www.youtube.com/watch?v=aircAruvnKk');await p.getByRole('dialog').getByRole('button',{name:'确认导入',exact:true}).click();await p.getByRole('dialog').getByRole('button',{name:'完成',exact:true}).waitFor({timeout:60000});await p.getByRole('dialog').getByRole('button',{name:'完成',exact:true}).click();await p.goto(base+'#Content/aircAruvnKk');await p.getByRole('button',{name:'提炼为洞察',exact:true}).waitFor({timeout:120000});console.log('ready for extraction');
}finally{await p.screenshot({path:'docs/validation/waiting-model-final-fix/'+(final?'final-gui/':'')+'screenshots/02b-youtube-before-extract.png',fullPage:true});console.log((await p.locator('body').innerText()).slice(-3000));await c.close()}
