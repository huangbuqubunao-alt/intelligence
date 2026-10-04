import assert from 'node:assert/strict';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright-core';

const base = 'http://127.0.0.1:5611/';
const root = new URL('../.var/phase10b/browser-fixture/', import.meta.url).pathname;
const evidence = new URL('../docs/validation/phase10b/', import.meta.url).pathname;
const info = JSON.parse(readFileSync(join(root, 'fixture.json')));
const offline = process.env.YIA_PHASE10B_OFFLINE === '1';
const screenshots = join(root, 'screenshots'); mkdirSync(screenshots, { recursive: true });
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true,
  args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'] });
const errors = [], external = [], scenarios = [];
const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
try {
  for (const language of ['zh-CN', 'en']) for (const width of [320, 768, 1024, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    page.on('pageerror', error => errors.push(String(error)));
    page.on('console', message => { if (['error', 'warning'].includes(message.type())) errors.push(message.text()); });
    page.on('request', request => { if (!request.url().startsWith(base)) external.push(request.url()); });
    page.on('dialog', async dialog => { errors.push('Untrusted remote text executed'); await dialog.dismiss(); });
    await page.addInitScript(lang => localStorage.setItem('yia.ui-language', lang), language);
    const text = (en, zh) => language === 'en' ? en : zh;
    const get = async path => { const result = await page.request.get(`${base}api/v1/${path}`); assert.equal(result.status(), 200); return result.json(); };
    const noOverflow = async () => assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${language}/${width} overflow`);
    await page.goto(base + '#Home'); await page.locator('.knowledge-delta').waitFor();
    assert.equal(await page.locator('.sidebar-nav button').count(), 6);
    const add = async bvid => {
      await page.getByRole('navigation').getByRole('button', { name: text('Following', '关注'), exact: true }).click();
      await page.getByRole('button', { name: text('Add Source', '添加关注'), exact: true }).first().click();
      await page.getByRole('button', { name: text('Bilibili', '哔哩哔哩'), exact: true }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByLabel(text('Bilibili video URL or BV id', '哔哩哔哩视频链接或 BV 号')).fill(`https://m.bilibili.com/video/${bvid}?share=ignored`);
      await noOverflow();
      await dialog.getByRole('button', { name: text('Import public video', '导入公开视频'), exact: true }).click();
      const open = dialog.getByRole('link', { name: text('Open Content', '打开内容'), exact: true }); await open.waitFor();
      await page.screenshot({ path: join(screenshots, `${language}-${width}-${bvid}-import.png`), fullPage: true });
      await open.click();
    };
    if (!offline) await add(info.no_caption_bv);
    else await page.goto(base + '#Content/bilibili-' + info.no_caption_bv);
    await page.getByRole('button', { name: text('Retry public captions', '重试获取公开字幕'), exact: true }).waitFor();
    assert.ok((await page.locator('body').innerText()).includes(text('Summary and Evidence require trusted captions', '摘要和证据需要可信字幕')));
    assert.equal(await page.locator('.timed-transcript').count(), 0);
    if (!offline) {
      await Promise.all([page.waitForResponse(response => response.url().endsWith('/captions/retry') && response.status() === 200), page.getByRole('button', { name: text('Retry public captions', '重试获取公开字幕'), exact: true }).click()]);
      await noOverflow();
      await add(info.caption_bv);
    } else await page.goto(base + '#Content/bilibili-' + info.caption_bv);
    await page.locator('.timed-transcript li').first().waitFor();
    await page.locator('[id^="content-evidence-"]').first().waitFor();
    const body = await page.locator('body').innerText();
    assert.ok(body.includes('Sentence1 哔哩哔哩原始字幕支持统一证据。'));
    assert.ok(body.includes(text('These are stored original Bilibili timed captions', '这是已保存的哔哩哔哩原始字幕')));
    assert.ok(body.includes(text('Timestamped key points', '按时间标记的要点')));
    assert.ok(body.includes('0.250s') && body.includes('zh-CN'));
    assert.equal(await page.getByRole('button', { name: text('Transcribe on device', '在设备上转写'), exact: true }).count(), 0);
    await noOverflow(); await page.screenshot({ path: join(screenshots, `${offline ? 'offline-' : ''}${language}-${width}-content.png`), fullPage: true });
    await page.reload(); await page.locator('.timed-transcript li').first().waitFor(); await noOverflow();
    const contents = (await get('videos')).videos;
    assert.deepEqual([...new Set(contents.map(content => content.provider))].sort(), ['BILIBILI', 'LOCAL', 'YOUTUBE']);
    assert.equal(contents.filter(content => content.provider === 'BILIBILI').length, 2);
    await page.getByRole('navigation').getByRole('button', { name: text('Following', '关注'), exact: true }).click();
    await page.getByText(text('Manually imported video', '手动导入的视频'), { exact: false }).first().waitFor(); await noOverflow();
    const following = (await get('sources')).sources.filter(source => source.provider === 'BILIBILI');
    assert.equal(following.length, 2); assert.ok(following.every(source => source.source_type === 'VIDEO_URL' && source.channel_id === null));
    await page.getByRole('navigation').getByRole('button', { name: text('Intelligence', '洞察'), exact: true }).click();
    await page.getByRole('button', { name: text('Research', '研究'), exact: true }).click();
    await page.getByRole('button', { name: text('New Research', '新建研究'), exact: true }).click();
    await page.getByLabel(text('Research question', '研究问题')).fill('sentence1 three provider sources');
    for (const id of [info.youtube_id, info.local_id, 'bilibili-' + info.caption_bv]) {
      const title = contents.find(content => content.video_id === id).title;
      await page.getByRole('checkbox', { name: new RegExp(escape(title)) }).check();
    }
    await page.getByRole('button', { name: text('Assemble library packet', '收集资料库证据包'), exact: true }).click();
    await page.locator('.research-result blockquote').first().waitFor();
    const research = await page.locator('.research-result').innerText();
    for (const label of ['YouTube', text('Local', '本地'), text('Bilibili', '哔哩哔哩')]) assert.ok(research.includes(label), label);
    await noOverflow(); await page.screenshot({ path: join(screenshots, `${offline ? 'offline-' : ''}${language}-${width}-research.png`), fullPage: true });
    await page.getByRole('navigation').getByRole('button', { name: text('Home', '首页'), exact: true }).click();
    await page.locator('.knowledge-delta').getByText(new RegExp('Sentence1 Bilibili trusted captions')).first().waitFor(); await noOverflow();
    scenarios.push(offline
      ? `restart/offline/${language}/${width}: stored no-caption Content, captions, Summary, Evidence, reload, mixed Research, Delta`
      : `${language}/${width}: Following Add, no-caption, explicit retry, caption Content, Summary, Evidence, dedupe, mixed Research, Delta`);
    await page.close();
  }
  assert.deepEqual(errors, []); assert.deepEqual(external, []);
  writeFileSync(join(evidence, offline ? 'bilibili-offline-browser.json' : 'bilibili-browser.json'), JSON.stringify({ fixture: true, scenarios, errors, external, overflow: 0, noNewPrimaryNavigation: true }, null, 2));
  console.log(`${scenarios.length} Bilibili three-provider HTTP/SQLite browser flows passed.`);
} catch (error) {
  const pages = browser.contexts().flatMap(context => context.pages());
  for (const [index, page] of pages.entries()) {
    writeFileSync(join(evidence, `browser-failure-${index}.json`), JSON.stringify({ url: page.url(), text: await page.locator('body').innerText(), errors, external }, null, 2));
    await page.screenshot({ path: join(screenshots, `failure-${index}.png`), fullPage: true });
  }
  throw error;
} finally { await browser.close(); }
