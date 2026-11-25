import { useState } from "react";
import { ApiRequestError, post, put } from "../api/client";

const BROWSER_CHOICES = [
  "chrome",
  "safari",
  "edge",
  "firefox",
  "brave",
  "vivaldi",
  "chromium",
] as const;

export type InlineYouTubeAuthRecoveryProps = {
  videoId: string;
  sourceId?: string | null;
  zh: boolean;
  onAuthorizedRetry: (message: string) => void;
};

export function InlineYouTubeAuthRecovery({
  videoId,
  sourceId,
  zh,
  onAuthorizedRetry,
}: InlineYouTubeAuthRecoveryProps) {
  const [expanded, setExpanded] = useState(false);
  const [authMode, setAuthMode] = useState<"browser" | "cookie_file">("browser");
  const [browserName, setBrowserName] = useState<string>("chrome");
  const [cookiesText, setCookiesText] = useState("");
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (busy) return;
    if (authMode === "cookie_file" && !cookiesText.trim()) {
      setErrorMsg(zh ? "请先粘贴 Netscape cookies.txt 内容。" : "Paste Netscape cookies.txt first.");
      return;
    }
    setBusy(true);
    setErrorMsg(null);
    try {
      await put("/workspace-ai/youtube-auth", {
        enabled: true,
        auth_mode: authMode,
        browser_name: authMode === "browser" ? browserName : undefined,
        cookies_txt: authMode === "cookie_file" ? cookiesText : undefined,
      });
      if (sourceId) {
        const commandId =
          typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
            ? crypto.randomUUID()
            : `retry-${Date.now()}`;
        await post(`/sources/${sourceId}/check`, { command_id: commandId });
      }
      setExpanded(false);
      onAuthorizedRetry(
        zh
          ? "已在本机安全授权并立即重新发起采集，结果将直接在本页刷新。"
          : "Authorized locally and immediately re-triggered fetch; progress will update here.",
      );
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg(
          zh
            ? "授权或重试失败，请检查所选浏览器或 cookies.txt 格式。"
            : "Authorization or retry failed. Check browser selection or cookies.txt format.",
        );
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="inline-yt-auth-wrap">
      <div className="button-row">
        <button
          type="button"
          className="button button-primary button-small"
          aria-expanded={expanded}
          onClick={() => {
            setErrorMsg(null);
            setExpanded((cur) => !cur);
          }}
        >
          {zh ? "页内授权并立即重试" : "Authorize here & retry"}
        </button>
        <a
          className="button button-secondary button-small"
          href={`#Settings/youtube-auth?return=${encodeURIComponent(`#Content/${videoId}`)}`}
        >
          {zh ? "授权本人 YouTube 登录态 ›" : "Authorize YouTube login ›"}
        </a>
      </div>
      {expanded ? (
        <section
          className="inline-yt-auth-card"
          role="region"
          aria-label={zh ? "页内 YouTube 登录态授权确认" : "In-place YouTube authorization consent"}
        >
          <p className="inline-yt-auth-scope">
            {zh
              ? "明确授权说明：仅在匿名获取被拦截时用于当前视频重试；Cookie 严格按 YouTube/Google 白名单过滤并仅存于本机钥匙串，不进入数据库与导出备份，受每日限额及冷却保护，可随时断开。"
              : "Explicit consent: used only when anonymous fetch is blocked; cookies are strictly domain-filtered and kept in local Keychain only, with daily caps and instant disconnect."}
          </p>
          <div className="inline-yt-auth-fields">
            <label>
              <span>{zh ? "授权方式" : "Mode"}</span>
              <select
                aria-label={zh ? "页内授权方式" : "Inline authorization mode"}
                value={authMode}
                disabled={busy}
                onChange={(e) => setAuthMode(e.target.value as "browser" | "cookie_file")}
              >
                <option value="browser">{zh ? "复用本机已登录浏览器" : "Use signed-in local browser"}</option>
                <option value="cookie_file">{zh ? "粘贴 Netscape cookies.txt" : "Paste Netscape cookies.txt"}</option>
              </select>
            </label>
            {authMode === "browser" ? (
              <label>
                <span>{zh ? "已登录 YouTube 的浏览器" : "Browser"}</span>
                <select
                  aria-label={zh ? "选择已登录浏览器" : "Select signed-in browser"}
                  value={browserName}
                  disabled={busy}
                  onChange={(e) => setBrowserName(e.target.value)}
                >
                  {BROWSER_CHOICES.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label className="inline-yt-auth-cookies">
                <span>{zh ? "cookies.txt 内容" : "cookies.txt"}</span>
                <textarea
                  rows={3}
                  aria-label={zh ? "粘贴 YouTube cookies.txt" : "Paste YouTube cookies.txt"}
                  value={cookiesText}
                  disabled={busy}
                  onChange={(e) => setCookiesText(e.target.value)}
                  placeholder=".youtube.com	TRUE	/	TRUE	..."
                />
              </label>
            )}
          </div>
          {errorMsg ? (
            <p className="form-error" role="alert">
              {errorMsg}
            </p>
          ) : null}
          <div className="button-row">
            <button
              type="button"
              className="button button-primary button-small"
              disabled={busy}
              onClick={() => void handleConfirm()}
            >
              {busy
                ? zh
                  ? "正在授权并重试…"
                  : "Authorizing & retrying…"
                : zh
                  ? "确认授权并立即重试"
                  : "Confirm & retry now"}
            </button>
            <button
              type="button"
              className="button button-ghost button-small"
              disabled={busy}
              onClick={() => {
                setExpanded(false);
                setErrorMsg(null);
              }}
            >
              {zh ? "取消" : "Cancel"}
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
