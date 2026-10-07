import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { chromium } from 'playwright-core';

// Disposable Vite UI plus synthetic HTTP responses. Nothing here contacts
// Bilibili, the local backend, or any model: the point is the narrow-viewport
// layout of a stored source that no longer verifies, in both interface
// languages, at every supported width.
const base = process.env.YIA_STATUS_UI_URL ?? 'http://127.0.0.1:5311/';
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+\/$/);
const screenshots = process.env.YIA_STATUS_SCREENSHOTS ?? '/tmp/v1x-status-responsive';
const evidence = process.env.YIA_STATUS_EVIDENCE ?? '/tmp/v1x-status-responsive-evidence';
mkdirSync(screenshots, { recursive: true });
mkdirSync(evidence, { recursive: true });

// Each stored Content is in the state a failed source re-verification produces.
// The Bilibili and Local wording differ, so both are checked separately.
const untrusted = (provider, video_id, title, channel) => ({
  video_id, title, channel_name: channel, provider,
  processing_status: provider === 'LOCAL' ? 'LOCAL_SOURCE_UNTRUSTED' : 'SOURCE_UNTRUSTED',
  availability: 'public', media_kind: provider === 'LOCAL' ? 'TEXT' : 'VIDEO',
  filename: title, format: provider === 'LOCAL' ? '.md' : '.json',
  source_url: `https://example.invalid/${video_id}`,
  published_at: '2026-10-01T00:00:00Z', imported_at: '2026-10-01T00:00:00Z',
  source_language: 'zh-CN', duration_seconds: 42,
});
const bilibili = untrusted('BILIBILI', 'bilibili-BV1untrusted', 'Stored Bilibili source that no longer verifies', '公开 UP 主');
const local = untrusted('LOCAL', 'local-untrusted', 'Stored Local snapshot that no longer verifies', null);
// A normal Bilibili video whose public captions were not exposed. This one must
// keep its honest metadata-only wording and must not be reported as a failure.
const captionless = {
  ...untrusted('BILIBILI', 'bilibili-BV1captionless', 'Public video without an exposed caption', '公开 UP 主'),
  processing_status: 'CAPTION_UNAVAILABLE',
};
const videos = [bilibili, local, captionless];

const detail = (video) => ({
  video, transcript: { status: 'UNAVAILABLE', code: `${video.provider}_SOURCE_UNTRUSTED`, code_reason: null },
  note: { v1: { status: 'UNAVAILABLE' }, v2: { status: 'UNAVAILABLE' } },
  intelligence_result: { status: 'NOT_PROCESSED' }, history: [],
});
const settings = {
  processing_defaults: {},
  general: {
    timezone: 'Asia/Shanghai', output_language: 'zh-CN',
    output_language_source: 'APP_DEFAULT', output_language_updated_at: null,
  },
  cloud_credential: { configured: false }, model_preference: {}, providers: [],
  bilibili: {
    provider: 'BILIBILI',
    video_ingestion: { available: true, code: 'PUBLIC_VIDEO_INGESTION_AVAILABLE' },
    creator_following: {
      available: false, code: 'CREATOR_TRACKING_UNAVAILABLE', endpoint: '/x/space/arc/search',
      message: 'Continuous Bilibili creator tracking is currently unavailable. You can still add public Bilibili videos.',
    },
    public_captions: { available: false, code: 'PUBLIC_CAPTIONS_NOT_OBSERVED', note: 'Not observed on the compliant no-login path.' },
  },
};
const sources = {
  sources: [{
    source_id: 'bilibili-BV1captionless', display_name: '手动导入的视频', provider: 'BILIBILI',
    canonical_url: 'https://www.bilibili.com/video/BV1captionless', enabled: true,
    last_checked_at: null, last_success_at: null, last_error: null,
    source_type: 'VIDEO_URL', channel_id: null, tracking: {
      health: 'HEALTHY', coverage: 'FOLLOWING_SCOPE', verified_at: null, baseline_at: null,
      update_count: 0, pending_count: 0, unavailable_count: 0, checking: false, processing_count: 0,
    },
  }],
};
const localSource = {
  sources: [{
    source_id: 'local-untrusted', display_name: 'Local library', provider: 'LOCAL',
    canonical_url: 'file:///local', enabled: true, last_checked_at: null, last_success_at: null,
    last_error: null, source_type: 'LIBRARY', channel_id: null,
    recent_videos: [{ video_id: 'local-untrusted', title: local.title, processing_status: 'LOCAL_SOURCE_UNTRUSTED' }],
    tracking: null,
  }],
};

