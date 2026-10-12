import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { FirstRunOnboarding } from './Onboarding';
import { LocalTranscription } from './LocalTranscription';
import { UiLanguageProvider } from './uiLanguage';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
it.each(['en', 'zh-CN'])('offers transcription setup in first-run guidance (%s)', language => {
  localStorage.setItem('yia.ui-language', language);
  render(<UiLanguageProvider><FirstRunOnboarding onSkip={vi.fn()} onAddFollowing={vi.fn()} /></UiLanguageProvider>);
  fireEvent.click(screen.getByRole('button', { name: language === 'en' ? 'Continue' : '继续' }));
  const link = screen.getByRole('link', { name: language === 'en' ? 'Set up local transcription' : '设置本地转写' });
  expect(link.getAttribute('href')).toBe('#Settings/transcription');
  expect(document.body.textContent).toContain(language === 'en' ? 'Importing a video saves the file' : '导入视频只保存文件');
});
it.each(['en', 'zh-CN'])('gives missing model users a setup route after skipping onboarding (%s)', async language => {
  localStorage.setItem('yia.ui-language', language);
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ transcription: {
    status: 'MODEL_MISSING', start_available: false, retry_available: false,
    capability: { state: 'MODEL_MISSING', reason_code: 'MODEL_MISSING', runtime_available: true, model_present: false, production_eligible: false },
  } }) }));
  render(<UiLanguageProvider><LocalTranscription id='local-media' onCompleted={vi.fn()} /></UiLanguageProvider>);
  const link = await screen.findByRole('link', { name: language === 'en' ? 'Set up local transcription' : '设置本地转写' });
  expect(link.getAttribute('href')).toContain('#Settings/transcription');
  expect(screen.queryByRole('button', { name: language === 'en' ? 'Start transcription' : '开始转写' })).toBeNull();
});
it('explains a failed qualification without implying configuration grants quality', async () => {
  localStorage.setItem('yia.ui-language', 'zh-CN');
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ transcription: {
    status: 'QUALIFICATION_REQUIRED', retry_available: false,
    capability: { state: 'QUALIFICATION_REQUIRED', qualification_state: 'FAILED', runtime_available: true, model_present: true, executor_compatible: true, production_eligible: false },
  } }) }));
  render(<UiLanguageProvider><LocalTranscription id='local-media' onCompleted={vi.fn()} /></UiLanguageProvider>);
  expect(await screen.findByText(/该模型未通过语音质量验证/)).toBeTruthy();
  expect(document.body.textContent).toContain('配置目录不会解除此限制');
  expect(screen.queryByRole('button', { name: '开始转写' })).toBeNull();
});
