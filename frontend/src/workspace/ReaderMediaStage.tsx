import { useState } from "react";
import { PhosphorIcon } from "./ui/phosphorIcons";

export function formatHumanDuration(seconds: number): string {
  const rounded = Math.ceil(seconds);
  if (rounded < 60) return `${rounded}s`;
  const mins = Math.floor(rounded / 60);
  const secs = rounded % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

export function describeMediaPlaybackError(
  errorCode: number | null,
  zh: boolean,
): { title: string; detail: string } {
  switch (errorCode) {
    case 1:
      return zh
        ? {
            title: "媒体加载已中断",
            detail: "请求被切换或主动中止。点击下方「重试加载」即可重新建立媒体流。",
          }
        : {
            title: "Media loading aborted",
            detail: "Playback loading was interrupted before finishing. Click Retry to reload.",
          };
    case 2:
      return zh
        ? {
            title: "本机媒体流网络传输中断",
            detail: "与本地服务读取音视频流时连接中断，请确认应用服务正常后点击「重试加载」。",
          }
        : {
            title: "Local media stream interrupted",
            detail: "A network error interrupted local streaming. Ensure the local server is running and retry.",
          };
    case 3:
      return zh
        ? {
            title: "浏览器解码该媒体流失败",
            detail:
              "视频或音频帧可能损坏，或包含内置浏览器不兼容的编码参数。可先「重试加载」，或改用本机系统播放器观看原文件，右侧字幕/证据抽屉仍可正常阅读。",
          }
        : {
            title: "Browser failed to decode media",
            detail:
              "Some frames could not be decoded by the browser. Retry, or open the file in your system player while reading the transcript drawer here.",
          };
    case 4:
      return zh
        ? {
            title: "当前格式暂不支持浏览器内直接播放（或原文件已失效）",
            detail:
              "若为 HEVC/H.265 或特殊容器封装，建议使用本机系统播放器播放，并直接在当前页查看归纳与字幕；若怀疑文件缺失或被修改，可点击「重试加载」或重新导入。",
          }
        : {
            title: "Format unsupported in browser or source unavailable",
            detail:
              "Some codecs (such as HEVC) are unsupported inline, or the managed file changed/is missing. Open in your system player or retry loading.",
          };
    default:
      return zh
        ? {
            title: "无法播放当前本机媒体",
            detail: "请点击「重试加载」再次尝试；若仍失败，可改用系统播放器播放原文件并查阅字幕。",
          }
        : {
            title: "Unable to play local media",
            detail: "Click Retry to reload, or open the original file with your system media player.",
          };
  }
}

export type ReaderMediaStageProps = {
  zhReader: boolean;
  provider?: string | null;
  channelName?: string | null;
  title?: string | null;
  sourceUrl?: string | null;
  durationSeconds?: number | null;
  heroPosterUrl: string | null;
  isLocalMedia: boolean;
  isBilibili: boolean;
  isPlayableLocalVideo: boolean;
  isPlayableLocalAudio: boolean;
  localMediaSrc: string;
  playing: boolean;
  mediaErrorCode: number | null;
  onPlayStart: () => void;
  onHidePlayer: () => void;
  onMediaError: (code: number | null) => void;
  onRetryMedia: () => void;
  onOpenTranscriptDrawer?: () => void;
  evidenceCount?: number;
  transcriptAvailable?: boolean;
  onOpenEvidenceDrawer?: () => void;
};

export function ReaderMediaStage({
  zhReader,
  provider,
  channelName,
  title,
  sourceUrl,
  durationSeconds,
  heroPosterUrl,
  isLocalMedia,
  isBilibili,
  isPlayableLocalVideo,
  isPlayableLocalAudio,
  localMediaSrc,
  playing,
  mediaErrorCode,
  onPlayStart,
  onHidePlayer,
  onMediaError,
  onRetryMedia,
  onOpenTranscriptDrawer,
  evidenceCount = 0,
  transcriptAvailable = false,
  onOpenEvidenceDrawer,
}: ReaderMediaStageProps) {
  const [retryNonce, setRetryNonce] = useState(0);
  const errorInfo = mediaErrorCode !== null ? describeMediaPlaybackError(mediaErrorCode, zhReader) : null;

  const handleRetryClick = () => {
    setRetryNonce((value) => value + 1);
    onRetryMedia();
  };

  return (
    <div
      className={`reader-media-stage${playing ? " is-playing" : ""}`}
      aria-label={zhReader ? "视频预览与播放入口" : "Video preview and playback"}
    >
      {isPlayableLocalVideo && playing ? (
        <div className="reader-inline-player-wrap">
          {errorInfo === null ? (
            <video
              key={`video-${localMediaSrc}-${retryNonce}`}
              className="reader-inline-player"
              controls
              autoPlay
              preload="metadata"
              src={localMediaSrc}
              onError={(event) => onMediaError(event.currentTarget.error?.code ?? 4)}
            />
          ) : (
            <div className="semantic-state state-warning reader-media-error" role="alert">
              <strong>{errorInfo.title}</strong>
              <p>{errorInfo.detail}</p>
              <div className="button-row">
                <button
                  type="button"
                  className="button button-primary button-small"
                  onClick={handleRetryClick}
                >
                  {zhReader ? "重试加载" : "Retry"}
                </button>
                {onOpenTranscriptDrawer ? (
                  <button
                    type="button"
                    className="button button-secondary button-small"
                    onClick={onOpenTranscriptDrawer}
                  >
                    {zhReader ? "改看右侧原始字幕" : "View transcript instead"}
                  </button>
                ) : null}
              </div>
            </div>
          )}
          <button
            type="button"
            className="button button-ghost button-small"
            onClick={onHidePlayer}
          >
            {zhReader ? "收起播放器" : "Hide player"}
          </button>
        </div>
      ) : isPlayableLocalAudio && playing ? (
        <div className="reader-inline-player-wrap is-audio">
          {errorInfo === null ? (
            <audio
              key={`audio-${localMediaSrc}-${retryNonce}`}
              className="reader-inline-audio"
              controls
              autoPlay
              preload="metadata"
              src={localMediaSrc}
              onError={(event) => onMediaError(event.currentTarget.error?.code ?? 4)}
            />
          ) : (
            <div className="semantic-state state-warning reader-media-error" role="alert">
              <strong>{errorInfo.title}</strong>
              <p>{errorInfo.detail}</p>
              <div className="button-row">
                <button
                  type="button"
                  className="button button-primary button-small"
                  onClick={handleRetryClick}
                >
                  {zhReader ? "重试加载" : "Retry"}
                </button>
                {onOpenTranscriptDrawer ? (
                  <button
                    type="button"
                    className="button button-secondary button-small"
                    onClick={onOpenTranscriptDrawer}
                  >
                    {zhReader ? "改看右侧原始字幕" : "View transcript instead"}
                  </button>
                ) : null}
              </div>
            </div>
          )}
          <button
            type="button"
            className="button button-ghost button-small"
            onClick={onHidePlayer}
          >
            {zhReader ? "收起音频条" : "Hide audio player"}
          </button>
        </div>
      ) : (
        <div className={`reader-media-poster${heroPosterUrl ? "" : " is-editorial-card"}`}>
          {heroPosterUrl ? (
            <img
              className="reader-media-poster-img"
              src={heroPosterUrl}
              alt={title ?? (zhReader ? "视频封面预览" : "Video preview frame")}
            />
          ) : null}
          <div className="reader-media-poster-overlay">
            <div className="reader-media-poster-top">
              <span
                className={`provider-glyph provider-${(provider ?? "YOUTUBE").toLowerCase()}`}
                aria-hidden="true"
              >
                <PhosphorIcon
                  name={isLocalMedia ? "play-circle" : isBilibili ? "television" : "youtube-logo"}
                  size={18}
                />
              </span>
              {durationSeconds != null ? (
                <span className="reader-media-duration tabular-nums">
                  {formatHumanDuration(durationSeconds)}
                </span>
              ) : null}
            </div>
            <div className="reader-media-editorial-copy">
              <p className="reader-media-poster-title">
                {isLocalMedia
                  ? zhReader
                    ? "本机原始媒体已保存 · 点击直接页内播放"
                    : "Local media stored on device · Play inline"
                  : channelName || (isBilibili ? "Bilibili" : "YouTube")}
              </p>
              {!heroPosterUrl ? (
                <p className="reader-media-editorial-status tabular-nums">
                  {transcriptAvailable && evidenceCount > 0
                    ? zhReader
                      ? `已保存可核验原文 · ${evidenceCount} 条原话证据`
                      : `Verified transcript · ${evidenceCount} evidence spans`
                    : transcriptAvailable
                      ? zhReader
                        ? "已保存可核验原文"
                        : "Verified transcript saved"
                      : zhReader
                        ? "按需打开原视频观看"
                        : "Watch original video on demand"}
                </p>
              ) : null}
            </div>
            <div className="reader-media-poster-actions">
              {isPlayableLocalVideo || isPlayableLocalAudio ? (
                <button
                  type="button"
                  className="button button-primary button-small"
                  onClick={onPlayStart}
                >
                  <PhosphorIcon name="play-circle" weight="fill" size={14} />
                  {isPlayableLocalAudio
                    ? zhReader
                      ? "页内试听原音频"
                      : "Play audio inline"
                    : zhReader
                      ? "页内播放原视频"
                      : "Play video inline"}
                </button>
              ) : sourceUrl ? (
                <a
                  className="button button-primary button-small"
                  href={sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  <PhosphorIcon name="play-circle" weight="fill" size={14} />
                  {zhReader ? "在原站播放原视频 ↗" : "Watch original video ↗"}
                </a>
              ) : null}
              {!heroPosterUrl && evidenceCount > 0 && onOpenEvidenceDrawer ? (
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={onOpenEvidenceDrawer}
                >
                  {zhReader ? "核对原话证据" : "Inspect evidence"}
                </button>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
