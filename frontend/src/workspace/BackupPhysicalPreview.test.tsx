import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App } from './App';
const oldPreview = { backup_date: '2026-10-16T00:00:00Z', application_version: 'test', schema_version: 39,
  following_count: 1, content_count: 1, summary_count: 1, evidence_count: 1, intelligence_count: 0, topic_count: 0,
  settings_included: true, data_artifact_count: 2, data_size_bytes: 1024, vault_excluded: true };
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ''; });
it.each(['en', 'zh-CN'].flatMap(language => ['new', 'old', 'malformed'].map(kind => [language, kind])))('labels physical files only with complete valid additive DTO %s/%s', async (language, kind) => {
  localStorage.setItem('yia.ui-language', language); location.hash = '#Settings';
  const preview = kind === 'new' ? { ...oldPreview, data_file_count: 1, data_file_size_bytes: 1024 }
    : kind === 'malformed' ? { ...oldPreview, data_file_count: -1, data_file_size_bytes: {} } : oldPreview;
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    let body: object = {};
    if (path.endsWith('/backup-restore/status')) body = { status: { ready: true, reasons: [], restore_pending: false } };
    else if (init?.method === 'POST') body = { backup: { backup_id: 'b1', preview, download_url: '/api/v1/backup-restore/backups/b1/download' } };
    else if (path.endsWith('/settings')) body = { general: { timezone: 'Asia/Shanghai', output_language: 'en' }, providers: [] };
    else if (path.endsWith('/settings/preferences')) body = { active: [], history: [] };
    else if (path.endsWith('/settings/source-policy')) body = { policy: { focus_rules: [], ignore_rules: [], distillation_style: 'BALANCED', initial_history_count: 3, per_run_max_new_videos: 5 } };
    else if (path.endsWith('/settings/resource-usage')) body = { usage: [] };
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal('fetch', fetcher); render(<App />);
  const create = await screen.findByRole('button', { name: language === 'en' ? 'Create Backup' : '创建备份' }) as HTMLButtonElement;
  await waitFor(() => expect(create.disabled).toBe(false));
  fireEvent.click(create);
  const label = kind === 'new' ? language === 'en' ? 'DATA files' : '数据文件' : language === 'en' ? 'DATA entries' : '数据条目';
  const dt = await screen.findByText(label);
  expect(dt.nextElementSibling?.textContent).toBe(`${kind === 'new' ? 1 : 2} · 1.0 KB`);
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1);
});
