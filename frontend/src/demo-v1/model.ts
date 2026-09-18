export type Experience = "onboarding" | "workspace";

export type Route =
  | "home"
  | "following"
  | "following-add"
  | "following-ai-explained"
  | "following-bilibili-creator"
  | "following-agentbuilder"
  | "following-local-conference"
  | "following-practical-ai"
  | "intelligence"
  | "intelligence-detail"
  | "intelligence-detail-pricing"
  | "topics"
  | "topic-detail"
  | "content-youtube-task-ui"
  | "content-bilibili-task-ui"
  | "content-x-task-ui"
  | "content-youtube-evaluation"
  | "content-youtube-failure"
  | "content-local-conference"
  | "content-practical-ai"
  | "content-youtube-pricing"
  | "content-bilibili-pricing"
  | "content-x-pricing"
  | "content-youtube-agent-pricing-en"
  | "research"
  | "research-result"
  | "search"
  | "settings";

export type AsyncState = "idle" | "checking" | "success" | "error";
export type SettingsSection = "general" | "ai" | "providers" | "analysis" | "preferences" | "data" | "system";
export type FollowingTab = "overview" | "content" | "intelligence" | "topics";
export type ResearchScopeMode = "library" | "current" | "specified";
export type SpecifiedScope = "following" | "content" | "intelligence" | "topic";
export type ResearchContext = { kind: "Topic" | "洞察" | "关注" | "内容"; label: string };

/**
 * Language model:
 * - UI language (界面语言) controls product chrome text.
 * - Source language (源语言) is intrinsic to each Content/Evidence fixture.
 * - Content output language (内容输出语言) controls the language of generated
 *   artifacts (summary, key points, chapters, Intelligence, Topic, Research).
 * These three concepts are independent; changing UI language must not imply
 * changing how source content is stored.
 */
export type Language = "简体中文" | "English";
export type EvidenceDisplay = "译文" | "双语" | "原文";
export type LanguageSettings = {
  uiLanguage: Language;
  outputLanguage: Language;
  evidenceDisplay: EvidenceDisplay;
};
export type FollowingLanguageMode = "global" | "custom";

export type SearchScope = "all" | "following" | "content" | "intelligence" | "topic" | "research" | "evidence";
export type SearchResultType = "关注" | "内容" | "洞察" | "主题" | "调研" | "Evidence";

export const defaultLanguageSettings: LanguageSettings = {
  uiLanguage: "简体中文",
  outputLanguage: "简体中文",
  evidenceDisplay: "双语",
};

export const contentRoutes: Record<string, Route> = {
  "content-youtube-task-ui": "content-youtube-task-ui",
  "content-bilibili-task-ui": "content-bilibili-task-ui",
  "content-x-task-ui": "content-x-task-ui",
  "content-youtube-evaluation": "content-youtube-evaluation",
  "content-youtube-failure": "content-youtube-failure",
  "content-local-conference": "content-local-conference",
  "content-practical-ai": "content-practical-ai",
  "content-youtube-pricing": "content-youtube-pricing",
  "content-bilibili-pricing": "content-bilibili-pricing",
  "content-x-pricing": "content-x-pricing",
  "content-youtube-agent-pricing-en": "content-youtube-agent-pricing-en",
};

export const followingRoutes: Record<string, Route> = {
  "following-ai-explained": "following-ai-explained",
  "following-bilibili-creator": "following-bilibili-creator",
  "following-agentbuilder": "following-agentbuilder",
  "following-local-conference": "following-local-conference",
  "following-practical-ai": "following-practical-ai",
};
