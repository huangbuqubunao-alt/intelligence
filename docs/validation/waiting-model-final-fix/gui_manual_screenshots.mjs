import {chromium} from '../../../frontend/node_modules/playwright-core/index.mjs';
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
const final=process.env.WAITING_MODEL_FINAL_GUI==='1';
const root='docs/validation/waiting-model-final-fix'+(final?'/final-gui':''),base=final?'http://127.0.0.1:5798/':'http://127.0.0.1:5788/';
const c=await chromium.launchPersistentContext('.var/waiting-model-final-fix/'+(final?'gui-final':'gui')+'/chrome-profile',{executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:false,viewport:{width:1440,height:1080}}),p=c.pages()[0];
try{
await p.goto(base+'#Content/aircAruvnKk');const panel=p.locator('.panel').filter({has:p.getByRole('heading',{name:'洞察处理结果',exact:true})});
await p.getByText('本次提炼已取消，没有生成洞察。原 Content、字幕、摘要和 Evidence 均保留。',{exact:true}).waitFor();await panel.screenshot({path:root+'/screenshots/10c-restored-cancelled-panel.png'});
await p.getByRole('button',{name:'提炼为洞察',exact:true}).click();await p.getByText('当前没有合格的洞察模型。',{exact:true}).waitFor();await panel.screenshot({path:root+'/screenshots/03c-waiting-model-panel.png'});
await p.getByRole('button',{name:'取消本次提炼',exact:true}).click();await p.getByText('本次提炼已取消，没有生成洞察。原 Content、字幕、摘要和 Evidence 均保留。',{exact:true}).waitFor();await panel.screenshot({path:root+'/screenshots/05c-cancelled-panel.png'});
const state=await (await p.request.get(base+'api/v1/backup-restore/status')).json();assert.equal(state.status.ready,true);writeFileSync(root+'/gui-manual-screenshots.json',JSON.stringify({headless:false,macOS:process.platform==='darwin',ready:state.status.ready,passed:true},null,2));
}finally{await c.close()}
