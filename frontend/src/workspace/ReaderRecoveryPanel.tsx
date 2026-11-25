import { useEffect, useRef, useState } from "react";
import { ApiRequestError, api, post, put } from "../api/client";

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
  const [grantScope, setGrantScope] = useState<"single_video" | "global">("single_video");
  const [authMode, setAuthMode] = useState<"browser" | "cookie_file">("browser");
  const [browserName, setBrowserName] = useState<string>("chrome");
  const [cookiesText, setCookiesText] = useState("");
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [persistedScope, setPersistedScope] = useState<"single_video" | "global" | null>(null);
  const [activeVideoGrant, setActiveVideoGrant] = useState(false);
  const [globalAuthEnabled, setGlobalAuthEnabled] = useState(false);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  const clearTransientSecrets = () => {
    setCookiesText("");
  };

  useEffect(() => {
    setExpanded(false);
    setCookiesText("");
    setErrorMsg(null);
    setPersistedScope(null);
    setActiveVideoGrant(false);
    setGlobalAuthEnabled(false);
    setStatusNotice(null);
    let active = true;
    void (async () => {
      try {
        const res = await api<{
          global_enabled?: boolean;
          enabled?: boolean;
          video_grant?: { active?: boolean } | null;
        }>(`/workspace-ai/youtube-auth?video_id=${encodeURIComponent(videoId)}`);
        if (!active || !res || typeof res !== "object") return;
        setActiveVideoGrant(Boolean(res.video_grant?.active));
        setGlobalAuthEnabled(Boolean(res.global_enabled ?? res.enabled));
      } catch {
        // tolerate absent mock endpoint cleanly
      }
    })();
    return () => {
      active = false;
    };
  }, [videoId]);

  useEffect(() => {
    return () => {
      setCookiesText("");
    };
  }, []);

  const triggerSourceCheck = async (appliedScope: "single_video" | "global") => {
    if (!sourceId) {
      setErrorMsg(
        zh
          ? "当前条目缺少来源 ID，无法自动重试抓取（未发起额外网络请求）。"
          : "Missing source ID; retry request cannot be started.",
      );
      return;
    }
    const commandId =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `retry-${Date.now()}`;
    await post(`/sources/${sourceId}/check`, { command_id: commandId });
    clearTransientSecrets();
    setPersistedScope(null);
    setExpanded(false);
    onAuthorizedRetry(
      appliedScope === "single_video"
        ? zh
          ? "已仅对当前视频启用单次临时授权（10 分钟内有效，不开启全局授权）并立即重新发起采集。"
          : "Authorized for this video once (10m TTL) and re-triggered fetch."
        : zh
          ? "已启用全局备用授权并立即重新发起采集，结果将直接在本页刷新。"
          : "Global fallback authorized locally and fetch re-triggered.",
    );
  };

  const handleConfirm = async () => {
    if (busyRef.current || busy) return;
    if (!sourceId) {
      setErrorMsg(
        zh
          ? "当前条目缺少来源标识，暂不能执行页内重试，请保留或从来源页发起重试。"
          : "Source ID is missing; cannot trigger inline retry.",
      );
      return;
    }
    if (authMode === "cookie_file" && !cookiesText.trim()) {
      setErrorMsg(zh ? "请先粘贴 Netscape cookies.txt 内容。" : "Paste Netscape cookies.txt first.");
      return;
    }
    busyRef.current = true;
    setBusy(true);
    setErrorMsg(null);
    setStatusNotice(null);
    let savedScope: "single_video" | "global" | null = null;
    try {
      await put("/workspace-ai/youtube-auth", {
        enabled: true,
        grant_scope: grantScope,
        target_video_id: grantScope === "single_video" ? videoId : undefined,
        auth_mode: authMode,
        browser_name: authMode === "browser" ? browserName : undefined,
        cookies_txt: authMode === "cookie_file" ? cookiesText : undefined,
      });
      savedScope = grantScope;
      setPersistedScope(savedScope);
      clearTransientSecrets();
      await triggerSourceCheck(savedScope);
    } catch (err) {
      const detail =
        err instanceof ApiRequestError
          ? err.message
          : zh
            ? "请求未能完成，请检查设置或网络连接。"
            : "Request failed. Check settings or connectivity.";
      if (savedScope !== null) {
        setErrorMsg(
          savedScope === "single_video"
            ? zh
              ? `本次视频单次授权已写入（10 分钟内有效，未开启全局授权），但立即重抓请求失败：${detail}。可直接重试或点击撤销。`
              : `Single-video grant saved, but retry failed: ${detail}. Retry or revoke.`
            : zh
              ? `全局备用授权已保存并持久化，但立即重抓请求失败：${detail}。可直接重试或点击撤销全局授权。`
              : `Global fallback saved, but retry failed: ${detail}. Retry or revoke.`,
        );
      } else {
        setErrorMsg(detail);
      }
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const handleRetryOnly = async () => {
    if (busyRef.current || busy || !persistedScope) return;
    busyRef.current = true;
    setBusy(true);
    setErrorMsg(null);
    try {
      await triggerSourceCheck(persistedScope);
    } catch (err) {
      const detail =
        err instanceof ApiRequestError
          ? err.message
          : zh
            ? "重试抓取请求失败，请稍后再试或撤销授权。"
            : "Retry request failed.";
      setErrorMsg(detail);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const handleRevoke = async (explicitScope?: "single_video" | "global") => {
    if (busyRef.current || busy) return;
    const revokeScope = explicitScope ?? (persistedScope === "global" ? "global" : "single_video");
    busyRef.current = true;
    setBusy(true);
    setErrorMsg(null);
    try {
      await post(
        "/workspace-ai/youtube-auth/disconnect",
        revokeScope === "global"
          ? { scope: "global" }
          : { scope: "single_video", target_video_id: videoId },
      );
      clearTransientSecrets();
      setPersistedScope(null);
      if (revokeScope === "single_video") {
        setActiveVideoGrant(false);
      } else {
        setGlobalAuthEnabled(false);
      }
      setExpanded(false);
      setStatusNotice(
        revokeScope === "global"
          ? zh
            ? "已撤销全局备用授权并清除全局 Cookie（未影响其他单视频授权）。"
            : "Global fallback authorization revoked and global cookies purged."
          : zh
            ? "已撤销本页授权并清除临时 Cookie。"
            : "Authorization revoked and stored cookies cleared.",
      );
    } catch (err) {
      setErrorMsg(
        err instanceof ApiRequestError
          ? err.message
          : zh
            ? "撤销授权失败，请到设置页检查状态。"
            : "Failed to revoke authorization.",
      );
    } finally {
      busyRef.current = false;
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
            setStatusNotice(null);
            setExpanded((cur) => {
              if (cur) clearTransientSecrets();
              return !cur;
            });
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
        {activeVideoGrant ? (
          <button
            type="button"
            className="button button-ghost button-small"
            disabled={busy}
            onClick={() => void handleRevoke("single_video")}
          >
            {zh ? "撤销当前视频授权" : "Revoke this video grant"}
          </button>
        ) : null}
      </div>
      {activeVideoGrant || globalAuthEnabled ? (
        <p className="hint">
          {activeVideoGrant
            ? zh
              ? "当前视频存在未消费的临时单次授权（仅限本视频使用，可随时单独撤销）。"
              : "Active single-video grant exists for this video (isolated from other videos)."
            : zh
              ? "全局备用授权当前已启用（对所有受阻视频生效）。"
              : "Global fallback is currently enabled."}
        </p>
      ) : null}
      {statusNotice ? (
        <p className="hint" role="status">
          {statusNotice}
        </p>
      ) : null}
      {expanded ? (
        <section
          className="inline-yt-auth-card"
          role="region"
          aria-label={zh ? "页内 YouTube 登录态授权确认" : "In-place YouTube authorization consent"}
        >
          <p className="inline-yt-auth-scope">
            {grantScope === "single_video"
              ? zh
                ? "明确授权说明：默认仅授权当前视频单次重试（10 分钟内有效、用后即失效，不开启全局备用授权）；浏览器模式将从所选浏览器读取登录态并在内存中严格按 YouTube/Google 域名白名单过滤，粘贴 Cookie 仅存本机钥匙串，不入数据库与备份，受每日限额及冷却保护，可随时撤销。"
                : "Explicit consent: default single-video grant applies once for this video (10m TTL, no global fallback). Browser/cookie credentials are strictly YouTube/Google allowlist filtered and capped daily."
              : zh
                ? "明确授权说明：你已选择开启全局备用授权，后续其他匿名被拦截的 YouTube 视频也会在每日限额与冷却保护下复用此配置；Cookie 严格按 YouTube/Google 白名单过滤，可随时在此或设置页撤销断开。"
                : "Explicit consent: global fallback stays enabled for future blocked videos under daily limits and cooldowns, and can be disconnected anytime."}
          </p>
          <div className="inline-yt-auth-fields">
            <label>
              <span>{zh ? "授权范围" : "Scope"}</span>
              <select
                aria-label={zh ? "页内授权范围" : "Inline authorization scope"}
                value={grantScope}
                disabled={busy}
                onChange={(e) => {
                  clearTransientSecrets();
                  setErrorMsg(null);
                  setGrantScope(e.target.value as "single_video" | "global");
                }}
              >
                <option value="single_video">
                  {zh ? "仅本次视频重试（默认，不启用全局授权）" : "This video once only (default)"}
                </option>
                <option value="global">
                  {zh ? "开启全局备用授权（后续其他受阻视频也可使用）" : "Enable global fallback"}
                </option>
              </select>
            </label>
            <label>
              <span>{zh ? "授权方式" : "Mode"}</span>
              <select
                aria-label={zh ? "页内授权方式" : "Inline authorization mode"}
                value={authMode}
                disabled={busy}
                onChange={(e) => {
                  clearTransientSecrets();
                  setErrorMsg(null);
                  setAuthMode(e.target.value as "browser" | "cookie_file");
                }}
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
            <div className="inline-yt-auth-failure" role="alert">
              <p className="form-error">{errorMsg}</p>
              {persistedScope !== null ? (
                <div className="button-row">
                  <button
                    type="button"
                    className="button button-secondary button-small"
                    disabled={busy || !sourceId}
                    onClick={() => void handleRetryOnly()}
                  >
                    {zh ? "重新发起采集" : "Retry fetch"}
                  </button>
                  <button
                    type="button"
                    className="button button-ghost button-small"
                    disabled={busy}
                    onClick={() => void handleRevoke()}
                  >
                    {persistedScope === "global"
                      ? zh
                        ? "撤销全局授权"
                        : "Revoke global auth"
                      : zh
                        ? "撤销本次授权"
                        : "Revoke grant"}
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
          <div className="button-row">
            <button
              type="button"
              className="button button-primary button-small"
              disabled={busy || !sourceId}
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
                clearTransientSecrets();
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
