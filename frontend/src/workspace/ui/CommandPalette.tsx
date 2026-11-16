/**
 * Command Palette & Fuzzy Command Scoring (ADAPT).
 * Upstream scoring & keyboard state machine: https://github.com/dip/cmdk
 *   Commit: dd2250ed608443e8f32bafc5fa2d1d07a3746aa3 (MIT, Copyright (c) 2022 Paco Coursey)
 * Upstream visual dialog anatomy: https://github.com/shadcn-ui/ui
 *   Commit: dd41d19e2f80ff6891951f7ced74c2c9a650b065 (MIT, Copyright (c) 2023 shadcn)
 * Modifications: TypeScript strict typing, CJK/Chinese substring boost, zero-dependency React 19 dialog,
 *   and lazy library indexing (/videos, /intelligence, /topics) only when opened.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api/client";
import { useUiLanguage } from "../uiLanguage";
import { PhosphorIcon, PhosphorIconName } from "./phosphorIcons";

const SCORE_CONTINUE_MATCH = 1;
const SCORE_SPACE_WORD_JUMP = 0.9;
const SCORE_NON_SPACE_WORD_JUMP = 0.8;
const SCORE_CHARACTER_JUMP = 0.17;
const SCORE_TRANSPOSITION = 0.1;
const PENALTY_SKIPPED = 0.999;
const PENALTY_CASE_MISMATCH = 0.9999;
const PENALTY_NOT_COMPLETE = 0.99;

const IS_GAP_REGEXP = /[\\/_+.#"@[\]({&]/;
const COUNT_GAPS_REGEXP = /[\\/_+.#"@[\]({&]/g;
const IS_SPACE_REGEXP = /[\s-]/;
const COUNT_SPACE_REGEXP = /[\s-]/g;
const HAS_CJK_REGEXP = /[\u3400-\u9fff]/;

function commandScoreInner(
  str: string,
  abbreviation: string,
  lowerString: string,
  lowerAbbreviation: string,
  stringIndex: number,
  abbreviationIndex: number,
  memoizedResults: Record<string, number>,
): number {
  if (abbreviationIndex === abbreviation.length) {
    if (stringIndex === str.length) {
      return SCORE_CONTINUE_MATCH;
    }
    return PENALTY_NOT_COMPLETE;
  }

  const memoizeKey = `${stringIndex},${abbreviationIndex}`;
  if (memoizedResults[memoizeKey] !== undefined) {
    return memoizedResults[memoizeKey];
  }

  const abbreviationChar = lowerAbbreviation.charAt(abbreviationIndex);
  let index = lowerString.indexOf(abbreviationChar, stringIndex);
  let highScore = 0;

  while (index >= 0) {
    let score = commandScoreInner(
      str,
      abbreviation,
      lowerString,
      lowerAbbreviation,
      index + 1,
      abbreviationIndex + 1,
      memoizedResults,
    );
    if (score > highScore) {
      if (index === stringIndex) {
        score *= SCORE_CONTINUE_MATCH;
      } else if (IS_GAP_REGEXP.test(str.charAt(index - 1))) {
        score *= SCORE_NON_SPACE_WORD_JUMP;
        const wordBreaks = str.slice(stringIndex, index - 1).match(COUNT_GAPS_REGEXP);
        if (wordBreaks && stringIndex > 0) {
          score *= Math.pow(PENALTY_SKIPPED, wordBreaks.length);
        }
      } else if (IS_SPACE_REGEXP.test(str.charAt(index - 1))) {
        score *= SCORE_SPACE_WORD_JUMP;
        const spaceBreaks = str.slice(stringIndex, index - 1).match(COUNT_SPACE_REGEXP);
        if (spaceBreaks && stringIndex > 0) {
          score *= Math.pow(PENALTY_SKIPPED, spaceBreaks.length);
        }
      } else {
        score *= SCORE_CHARACTER_JUMP;
        if (stringIndex > 0) {
          score *= Math.pow(PENALTY_SKIPPED, index - stringIndex);
        }
      }

      if (str.charAt(index) !== abbreviation.charAt(abbreviationIndex)) {
        score *= PENALTY_CASE_MISMATCH;
      }
    }

    if (
      (score < SCORE_TRANSPOSITION &&
        lowerString.charAt(index - 1) === lowerAbbreviation.charAt(abbreviationIndex + 1)) ||
      (lowerAbbreviation.charAt(abbreviationIndex + 1) === lowerAbbreviation.charAt(abbreviationIndex) &&
        lowerString.charAt(index - 1) !== lowerAbbreviation.charAt(abbreviationIndex))
    ) {
      const transposedScore = commandScoreInner(
        str,
        abbreviation,
        lowerString,
        lowerAbbreviation,
        index + 1,
        abbreviationIndex + 2,
        memoizedResults,
      );
      if (transposedScore * SCORE_TRANSPOSITION > score) {
        score = transposedScore * SCORE_TRANSPOSITION;
      }
    }

    if (score > highScore) {
      highScore = score;
    }
    index = lowerString.indexOf(abbreviationChar, index + 1);
  }

  memoizedResults[memoizeKey] = highScore;
  return highScore;
}

function formatInput(str: string): string {
  return str.toLowerCase().replace(COUNT_SPACE_REGEXP, " ");
}

export function commandScore(str: string, abbreviation: string, aliases: string[] = []): number {
  const trimmed = abbreviation.trim();
  if (!trimmed) return 1;
  const full = aliases.length > 0 ? `${str} ${aliases.join(" ")}` : str;
  const lowerFull = formatInput(full);
  const lowerQuery = formatInput(trimmed);
  const directIdx = lowerFull.indexOf(lowerQuery);
  if (directIdx === 0) return 0.995;
  if (directIdx > 0 && HAS_CJK_REGEXP.test(trimmed)) {
    return Math.max(0.86, 0.94 - Math.min(directIdx, 40) * 0.0015);
  }
  const base = commandScoreInner(full, trimmed, lowerFull, lowerQuery, 0, 0, {});
  if (directIdx > 0) {
    return Math.max(base, 0.82 - Math.min(directIdx, 40) * 0.001);
  }
  return base;
}

export type CommandPaletteAction = {
  id: string;
  group: "navigation" | "actions" | "content" | "research" | "intelligence" | "topics";
  label: string;
  subtitle?: string;
  shortcut?: string;
  icon: PhosphorIconName;
  aliases?: string[];
  rankBonus?: number;
  onSelect: () => void;
};

type PaletteVideo = {
  video_id: string;
  provider?: string;
  work_kind?: string;
  channel_name?: string | null;
  title?: string | null;
  duration_seconds?: number | null;
  ai_brief?: {
    headline_zh?: string;
    score?: number;
    recommendation_tier?: string;
    is_short_noise?: boolean;
    starred?: boolean;
    is_read?: boolean;
    topic_cluster_zh?: string;
    topics_zh?: string[];
  } | null;
};

type PaletteIntelligence = {
  intelligence_id?: string;
  status: string;
  trusted?: boolean;
  linked_topics?: { topic_id: string; name: string }[];
  card?: {
    core_conclusion: string;
    video_title?: string;
    source_display_name?: string;
  };
};

type PaletteTopic = {
  topic_id: string;
  name: string;
  pinned?: boolean;
  ai_evolution?: {
    video_count?: number;
    must_watch_count?: number;
    latest_headline_zh?: string;
  } | null;
};

type PaletteResearchSession = {
  session_id: string;
  question: string;
  pinned?: boolean;
  scope_label_zh?: string;
  answer_zh?: string;
  citations?: {
    video_title?: string;
    channel_name?: string;
  }[];
};

type PaletteChannelScope = {
  key: string;
  label: string;
  video_count?: number;
  count?: number;
};

export function CommandPalette({
  open,
  onClose,
  staticActions,
  onOpenContent,
  onOpenIntelligence,
  onOpenTopic,
  onOpenResearchSession,
  onFilterContentByChannel,
}: {
  open: boolean;
  onClose: () => void;
  staticActions: CommandPaletteAction[];
  onOpenContent: (videoId: string) => void;
  onOpenIntelligence: (intelligenceId: string) => void;
  onOpenTopic: (topicId: string) => void;
  onOpenResearchSession?: (sessionId: string) => void;
  onFilterContentByChannel?: (channelKey: string) => void;
}) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const [videos, setVideos] = useState<PaletteVideo[]>([]);
  const [insights, setInsights] = useState<PaletteIntelligence[]>([]);
  const [topics, setTopics] = useState<PaletteTopic[]>([]);
  const [qaSessions, setQaSessions] = useState<PaletteResearchSession[]>([]);
  const [channelScopes, setChannelScopes] = useState<PaletteChannelScope[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setActiveIndex(0);
      return;
    }
    let alive = true;
    queueMicrotask(() => inputRef.current?.focus());
    api<{ videos?: PaletteVideo[] }>("/videos")
      .then((res) => {
        if (!alive || !Array.isArray(res?.videos)) return;
        const realVideos = res.videos.filter(
          (v) => v.work_kind !== "DURABLE_CONTENT_IDENTITY",
        );
        const sortedVideos = [...realVideos].sort((a, b) => {
          const aShort = Boolean(a.ai_brief?.is_short_noise);
          const bShort = Boolean(b.ai_brief?.is_short_noise);
          if (aShort !== bShort) return aShort ? 1 : -1;
          const aStar = Boolean(a.ai_brief?.starred);
          const bStar = Boolean(b.ai_brief?.starred);
          if (aStar !== bStar) return aStar ? -1 : 1;
          const aScore = typeof a.ai_brief?.score === "number" ? a.ai_brief.score : -1;
          const bScore = typeof b.ai_brief?.score === "number" ? b.ai_brief.score : -1;
          return bScore - aScore;
        });
        setVideos(sortedVideos.slice(0, 200));
      })
      .catch(() => {});

    api<{ intelligence?: PaletteIntelligence[] }>("/intelligence")
      .then((res) => {
        if (!alive || !Array.isArray(res?.intelligence)) return;
        setInsights(
          res.intelligence
            .filter(
              (item) =>
                item.status === "AVAILABLE" &&
                item.trusted &&
                item.intelligence_id &&
                item.card?.core_conclusion,
            )
            .slice(0, 100),
        );
      })
      .catch(() => {});

    api<{ topics?: PaletteTopic[] }>("/topics")
      .then((res) => {
        if (!alive || !Array.isArray(res?.topics)) return;
        setTopics(res.topics.slice(0, 50));
      })
      .catch(() => {});

    api<{
      sessions?: PaletteResearchSession[];
      scope_options?: { channels?: PaletteChannelScope[] };
    }>("/workspace-ai/research/sessions")
      .then((res) => {
        if (!alive || !res || typeof res !== "object") return;
        if (Array.isArray(res.sessions)) {
          setQaSessions(
            res.sessions
              .filter(
                (s) =>
                  Boolean(s) &&
                  typeof s.session_id === "string" &&
                  s.session_id.trim().length > 0 &&
                  typeof s.question === "string" &&
                  s.question.trim().length > 0,
              )
              .slice(0, 40),
          );
        }
        const rawChannels = res.scope_options?.channels;
        if (Array.isArray(rawChannels)) {
          setChannelScopes(
            rawChannels
              .map((ch) => {
                const countVal =
                  typeof ch?.video_count === "number"
                    ? ch.video_count
                    : typeof ch?.count === "number"
                      ? ch.count
                      : 0;
                return {
                  key: typeof ch?.key === "string" ? ch.key : "",
                  label: typeof ch?.label === "string" ? ch.label : "",
                  video_count: countVal,
                  count: countVal,
                };
              })
              .filter(
                (ch) =>
                  ch.key.trim().length > 0 &&
                  ch.label.trim().length > 0 &&
                  (ch.video_count ?? 0) > 0,
              )
              .slice(0, 20),
          );
        }
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [open]);

  const allItems = useMemo<CommandPaletteAction[]>(() => {
    const dynamicContent: CommandPaletteAction[] = videos.map(video => {
      const brief = video.ai_brief;
      const providerLabel =
        video.provider === "LOCAL"
          ? t("Local")
          : video.provider === "BILIBILI"
            ? t("Bilibili")
            : "YouTube";
      const scoreBadge =
        typeof brief?.score === "number" ? `${brief.score.toFixed(1)}` : "";
      const starMark = brief?.starred ? "★" : "";
      const headlineSnippet = brief?.headline_zh
        ? brief.headline_zh.length > 44
          ? `${brief.headline_zh.slice(0, 44)}…`
          : brief.headline_zh
        : "";
      const rankBonus =
        !brief?.is_short_noise && (brief?.starred || brief?.recommendation_tier === "MUST_WATCH")
          ? 0.03
          : brief?.is_short_noise
            ? -0.02
            : 0;
      return {
        id: `content:${video.video_id}`,
        group: "content",
        label: video.title || video.video_id,
        subtitle: [
          [starMark, scoreBadge].filter(Boolean).join(" "),
          providerLabel,
          video.channel_name,
          headlineSnippet,
        ]
          .filter(Boolean)
          .join(" · "),
        icon: video.provider === "LOCAL" ? "file-text" : video.provider === "BILIBILI" ? "television" : "play-circle",
        aliases: [
          video.video_id,
          video.channel_name ?? "",
          video.provider ?? "",
          brief?.headline_zh ?? "",
          brief?.topic_cluster_zh ?? "",
          ...(brief?.topics_zh ?? []),
          brief?.starred ? "已收藏 收藏 starred" : "",
          brief && !brief.is_read && !brief.is_short_noise ? "未读 unread" : "",
          brief?.recommendation_tier === "MUST_WATCH" ? "必看 must watch" : "",
        ].filter(Boolean),
        rankBonus,
        onSelect: () => onOpenContent(video.video_id),
      };
    });

    const dynamicInsights: CommandPaletteAction[] = insights.map(item => {
      const topicNames = (item.linked_topics ?? [])
        .map(tp => tp.name?.trim())
        .filter((name): name is string => Boolean(name));
      const topicBadge = topicNames.length > 0 ? `[[${topicNames[0]}]]` : undefined;
      const rawSource = item.card?.source_display_name?.trim();
      const localizedSource = rawSource ? t(rawSource) : undefined;
      return {
        id: `intel:${item.intelligence_id}`,
        group: "intelligence",
        label: item.card!.core_conclusion,
        subtitle:
          [topicBadge, localizedSource, item.card?.video_title]
            .filter(Boolean)
            .join(" · ") || undefined,
        icon: "sparkle",
        aliases: [
          item.card?.video_title ?? "",
          rawSource ?? "",
          localizedSource ?? "",
          ...topicNames,
        ].filter(Boolean),
        onSelect: () => onOpenIntelligence(item.intelligence_id!),
      };
    });

    const dynamicTopics: CommandPaletteAction[] = topics.map(topic => {
      const evoCount = topic.ai_evolution?.video_count ?? 0;
      const evoMeta =
        evoCount > 0
          ? zh
            ? `${evoCount} 篇 · ${topic.ai_evolution?.must_watch_count ?? 0} 必看`
            : `${evoCount} items · ${topic.ai_evolution?.must_watch_count ?? 0} must-watch`
          : undefined;
      return {
        id: `topic:${topic.topic_id}`,
        group: "topics",
        label: topic.name,
        subtitle: [topic.pinned ? t("Pinned") : undefined, evoMeta].filter(Boolean).join(" · ") || undefined,
        icon: "stack",
        aliases: [topic.topic_id, topic.ai_evolution?.latest_headline_zh ?? ""].filter(Boolean),
        onSelect: () => onOpenTopic(topic.topic_id),
      };
    });

    const dynamicChannelActions: CommandPaletteAction[] = onFilterContentByChannel
      ? channelScopes.map((ch) => {
          const itemCount = ch.video_count ?? ch.count ?? 0;
          return {
            id: `act:channel:${ch.key}`,
            group: "actions",
            label: zh ? `筛选频道干货：${ch.label}` : `Filter channel: ${ch.label}`,
            subtitle: zh
              ? `${itemCount} 篇长视频干货 · 在内容库中查看`
              : `${itemCount} long-form items in Content`,
            icon: "rss",
            aliases: [ch.key, ch.label, "channel", "频道", "干货", "filter"],
            rankBonus: 0.15,
            onSelect: () => onFilterContentByChannel(ch.key),
          };
        })
      : [];

    const dynamicResearch: CommandPaletteAction[] = onOpenResearchSession
      ? qaSessions.map((session) => {
          const citeCount = session.citations?.length ?? 0;
          const isPinned = Boolean(session.pinned);
          return {
            id: `qa:${session.session_id}`,
            group: "research",
            label: session.question,
            subtitle:
              [
                isPinned ? (zh ? "已置顶" : "Pinned") : undefined,
                session.scope_label_zh,
                citeCount > 0
                  ? zh
                    ? `${citeCount} 处时间轴引用`
                    : `${citeCount} citations`
                  : undefined,
              ]
                .filter(Boolean)
                .join(" · ") || undefined,
            icon: isPinned ? "push-pin" : "quotes",
            aliases: [
              isPinned ? "已置顶 置顶 pinned" : "",
              session.answer_zh?.slice(0, 140) ?? "",
              ...(session.citations ?? []).map(
                (c) => `${c.video_title ?? ""} ${c.channel_name ?? ""}`,
              ),
            ].filter(Boolean),
            rankBonus: isPinned ? 0.06 : 0.02,
            onSelect: () => onOpenResearchSession(session.session_id),
          };
        })
      : [];

    return [
      ...staticActions,
      ...dynamicChannelActions,
      ...dynamicContent,
      ...dynamicResearch,
      ...dynamicInsights,
      ...dynamicTopics,
    ];
  }, [
    staticActions,
    channelScopes,
    videos,
    qaSessions,
    insights,
    topics,
    zh,
    t,
    onOpenContent,
    onOpenIntelligence,
    onOpenTopic,
    onOpenResearchSession,
    onFilterContentByChannel,
  ]);

  const filteredItems = useMemo(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      // Show concise default set when query is empty
      return [
        ...staticActions,
        ...allItems.filter(item => item.group === "content").slice(0, 6),
        ...allItems.filter(item => item.group === "research").slice(0, 3),
        ...allItems.filter(item => item.group === "intelligence").slice(0, 4),
        ...allItems.filter(item => item.group === "topics").slice(0, 4),
      ];
    }
    return allItems
      .map(item => {
        const rawScore = commandScore(
          item.label,
          trimmed,
          [item.subtitle ?? "", ...(item.aliases ?? [])],
        );
        return {
          item,
          rawScore,
          score: rawScore > 0.05 ? rawScore + (item.rankBonus ?? 0) : rawScore,
        };
      })
      .filter(entry => entry.rawScore > 0.05)
      .sort((a, b) => b.score - a.score)
      .slice(0, 24)
      .map(entry => entry.item);
  }, [allItems, staticActions, query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  if (!open) return null;

  const boundedIndex = filteredItems.length ? Math.min(activeIndex, filteredItems.length - 1) : -1;
  const activeItem = boundedIndex >= 0 ? filteredItems[boundedIndex] : undefined;

  const groupTitle: Record<CommandPaletteAction["group"], string> = {
    navigation: t("Quick navigation"),
    actions: t("Quick actions"),
    content: t("Content library"),
    research: zh ? "AI 深度问答存档" : "Saved AI Q&A",
    intelligence: t("Verified Intelligence"),
    topics: t("Topics"),
  };

  const groupsOrder: CommandPaletteAction["group"][] = [
    "navigation",
    "actions",
    "content",
    "research",
    "intelligence",
    "topics",
  ];

  // Build visual group sections while preserving flat index for keyboard navigation
  let runningIdx = 0;
  const groupedSections = groupsOrder
    .map(group => {
      const members = filteredItems.filter(item => item.group === group);
      const indexed = members.map(item => ({ item, flatIndex: runningIdx++ }));
      return { group, indexed };
    })
    .filter(section => section.indexed.length > 0);

  // Use groupedSections' flat ordering for Enter/Arrow consistency
  const orderedFlat = groupedSections.flatMap(section => section.indexed.map(entry => entry.item));
  const resolvedActive = boundedIndex >= 0 ? orderedFlat[boundedIndex] : undefined;

  const executeItem = (target: CommandPaletteAction | undefined) => {
    if (!target) return;
    onClose();
    target.onSelect();
  };

  return (
    <div
      className="overlay cmdk-overlay"
      onMouseDown={event => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="cmdk-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={t("Command palette and library search")}
        onKeyDown={event => {
          if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            onClose();
            return;
          }
          if (!orderedFlat.length) return;
          if (event.key === "ArrowDown") {
            event.preventDefault();
            const next = (boundedIndex + 1) % orderedFlat.length;
            setActiveIndex(next);
            listRef.current?.querySelector<HTMLElement>(`[data-cmdk-idx="${next}"]`)?.scrollIntoView({ block: "nearest" });
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            const prev = (boundedIndex - 1 + orderedFlat.length) % orderedFlat.length;
            setActiveIndex(prev);
            listRef.current?.querySelector<HTMLElement>(`[data-cmdk-idx="${prev}"]`)?.scrollIntoView({ block: "nearest" });
          } else if (event.key === "Home") {
            event.preventDefault();
            setActiveIndex(0);
          } else if (event.key === "End") {
            event.preventDefault();
            setActiveIndex(orderedFlat.length - 1);
          } else if (event.key === "Enter") {
            event.preventDefault();
            executeItem(resolvedActive ?? activeItem);
          }
        }}
      >
        <div className="cmdk-input-wrap">
          <PhosphorIcon name="magnifying-glass" size={17} className="cmdk-search-icon" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-controls="cmdk-listbox"
            aria-activedescendant={resolvedActive ? `cmdk-opt-${resolvedActive.id}` : undefined}
            aria-label={t("Search pages, Content, Intelligence, or actions")}
            placeholder={t("Search pages, videos, insights, Topics, or type a command…")}
            className="cmdk-input"
            value={query}
            onChange={event => setQuery(event.target.value)}
          />
          <kbd className="cmdk-kbd" aria-hidden="true">ESC</kbd>
        </div>

        <div id="cmdk-listbox" ref={listRef} role="listbox" className="cmdk-list" aria-label={t("Command results")}>
          {groupedSections.length === 0 ? (
            <div className="cmdk-empty">{t("No matching commands or library items.")}</div>
          ) : (
            groupedSections.map(section => (
              <div key={section.group} className="cmdk-group" role="group" aria-label={groupTitle[section.group]}>
                <div className="cmdk-group-heading" aria-hidden="true">{groupTitle[section.group]}</div>
                {section.indexed.map(({ item, flatIndex }) => {
                  const isSelected = flatIndex === boundedIndex;
                  return (
                    <div
                      key={item.id}
                      id={`cmdk-opt-${item.id}`}
                      data-cmdk-idx={flatIndex}
                      role="option"
                      aria-selected={isSelected}
                      className={`cmdk-item${isSelected ? " is-selected" : ""}`}
                      onMouseEnter={() => setActiveIndex(flatIndex)}
                      onClick={() => executeItem(item)}
                    >
                      <PhosphorIcon
                        name={item.icon}
                        weight={isSelected ? "fill" : "regular"}
                        size={16}
                        className="cmdk-item-icon"
                      />
                      <div className="cmdk-item-copy">
                        <span className="cmdk-item-label">{item.label}</span>
                        {item.subtitle && <small className="cmdk-item-sub">{item.subtitle}</small>}
                      </div>
                      {item.shortcut && <kbd className="cmdk-kbd" aria-hidden="true">{item.shortcut}</kbd>}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <footer className="cmdk-footer" aria-hidden="true">
          <span><kbd className="cmdk-kbd">↑↓</kbd> {t("Select")}</span>
          <span><kbd className="cmdk-kbd">↵</kbd> {t("Open")}</span>
          <span><kbd className="cmdk-kbd">ESC</kbd> {t("Close")}</span>
        </footer>
      </div>
    </div>
  );
}