const copy = {
  en: {
    bilibili: 'The stored Bilibili source failed verification. Its Evidence is unavailable.',
    local: 'The imported snapshot failed verification. Existing Evidence is unavailable.',
    captionless: 'Public captions are unavailable',
    metadataOnly: 'Summary and Evidence require trusted captions',
    creatorOff: 'Continuous creator tracking is currently unavailable',
    backupReady: 'Core data is quiescent and ready for backup.',
    backupBlocked: 'a Source Run is still working',
    backupListing: 'Backup is unavailable while these are still running:',
  },
  'zh-CN': {
    bilibili: '已保存的哔哩哔哩来源未通过验证，其证据不可用。',
    local: '已导入的快照未通过验证，现有证据暂不可用。',
    captionless: '暂无可用的公开字幕',
    metadataOnly: '摘要和证据需要可信字幕',
    creatorOff: 'UP 主持续关注当前暂不可用',
    backupReady: '核心数据已就绪，可以创建备份。',
    backupBlocked: '有一个采集任务仍在执行',
    backupListing: '以下工作尚未结束，暂时无法备份：',
  },
};

const browser = await chromium.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
  args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'],
});
const errors = [], external = [], scenarios = [], offenders = [];
// Backup readiness is checked twice per language/width run: quiescent, then with
// work still in flight. Phase 11R's quiescence fix lives on this surface, so
// both wordings have to survive the responsive pass untouched.
const quiescent = {
  restore_pending: false, last_restore: null,
  schema_version: 34, app_version: '0.1.0', data_artifacts: [],
};
const busy = {
  restore_pending: false, last_restore: null,
  schema_version: 34, app_version: '0.1.0', data_artifacts: [],
  reasons: ['SOURCE_RUN_ACTIVE', 'DISTILLATION_ACTIVE'],
};
let backupStatus = { ...quiescent, ready: true, reasons: [] };
try {
  for (const language of ['zh-CN', 'en']) for (const width of [320, 768, 1024, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    page.setDefaultTimeout(20000);
    page.on('pageerror', (error) => errors.push(String(error)));
    page.on('console', (message) => { if (['error', 'warning'].includes(message.type())) errors.push(message.text()); });
    page.on('request', (request) => { if (!request.url().startsWith(base)) external.push(request.url()); });
    page.on('dialog', async (dialog) => { errors.push('Remote text executed'); await dialog.dismiss(); });
    await page.addInitScript((value) => localStorage.setItem('yia.ui-language', value), language);
    await page.route('**/api/v1/**', async (route) => {
      const path = new URL(route.request().url()).pathname;
      const video = videos.find((item) => path.endsWith(`/videos/${item.video_id}`));
      const body = path.endsWith('/settings') ? settings
        : path.endsWith('/videos') ? { videos }
        : path.endsWith('/sources/local-untrusted') ? localSource
        : path.endsWith('/sources') ? sources
        // Backup readiness is checked twice per run: once quiescent, once with
        // work still in flight, because the Phase 11R quiescence fix lives here.
        : path.endsWith('/backup-restore/status') ? { status: backupStatus }
        // The rest of Settings has to render, or the Backup panel below it is
        // never reached and the check would pass without testing anything.
        : path.endsWith('/settings/preferences') ? { active: [], history: [] }
        : path.endsWith('/settings/source-policy') ? { policy: { initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: [], ignore_rules: [], distillation_style: 'BALANCED' } }
        : path.endsWith('/settings/resource-usage') ? { usage: [] }
        : video ? detail(video)
        : path.endsWith('/knowledge-delta') ? { window: null, items: [], counts: {}, blocked_source_checks: 0 }
        : {};
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    });

    // Every element that reaches past the viewport is collected, so a failure
    // names the component that broke rather than only reporting a number. The
    // narrow primary navigation is an intentional horizontal scroll strip, so
    // content inside such a strip is not counted as overflow.
    const noOverflow = async (where) => {
      const wide = await page.evaluate(() => {
        const scrollable = (node) => {
          for (let parent = node.parentElement; parent; parent = parent.parentElement) {
            const overflow = getComputedStyle(parent).overflowX;
            if (overflow === 'auto' || overflow === 'scroll') return true;
          }
          return false;
        };
        return [...document.querySelectorAll('body *')]
          .filter((node) => node.getBoundingClientRect().right > window.innerWidth + 1 && !scrollable(node))
          .map((node) => ({ tag: node.tagName, cls: String(node.className), width: Math.round(node.getBoundingClientRect().width), text: (node.textContent ?? '').slice(0, 90) }));
      });
      if (wide.length) offenders.push({ language, width, where, wide: wide.slice(0, 8) });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false, `${language}/${width}/${where} horizontal overflow`);
    };
    const body = async () => (await page.locator('body').innerText());
    // The failure mode being regressed: a resolved sentence that was run
    // through the enum de-CamelCaser, or a backend code shown verbatim.
    const noRawVocabulary = async (where, forbidden) => {
      const text = await body();
      for (const phrase of forbidden) assert.equal(text.includes(phrase), false, `${language}/${width}/${where} leaked ${JSON.stringify(phrase)}`);
    };

    await page.goto(base + '#Content');
    await page.locator('.list-row').first().waitFor();
    // Both untrusted states are visible in the list before anything is opened.
    await page.getByText(copy[language].bilibili, { exact: false }).first().waitFor();
    await page.getByText(copy[language].local, { exact: false }).first().waitFor();
    const raw = [
      'The stored bilibili source failed verification. its evidence is unavailable.',
      'LOCAL_SOURCE_UNTRUSTED', 'SOURCE_UNTRUSTED', 'Local source untrusted',
    ];
    await noRawVocabulary('content-list', raw);
    await noOverflow('content-list');
    await page.screenshot({ path: `${screenshots}/${language}-${width}-content-list.png`, fullPage: true });

    for (const video of videos) {
      await page.goto(`${base}#Content/${video.video_id}`);
      await page.getByText(copy[language][video === bilibili ? 'bilibili' : video === local ? 'local' : 'captionless'], { exact: false }).first().waitFor();
      await noRawVocabulary(`detail-${video.video_id}`, raw);
      await noOverflow(`detail-${video.video_id}`);
      // A no-caption Bilibili Content stays an honest metadata-only record.
      if (video === captionless) {
        assert.ok((await body()).includes(copy[language].metadataOnly), `${language}/${width} lost the metadata-only wording`);
        assert.equal(await page.locator('.timed-transcript').count(), 0);
      }
      await page.screenshot({ path: `${screenshots}/${language}-${width}-${video.video_id}.png`, fullPage: true });
    }

    await page.goto(base + '#Following');
    await page.getByText(copy[language].creatorOff, { exact: false }).first().waitFor();
    await noOverflow('following');
    await page.getByText('手动导入的视频', { exact: false }).first().click().catch(() => {});
    await noOverflow('following-bilibili-source');

    await page.goto(base + '#Home');
    await noOverflow('home');
    await page.close();

    // Backup readiness is checked on a fresh page in both states. Phase 11R
    // changed quiescence so a settled attention run no longer blocks, and this
    // is the surface that reports it.
    const settingsPage = await browser.newPage({ viewport: { width, height: 1000 } });
    settingsPage.setDefaultTimeout(20000);
    settingsPage.on('pageerror', (error) => errors.push(String(error)));
    settingsPage.on('console', (message) => { if (['error', 'warning'].includes(message.type())) errors.push(message.text()); });
    settingsPage.on('request', (request) => { if (!request.url().startsWith(base)) external.push(request.url()); });
    await settingsPage.addInitScript((value) => localStorage.setItem('yia.ui-language', value), language);
    await settingsPage.route('**/api/v1/**', async (route) => {
      const path = new URL(route.request().url()).pathname;
      const body = path.endsWith('/backup-restore/status') ? { status: backupStatus }
        : path.endsWith('/settings/preferences') ? { active: [], history: [] }
        : path.endsWith('/settings/source-policy') ? { policy: { initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: [], ignore_rules: [], distillation_style: 'BALANCED' } }
        : path.endsWith('/settings/resource-usage') ? { usage: [] }
        : path.endsWith('/settings') ? settings
        : path.endsWith('/knowledge-delta') ? { knowledge_delta: { window_start: '2026-09-26T08:00:00.000000Z', window_end: '2026-10-03T08:00:00.000000Z', timezone: 'Asia/Shanghai', status: 'available', detail_limit: 2, categories: [] } }
        : {};
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    });
    backupStatus = { ...quiescent, ready: true, reasons: [] };
    await settingsPage.goto(base + '#Settings');
    await settingsPage.getByText(copy[language].backupReady, { exact: false }).first().waitFor();
    assert.equal(await settingsPage.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false, `${language}/${width}/settings-backup-ready horizontal overflow`);
    // Quiescent means no blocking reason is listed at all.
    assert.equal((await settingsPage.locator('body').innerText()).includes(copy[language].backupListing), false, `${language}/${width} blocked Backup while quiescent`);
    await settingsPage.screenshot({ path: `${screenshots}/${language}-${width}-backup-ready.png`, fullPage: true });

    backupStatus = { ...busy, ready: false };
    await settingsPage.reload();
    await settingsPage.getByText(copy[language].backupListing, { exact: false }).first().waitFor();
    assert.ok((await settingsPage.locator('body').innerText()).includes(copy[language].backupBlocked), `${language}/${width} lost the blocking Backup wording`);
    assert.equal(await settingsPage.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false, `${language}/${width}/settings-backup-blocked horizontal overflow`);
    await settingsPage.screenshot({ path: `${screenshots}/${language}-${width}-settings.png`, fullPage: true });
    await settingsPage.close();

    scenarios.push({
      language, width,
      states: ['SOURCE_UNTRUSTED bilibili', 'LOCAL_SOURCE_UNTRUSTED local', 'CAPTION_UNAVAILABLE bilibili', 'creator following withdrawn', 'backup ready', 'backup blocked'],
    });
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  // Nothing outside an intentional scroll strip may reach past the viewport:
  // a status that only fits because its container clips it would be a silent
  // loss of meaning, which the document-level check alone would not catch.
  assert.deepEqual(offenders, [], 'content escaped the viewport instead of wrapping');
  writeFileSync(`${evidence}/status-responsive.json`, JSON.stringify({ fixture: true, scenarios, errors, external, overflow: 0, offenders, rawVocabularyLeaks: 0 }, null, 2));
  console.log(`${scenarios.length} untrusted-source responsive browser scenarios passed; no overflow, no raw vocabulary.`);
} catch (error) {
  writeFileSync(`${evidence}/status-responsive-failure.json`, JSON.stringify({ message: String(error), offenders, errors, external }, null, 2));
  throw error;
} finally {
  await browser.close();
}