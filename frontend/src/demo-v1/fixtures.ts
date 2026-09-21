import type { Language, SearchResultType } from "./model";

export type Provider = "YouTube" | "B站" | "X" | "Local";
export type FollowingGroup = "AI 模型" | "AI Agent" | "产品与商业" | "学习" | "个人收藏";
export type FollowingStatus = "正常" | "处理中" | "需要处理" | "已暂停";

export type Following = {
  id: string;
  name: string;
  provider: Provider;
  objectType: string;
  handle?: string;
  group: FollowingGroup;
  focus: string[];
  focusMode: "default" | "custom";
  processing: { summary: boolean; intelligence: boolean; topics: boolean };
  lastUpdated: string;
  newContent: number;
  newIntelligence: number;
  intelligenceIds: string[];
  topicIds: string[];
  status: FollowingStatus;
  summary: string;
  /** Search-only keywords; never rendered as product copy. */
  searchTags?: string[];
};

export type ContentItem = {
  id: string;
  followingId: string;
  provider: Provider;
  kind: string;
  title: string;
  publishedAt: string;
  positionLabel: string;
  status: "已分析" | "分析中" | "等待处理" | "失败";
  intelligenceIds: string[];
  topicIds: string[];
  /** Language the original source was published in. Never mutated by output-language settings. */
  sourceLanguage: Language;
  summary?: {
    oneLine: string;
    keyPoints: string[];
    chapters: Array<{ time: string; title: string; context: string }>;
    detailLevel: "完整" | "简要";
  };
  transcript: Array<{ position: string; text: string; evidenceId?: string }>;
  /**
   * On-demand translated transcript. Only present for fixtures whose
   * sourceLanguage differs from the default output language. Populated by the
   * "翻译完整字幕" mock action; never fetched from a real model.
   */
  translatedTranscript?: Array<{ position: string; text: string; evidenceId?: string }>;
  searchTags?: string[];
};

export type EvidenceItem = {
  id: string;
  contentId: string;
  followingId: string;
  provider: Provider;
  position: string;
  /** Authoritative excerpt in the source's original language. */
  quote: string;
  context: string;
  strength: string;
  stance: "supporting" | "contradicting" | "conditional";
  sourceLanguage: Language;
  /**
   * Optional translated excerpt shown when the user's output language differs
   * from sourceLanguage. Translation is a display aid, not a new Evidence
   * record — the original quote + position remain authoritative.
   */
  translatedQuote?: string;
  translatedContext?: string;
  searchTags?: string[];
};

const defaultProcessing = { summary: true, intelligence: true, topics: true };

export const followings: Following[] = [
  {
    id: "following-ai-explained",
    name: "AI Explained",
    provider: "YouTube",
    objectType: "Channel",
    handle: "@aiexplained",
    group: "AI Agent",
    focus: ["Agent", "模型能力", "商业化", "Benchmark"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "2 小时前",
    newContent: 3,
    newIntelligence: 1,
    intelligenceIds: ["intel-task-interface", "intel-evaluation", "intel-outcome-pricing"],
    topicIds: ["topic-agent-product"],
    status: "正常",
    summary: "长期跟踪 Agent 产品、模型能力与产品界面的深度频道。",
    searchTags: ["AI Explained", "Agent", "商业化", "模型能力", "Benchmark", "YouTube", "英文频道"],
  },
  {
    id: "following-bilibili-creator",
    name: "某 AI UP 主",
    provider: "B站",
    objectType: "UP主",
    handle: "UID 2188001",
    group: "AI Agent",
    focus: ["Agent", "产品设计", "中文实践"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "1 小时前",
    newContent: 3,
    newIntelligence: 1,
    intelligenceIds: ["intel-task-interface", "intel-outcome-pricing"],
    topicIds: ["topic-agent-product"],
    status: "正常",
    summary: "从中文产品实践角度拆解 AI Agent 的工作流与交付体验。",
    searchTags: ["Agent", "商业化", "产品设计", "中文实践", "B站"],
  },
  {
    id: "following-agentbuilder",
    name: "@agentbuilder",
    provider: "X",
    objectType: "Account",
    group: "AI Agent",
    focus: ["Agent", "新产品", "用户采用"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "28 分钟前",
    newContent: 5,
    newIntelligence: 1,
    intelligenceIds: ["intel-task-interface", "intel-outcome-pricing"],
    topicIds: ["topic-agent-product"],
    status: "正常",
    summary: "持续发布 Agent 产品设计与真实用户采用观察。",
    searchTags: ["Agent", "商业化", "新产品", "用户采用", "X"],
  },
  {
    id: "following-local-conference",
    name: "本地 AI Conference 录像",
    provider: "Local",
    objectType: "Video",
    group: "学习",
    focus: ["Agent", "产品趋势", "行业观点"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "昨天",
    newContent: 1,
    newIntelligence: 1,
    intelligenceIds: ["intel-evaluation"],
    topicIds: ["topic-agent-product"],
    status: "处理中",
    summary: "保存在本机的 2026 AI 产品会议录像集合。",
    searchTags: ["Agent", "会议", "本地", "产品趋势"],
  },
  {
    id: "following-practical-ai",
    name: "Practical AI Engineering",
    provider: "YouTube",
    objectType: "Channel",
    handle: "@practicalai",
    group: "学习",
    focus: ["Agent", "技术实现", "工作流"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "刚刚",
    newContent: 1,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "处理中",
    summary: "通过“添加关注”流程创建的连贯 Demo fixture。",
    searchTags: ["Practical AI", "Agent", "技术实现", "工作流", "英语学习"],
  },
  {
    id: "following-latent-space",
    name: "Latent Space",
    provider: "YouTube",
    objectType: "Channel",
    handle: "@latent-space",
    group: "AI 模型",
    focus: ["模型能力", "推理", "开发者生态"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "昨天",
    newContent: 2,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "正常",
    summary: "跟踪前沿模型、推理能力与开发者工具生态。",
    searchTags: ["Latent Space", "模型能力", "推理", "开发者生态"],
  },
  {
    id: "following-lennys-podcast",
    name: "Lenny's Podcast",
    provider: "YouTube",
    objectType: "Channel",
    handle: "@lennyspodcast",
    group: "产品与商业",
    focus: ["新产品", "增长", "定价变化"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "3 天前",
    newContent: 1,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "正常",
    summary: "产品负责人访谈与增长、定价实践。",
    searchTags: ["Lenny", "产品", "增长", "定价变化", "商业化"],
  },
  {
    id: "following-two-minute-papers",
    name: "Two Minute Papers",
    provider: "YouTube",
    objectType: "Channel",
    handle: "@TwoMinutePapers",
    group: "AI 模型",
    focus: ["模型能力", "Benchmark", "多模态"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "4 天前",
    newContent: 0,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "正常",
    summary: "用短视频跟踪研究成果与能力边界。",
    searchTags: ["Two Minute Papers", "模型能力", "Benchmark", "多模态"],
  },
  {
    id: "following-openai",
    name: "OpenAI",
    provider: "YouTube",
    objectType: "Channel",
    handle: "@OpenAI",
    group: "AI 模型",
    focus: ["模型发布", "模型能力", "Benchmark"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "5 天前",
    newContent: 0,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "正常",
    summary: "官方模型发布、演示与技术说明。",
    searchTags: ["OpenAI", "模型发布", "官方"],
  },
  {
    id: "following-y-combinator",
    name: "Y Combinator",
    provider: "YouTube",
    objectType: "Channel",
    handle: "@ycombinator",
    group: "产品与商业",
    focus: ["创业", "商业化", "增长"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "1 周前",
    newContent: 0,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "正常",
    summary: "创业公司产品、增长与商业模式观察。",
    searchTags: ["Y Combinator", "创业", "商业化", "增长"],
  },
  {
    id: "following-ai-product-observer",
    name: "AI 产品观察室",
    provider: "B站",
    objectType: "UP主",
    handle: "UID 8826410",
    group: "AI Agent",
    focus: ["Agent", "新产品", "定价变化"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "昨天",
    newContent: 2,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "需要处理",
    summary: "记录国内 AI 产品发布、定价与用户体验变化。",
    searchTags: ["AI 产品观察室", "Agent", "定价变化", "商业化"],
  },
  {
    id: "following-jiqizhixin",
    name: "机器之心",
    provider: "B站",
    objectType: "UP主",
    handle: "UID 1007000",
    group: "AI 模型",
    focus: ["模型发布", "Benchmark", "行业观点"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "2 天前",
    newContent: 1,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "正常",
    summary: "中文 AI 研究、模型发布与行业动态。",
    searchTags: ["机器之心", "模型发布", "Benchmark", "中文"],
  },
  {
    id: "following-product-notes",
    name: "产品沉思录",
    provider: "B站",
    objectType: "收藏夹",
    group: "学习",
    focus: ["产品设计", "增长", "方法论"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "3 周前",
    newContent: 0,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "已暂停",
    summary: "产品方法、用户研究与增长案例的学习收藏。",
    searchTags: ["产品沉思录", "产品设计", "方法论"],
  },
  {
    id: "following-swyx",
    name: "@swyx",
    provider: "X",
    objectType: "Account",
    group: "AI Agent",
    focus: ["Agent", "开发者生态", "产品趋势"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "今天",
    newContent: 4,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "正常",
    summary: "AI 工程、Agent 与开发者产品的一线观察。",
    searchTags: ["swyx", "Agent", "开发者生态", "AI 工程"],
  },
  {
    id: "following-levelsio",
    name: "@levelsio",
    provider: "X",
    objectType: "Account",
    group: "产品与商业",
    focus: ["独立开发", "增长", "定价变化"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "2 天前",
    newContent: 2,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "正常",
    summary: "独立产品、增长实验与公开商业数据。",
    searchTags: ["levelsio", "独立开发", "增长", "定价变化", "商业化"],
  },
  {
    id: "following-pricing-interviews",
    name: "Agent 定价访谈",
    provider: "Local",
    objectType: "Folder",
    group: "个人收藏",
    focus: ["商业化", "定价变化", "企业采购"],
    focusMode: "custom",
    processing: defaultProcessing,
    lastUpdated: "4 天前",
    newContent: 3,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: ["topic-agent-product"],
    status: "需要处理",
    summary: "本地保存的定价访谈与采购反馈。",
    searchTags: ["Agent 定价访谈", "商业化", "定价变化", "企业采购", "本地"],
  },
  {
    id: "following-agent-collection",
    name: "Agent 产品案例集",
    provider: "Local",
    objectType: "Folder",
    group: "个人收藏",
    focus: ["Agent", "产品设计", "工作流"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "1 周前",
    newContent: 0,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: ["topic-agent-product"],
    status: "正常",
    summary: "手动收藏的 Agent onboarding 与交付界面案例。",
    searchTags: ["Agent 产品案例集", "产品设计", "工作流", "本地"],
  },
  {
    id: "following-reading-clips",
    name: "稍后阅读视频剪藏",
    provider: "Local",
    objectType: "Folder",
    group: "个人收藏",
    focus: ["学习", "产品趋势", "行业观点"],
    focusMode: "default",
    processing: defaultProcessing,
    lastUpdated: "1 个月前",
    newContent: 0,
    newIntelligence: 0,
    intelligenceIds: [],
    topicIds: [],
    status: "已暂停",
    summary: "暂存尚未整理的视频与会议片段。",
    searchTags: ["稍后阅读", "学习", "剪藏"],
  },
];

export const contents: ContentItem[] = [
  {
    id: "content-youtube-task-ui",
    followingId: "following-ai-explained",
    provider: "YouTube",
    kind: "YouTube Video",
    title: "从聊天助手到任务执行系统",
    publishedAt: "9 月 15 日",
    positionLabel: "31:24",
    status: "已分析",
    intelligenceIds: ["intel-task-interface"],
    topicIds: ["topic-agent-product"],
    sourceLanguage: "简体中文",
    summary: {
      oneLine: "Agent 产品的界面正在从开放聊天框转向围绕目标、进度、证据与交付物组织的任务系统。",
      keyPoints: [
        "用户真正关心的是任务是否完成，而不是是否掌握更好的提示词。",
        "任务目标、执行进度、可核验证据和交付物构成新的界面骨架。",
        "聊天仍然重要，但更适合澄清意图和处理例外。",
        "可见进度能降低用户对 Agent 是否失控的不确定感。",
        "失败恢复需要成为任务界面的一等能力。",
        "产品价值会从对话质量逐步转向可检查的完成结果。",
      ],
      chapters: [
        { time: "00:00", title: "为什么聊天框不够", context: "介绍开放聊天界面对普通用户造成的使用门槛。" },
        { time: "03:20", title: "Agent workflow", context: "拆解目标、计划、执行与交付之间的关系。" },
        { time: "08:14", title: "界面从聊天转向任务", context: "关键判断：界面开始围绕目标、进度、证据和交付物组织。" },
        { time: "15:32", title: "失败恢复与产品承诺", context: "讨论任务失败后如何保留上下文并提供下一步。" },
      ],
      detailLevel: "完整",
    },
    transcript: [
      { position: "08:01", text: "用户并不想再学习一种新的聊天技巧，他们想知道任务是否完成。" },
      { position: "08:14", text: "真正有用的 Agent 界面开始围绕目标、进度、证据和交付物组织。", evidenceId: "E1" },
      { position: "08:32", text: "聊天仍然存在，但它退到澄清意图和处理例外的位置。" },
    ],
    searchTags: ["任务执行界面", "Agent", "聊天", "任务系统", "目标 进度 证据 交付物"],
  },
  {
    id: "content-bilibili-task-ui",
    followingId: "following-bilibili-creator",
    provider: "B站",
    kind: "Bilibili Video",
    title: "为什么 Agent 产品开始强调完成任务",
    publishedAt: "9 月 15 日",
    positionLabel: "18:42",
    status: "已分析",
    intelligenceIds: ["intel-task-interface"],
    topicIds: ["topic-agent-product"],
    sourceLanguage: "简体中文",
    transcript: [
      { position: "05:20", text: "只给用户一个对话框，很多人不知道该从哪里开始。" },
      { position: "05:32", text: "当界面把任务阶段和可检查的结果摆出来，用户才知道 Agent 正在做什么。", evidenceId: "E2" },
      { position: "05:48", text: "这也让失败后的恢复动作更清楚。" },
    ],
    searchTags: ["任务执行界面", "Agent", "完成任务", "中文实践"],
  },
  {
    id: "content-x-task-ui",
    followingId: "following-agentbuilder",
    provider: "X",
    kind: "X Post",
    title: "The moat is task completion, not chat quality",
    publishedAt: "9 月 15 日",
    positionLabel: "原帖",
    status: "已分析",
    intelligenceIds: ["intel-task-interface"],
    topicIds: ["topic-agent-product"],
    sourceLanguage: "English",
    transcript: [
      { position: "原帖", text: "The durable interface is not a better chat box. It is a visible contract: goal, progress, evidence, and completed work.", evidenceId: "E3" },
    ],
    translatedTranscript: [
      { position: "原帖", text: "真正稳固的界面不是更好的聊天框，而是一份可见的契约：目标、进度、证据与完成结果。", evidenceId: "E3" },
    ],
    searchTags: ["任务执行界面", "Agent", "task completion", "英文来源"],
  },
  {
    id: "content-youtube-evaluation",
    followingId: "following-ai-explained",
    provider: "YouTube",
    kind: "YouTube Video",
    title: "Agent 评估从模型分数转向任务验收",
    publishedAt: "9 月 13 日",
    positionLabel: "26:10",
    status: "已分析",
    intelligenceIds: ["intel-evaluation"],
    topicIds: ["topic-agent-product"],
    sourceLanguage: "简体中文",
    transcript: [
      { position: "11:02", text: "团队开始使用任务是否被可靠完成来评估 Agent，而不仅是模型评分。", evidenceId: "E4" },
    ],
    searchTags: ["Agent 评估", "任务验收", "模型分数"],
  },
  {
    id: "content-youtube-failure",
    followingId: "following-ai-explained",
    provider: "YouTube",
    kind: "YouTube Video",
    title: "AI Agent 产品设计的三个误区",
    publishedAt: "9 月 15 日",
    positionLabel: "24:03",
    status: "失败",
    intelligenceIds: [],
    topicIds: [],
    sourceLanguage: "简体中文",
    transcript: [],
    searchTags: ["Agent", "产品设计", "失败状态"],
  },
  {
    id: "content-local-conference",
    followingId: "following-local-conference",
    provider: "Local",
    kind: "Local Video",
    title: "2026 AI 产品会议：Agent 交付界面",
    publishedAt: "9 月 14 日",
    positionLabel: "42:18",
    status: "分析中",
    intelligenceIds: [],
    topicIds: ["topic-agent-product"],
    sourceLanguage: "简体中文",
    transcript: [],
    searchTags: ["本地会议", "Agent", "交付界面"],
  },
  {
    id: "content-practical-ai",
    followingId: "following-practical-ai",
    provider: "YouTube",
    kind: "YouTube Video",
    title: "从聊天原型到任务型 Agent",
    publishedAt: "9 月 15 日",
    positionLabel: "29:08",
    status: "已分析",
    intelligenceIds: [],
    topicIds: [],
    sourceLanguage: "简体中文",
    summary: {
      oneLine: "这期视频用一个轻量案例说明如何把聊天原型改造成带有明确步骤和结果检查的任务型 Agent。",
      keyPoints: [
        "从一个清晰任务开始，比堆叠通用能力更容易验证价值。",
        "步骤可见能帮助用户判断当前进度。",
        "原型应先处理最常见的失败路径。",
        "输出格式要与用户接下来的工作直接衔接。",
        "案例完整，但没有出现超出现有认知的新判断。",
      ],
      chapters: [
        { time: "00:00", title: "原型目标", context: "定义一个可被验收的任务。" },
        { time: "04:10", title: "拆分工作流", context: "把对话改成可见步骤。" },
        { time: "11:45", title: "处理失败", context: "为常见失败提供恢复动作。" },
        { time: "20:18", title: "检查交付结果", context: "用明确标准确认任务是否完成。" },
      ],
      detailLevel: "简要",
    },
    transcript: [
      { position: "04:10", text: "把用户真正要完成的工作拆成可见步骤，往往比继续优化聊天提示更有效。" },
      { position: "20:18", text: "原型最终要回答的是：用户能否检查并继续使用这个结果。" },
    ],
    searchTags: ["Practical AI", "任务型 Agent", "原型", "工作流"],
  },
  {
    id: "content-youtube-pricing",
    followingId: "following-ai-explained",
    provider: "YouTube",
    kind: "YouTube Video",
    title: "Agent 商业模式正在离开纯订阅吗？",
    publishedAt: "9 月 29 日",
    positionLabel: "27:16",
    status: "已分析",
    intelligenceIds: ["intel-outcome-pricing"],
    topicIds: ["topic-agent-product"],
    sourceLanguage: "简体中文",
    summary: {
      oneLine: "Agent 定价正在出现订阅加结果费用的混合尝试，但企业采购对可预测成本的需求仍然构成限制。",
      keyPoints: [
        "纯席位订阅难以表达 Agent 自动完成工作的价值。",
        "部分创业团队开始把费用与可核验结果挂钩。",
        "更常见的是订阅加成功费，而不是完全结果付费。",
        "结果定义与归因会直接影响定价是否可执行。",
        "企业客户仍然偏好可预测的预算。",
        "当前信号值得跨来源追踪，但还不足以宣布主流模式已经改变。",
      ],
      chapters: [
        { time: "00:00", title: "现有订阅模式", context: "回顾 Agent 产品按席位收费的常见方式。" },
        { time: "06:25", title: "结果如何计价", context: "解释可核验任务结果与价值度量。" },
        { time: "12:40", title: "混合收费信号", context: "观察到订阅加结果费用的公开案例。" },
        { time: "18:05", title: "落地限制", context: "结果定义、归因与采购流程仍是主要限制。" },
      ],
      detailLevel: "完整",
    },
    transcript: [
      { position: "12:40", text: "越来越多 Agent 团队开始把部分收费与完成结果挂钩，而不是只按席位收费。", evidenceId: "E5" },
      { position: "18:05", text: "真正困难的不是报价，而是双方能否提前约定什么结果算完成、由谁验收。", evidenceId: "E8" },
    ],
    searchTags: ["Agent 商业化", "定价", "订阅", "结果付费", "商业模式"],
  },
  {
    id: "content-bilibili-pricing",
    followingId: "following-bilibili-creator",
    provider: "B站",
    kind: "Bilibili Video",
    title: "Agent 创业公司的定价实验",
    publishedAt: "9 月 30 日",
    positionLabel: "21:05",
    status: "已分析",
    intelligenceIds: ["intel-outcome-pricing"],
    topicIds: ["topic-agent-product"],
    sourceLanguage: "简体中文",
    transcript: [{ position: "09:18", text: "纯结果付费还少见，但订阅加成功费的混合模式明显增多。", evidenceId: "E6" }],
    searchTags: ["Agent 商业化", "定价", "创业公司", "混合收费"],
  },
  {
    id: "content-x-pricing",
    followingId: "following-agentbuilder",
    provider: "X",
    kind: "X Post",
    title: "Enterprises still want predictable Agent pricing",
    publishedAt: "9 月 30 日",
    positionLabel: "原帖",
    status: "已分析",
    intelligenceIds: ["intel-outcome-pricing"],
    topicIds: ["topic-agent-product"],
    sourceLanguage: "English",
    transcript: [{ position: "原帖", text: "Enterprise buyers still prefer predictable subscriptions; outcome pricing shifts too much measurement risk to procurement.", evidenceId: "E7" }],
    translatedTranscript: [{ position: "原帖", text: "企业买方仍然偏好可预测的订阅；结果付费会把过多的度量风险转嫁给采购流程。", evidenceId: "E7" }],
    searchTags: ["Agent 商业化", "定价", "企业采购", "英文来源", "outcome pricing"],
  },
  {
    id: "content-youtube-agent-pricing-en",
    followingId: "following-ai-explained",
    provider: "YouTube",
    kind: "YouTube Video",
    title: "Are AI Agents moving past pure subscription pricing?",
    publishedAt: "9 月 28 日",
    positionLabel: "22:47",
    status: "已分析",
    intelligenceIds: ["intel-outcome-pricing"],
    topicIds: ["topic-agent-product"],
    sourceLanguage: "English",
    summary: {
      oneLine: "这期英文视频观察到部分 Agent 团队开始尝试订阅加结果费用的混合定价，但企业采购仍然偏好可预测成本。",
      keyPoints: [
        "纯席位订阅难以表达 Agent 自动完成工作的价值。",
        "一些创业团队开始把部分费用与可核验结果挂钩。",
        "订阅加成功费比完全结果付费更常见。",
        "结果定义与归因是定价能否落地的关键。",
        "企业买方仍然重视预算可预测性。",
        "这是值得跨来源追踪的早期信号，而非已成定论的主流模式。",
      ],
      chapters: [
        { time: "00:00", title: "订阅模式的现状", context: "回顾 Agent 产品按席位收费的常见方式。" },
        { time: "05:40", title: "结果如何计价", context: "解释可核验任务结果与价值度量。" },
        { time: "11:12", title: "混合收费的早期信号", context: "观察到订阅加结果费用的公开案例。" },
        { time: "17:30", title: "企业采购的限制", context: "结果定义、归因与采购流程仍是主要限制。" },
      ],
      detailLevel: "完整",
    },
    transcript: [
      { position: "11:12", text: "A growing number of Agent teams are tying part of their revenue to verified outcomes instead of charging purely per seat.", evidenceId: "E9" },
      { position: "17:30", text: "Enterprise buyers still want predictable budgets; that constraint shapes how far outcome pricing can go.", evidenceId: "E10" },
    ],
    translatedTranscript: [
      { position: "11:12", text: "越来越多 Agent 团队开始把部分收入与可核验结果挂钩，而不是单纯按席位收费。", evidenceId: "E9" },
      { position: "17:30", text: "企业买方仍然希望预算可预测；这个限制决定了结果付费能走多远。", evidenceId: "E10" },
    ],
    searchTags: ["Agent 商业化", "定价", "outcome pricing", "英文来源", "AI Explained", "订阅"],
  },
];

export const evidence: EvidenceItem[] = [
  {
    id: "E1",
    contentId: "content-youtube-task-ui",
    followingId: "following-ai-explained",
    provider: "YouTube",
    position: "08:14",
    quote: "“真正有用的 Agent 界面开始围绕目标、进度、证据和交付物组织。”",
    context: "频道将 Agent 的核心交互从开放对话重新定义为可检查的任务执行。",
    strength: "直接陈述",
    stance: "supporting",
    sourceLanguage: "简体中文",
    searchTags: ["任务执行界面", "目标 进度 证据 交付物"],
  },
  {
    id: "E2",
    contentId: "content-bilibili-task-ui",
    followingId: "following-bilibili-creator",
    provider: "B站",
    position: "05:32",
    quote: "“当界面把任务阶段和可检查的结果摆出来，用户才知道 Agent 正在做什么。”",
    context: "中文产品实践提供了相同方向的独立使用反馈。",
    strength: "交叉来源",
    stance: "supporting",
    sourceLanguage: "简体中文",
    searchTags: ["任务执行界面", "中文实践"],
  },
  {
    id: "E3",
    contentId: "content-x-task-ui",
    followingId: "following-agentbuilder",
    provider: "X",
    position: "原帖",
    quote: "“The durable interface is a visible contract: goal, progress, evidence, and completed work.”",
    context: "产品构建者用公开帖子概括任务型 Agent 界面的最小信息结构。",
    strength: "交叉来源",
    stance: "supporting",
    sourceLanguage: "English",
    translatedQuote: "“真正稳固的界面是一份可见的契约：目标、进度、证据与完成结果。”",
    translatedContext: "产品构建者用公开帖子概括任务型 Agent 界面的最小信息结构（英文原帖的中文译文）。",
    searchTags: ["任务执行界面", "task completion", "英文来源"],
  },
  {
    id: "E4",
    contentId: "content-youtube-evaluation",
    followingId: "following-ai-explained",
    provider: "YouTube",
    position: "11:02",
    quote: "“团队开始使用任务是否被可靠完成来评估 Agent，而不仅是模型评分。”",
    context: "评估方法的变化与任务执行界面的兴起相互支持。",
    strength: "支持性证据",
    stance: "supporting",
    sourceLanguage: "简体中文",
    searchTags: ["Agent 评估", "任务验收"],
  },
  {
    id: "E5",
    contentId: "content-youtube-pricing",
    followingId: "following-ai-explained",
    provider: "YouTube",
    position: "12:40",
    quote: "“越来越多 Agent 团队开始把部分收费与完成结果挂钩。”",
    context: "行业观察显示结果关联定价开始进入公开产品讨论。",
    strength: "支持性证据",
    stance: "supporting",
    sourceLanguage: "简体中文",
    searchTags: ["Agent 商业化", "定价", "结果付费"],
  },
  {
    id: "E6",
    contentId: "content-bilibili-pricing",
    followingId: "following-bilibili-creator",
    provider: "B站",
    position: "09:18",
    quote: "“订阅加成功费的混合模式明显增多。”",
    context: "中文创业案例支持趋势，但同时限定它更多表现为混合收费。",
    strength: "条件性证据",
    stance: "conditional",
    sourceLanguage: "简体中文",
    searchTags: ["Agent 商业化", "混合收费"],
  },
  {
    id: "E7",
    contentId: "content-x-pricing",
    followingId: "following-agentbuilder",
    provider: "X",
    position: "原帖",
    quote: "“Enterprise buyers still prefer predictable subscriptions.”",
    context: "企业采购视角直接反对结果付费已成为主流的强表述。",
    strength: "反对性证据",
    stance: "contradicting",
    sourceLanguage: "English",
    translatedQuote: "“企业买方仍然偏好可预测的订阅。”",
    translatedContext: "企业采购视角直接反对结果付费已成为主流的强表述（英文原帖的中文译文）。",
    searchTags: ["Agent 商业化", "企业采购", "英文来源", "订阅"],
  },
  {
    id: "E8",
    contentId: "content-youtube-pricing",
    followingId: "following-ai-explained",
    provider: "YouTube",
    position: "18:05",
    quote: "“真正困难的是双方能否提前约定什么结果算完成、由谁验收。”",
    context: "同一视频补充了结果定价落地所需的验收与归因条件。",
    strength: "条件性证据",
    stance: "conditional",
    sourceLanguage: "简体中文",
    searchTags: ["Agent 商业化", "结果验收"],
  },
  {
    id: "E9",
    contentId: "content-youtube-agent-pricing-en",
    followingId: "following-ai-explained",
    provider: "YouTube",
    position: "11:12",
    quote: "“A growing number of Agent teams are tying part of their revenue to verified outcomes instead of charging purely per seat.”",
    context: "English YouTube source directly observes the hybrid pricing shift.",
    strength: "支持性证据",
    stance: "supporting",
    sourceLanguage: "English",
    translatedQuote: "“越来越多 Agent 团队开始把部分收入与可核验结果挂钩，而不是单纯按席位收费。”",
    translatedContext: "英文 YouTube 来源直接观察到混合定价的变化（中文译文）。",
    searchTags: ["Agent 商业化", "outcome pricing", "英文来源", "AI Explained"],
  },
  {
    id: "E10",
    contentId: "content-youtube-agent-pricing-en",
    followingId: "following-ai-explained",
    provider: "YouTube",
    position: "17:30",
    quote: "“Enterprise buyers still want predictable budgets; that constraint shapes how far outcome pricing can go.”",
    context: "The same English source qualifies the trend with procurement reality.",
    strength: "条件性证据",
    stance: "conditional",
    sourceLanguage: "English",
    translatedQuote: "“企业买方仍然希望预算可预测；这个限制决定了结果付费能走多远。”",
    translatedContext: "同一英文来源用采购现实限定了这个趋势（中文译文）。",
    searchTags: ["Agent 商业化", "企业采购", "英文来源"],
  },
];

export const intelligence = [
  {
    id: "intel-task-interface",
    title: "Agent 产品正在从聊天界面转向任务执行界面",
    summary: "来自 YouTube、B站与 X 的独立信号共同显示，用户价值正在从“能否对话”转向“任务是否可见、可核验地完成”。",
    why: "这会重塑首页、状态反馈、失败恢复与价值度量；它不只是界面变化，也是产品承诺的变化。",
    importance: "最值得关注",
    evidenceIds: ["E1", "E2", "E3"],
    supportingEvidenceIds: ["E1", "E2", "E3"],
    contradictingEvidenceIds: [],
    conditionalEvidenceIds: [],
    contentIds: ["content-youtube-task-ui", "content-bilibili-task-ui", "content-x-task-ui"],
    followingIds: ["following-ai-explained", "following-bilibili-creator", "following-agentbuilder"],
    topicId: "topic-agent-product",
    time: "2 小时前",
    confidence: "强支持",
    retentionReasons: ["多来源支持", "与现有 Topic 发生变化", "存在新的产品信号"],
    stillNeedsValidation: ["任务界面是否能持续提高留存", "不同风险等级应展示多少执行过程"],
    lastUpdated: "2026-09-15 10:20",
    outputLanguage: "简体中文" as Language,
    searchTags: ["任务执行界面", "Agent", "聊天界面", "跨语言"],
  },
  {
    id: "intel-evaluation",
    title: "Agent 评估开始以任务验收替代单一模型分数",
    summary: "产品团队更关注任务完成质量、可恢复性和交付物，而非孤立的模型基准。",
    why: "评估单位决定产品优化方向，也影响用户是否愿意把真实工作交给 Agent。",
    importance: "重要",
    evidenceIds: ["E4"],
    supportingEvidenceIds: ["E4"],
    contradictingEvidenceIds: [],
    conditionalEvidenceIds: [],
    contentIds: ["content-youtube-evaluation"],
    followingIds: ["following-ai-explained", "following-local-conference"],
    topicId: "topic-agent-product",
    time: "昨天",
    confidence: "部分支持",
    retentionReasons: ["影响 Topic 的评估方式", "值得未来继续追踪"],
    stillNeedsValidation: ["是否已形成跨行业共识"],
    lastUpdated: "2026-09-14 18:05",
    outputLanguage: "简体中文" as Language,
    searchTags: ["Agent 评估", "任务验收", "模型分数"],
  },
  {
    id: "intel-outcome-pricing",
    title: "Outcome-based pricing 正在成为 Agent 商业模式趋势",
    summary: "YouTube 与 B站出现结果关联收费信号，但企业采购视角仍偏好固定订阅；当前证据存在分歧。",
    why: "定价方式会改变产品承诺、价值衡量与风险分配。即使尚未成为主流，这个变化也值得持续追踪。",
    importance: "值得追踪",
    evidenceIds: ["E5", "E6", "E7", "E8", "E9", "E10"],
    supportingEvidenceIds: ["E5", "E9"],
    contradictingEvidenceIds: ["E7"],
    conditionalEvidenceIds: ["E6", "E8", "E10"],
    contentIds: ["content-youtube-pricing", "content-bilibili-pricing", "content-x-pricing", "content-youtube-agent-pricing-en"],
    followingIds: ["following-ai-explained", "following-bilibili-creator", "following-agentbuilder"],
    topicId: "topic-agent-product",
    time: "刚刚",
    confidence: "部分支持",
    retentionReasons: ["多来源出现新信号", "推动已有 Topic 从稳定转为活跃", "存在明确反对观点", "英文与中文来源共同支持"],
    stillNeedsValidation: ["结果付费是否已超出早期创业公司", "企业采购是否接受可核验的结果口径"],
    lastUpdated: "2026-10-12 09:40",
    outputLanguage: "简体中文" as Language,
    searchTags: ["Agent 商业化", "outcome-based pricing", "定价", "跨语言", "商业模式"],
  },
] as const;

export const topic = {
  id: "topic-agent-product",
  name: "AI Agent 商业化",
  summary: "Agent 的价值衡量正在从席位与对话量，扩展到可核验的任务结果与混合收费。",
  currentUnderstanding: "订阅制仍是主流，但部分 Agent 产品开始尝试订阅加结果费用；纯 outcome-based pricing 是否会普及仍存在分歧。",
  recentChange: "过去 30 天出现新的定价 Evidence，主题由稳定转为活跃；当前理解从纯订阅主导更新为混合收费模式正在增加。",
  openQuestions: ["结果应由谁定义与验收？", "企业采购是否愿意承担波动成本？"],
  followingIds: ["following-ai-explained", "following-bilibili-creator", "following-agentbuilder"],
  intelligenceIds: ["intel-task-interface", "intel-evaluation", "intel-outcome-pricing"],
  evidenceIds: ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10"],
  trend: "过去 30 天明显升温",
  lifecycle: "活跃",
  lifecycleChange: "稳定 → 活跃",
  outputLanguage: "简体中文" as Language,
  searchTags: ["AI Agent 商业化", "Agent", "商业化", "定价", "跨语言"],
  evolution: [
    { date: "Sep 01", text: "当前理解：订阅制仍是主流" },
    { date: "Sep 15", text: "出现新 Evidence：部分 Agent 开始尝试 outcome pricing" },
    { date: "Sep 30", text: "当前理解更新：混合收费模式正在增加" },
  ],
};

export const research = {
  id: "research-task-interface",
  question: "AI Agent 商业模式正在如何变化？",
  conclusion: "订阅制仍占主导，但结果关联的混合收费开始增加；证据尚不足以判断纯 outcome-based pricing 已成为主流。",
  findings: [
    "结果可核验时，产品更容易尝试将部分收费与价值挂钩。",
    "当前可见变化主要是订阅加成功费，而不是彻底替代订阅。",
    "企业采购仍重视预算可预测性，形成明确反向 Evidence。",
  ],
  perspectives: [
    "创业团队认为结果收费更贴近产品价值。",
    "企业买方认为固定订阅更容易采购和控制预算。",
  ],
  unknowns: ["缺少足够的真实合同样本。", "结果定义、归因与争议处理仍未形成共识。"],
  outputLanguage: "简体中文" as Language,
  searchTags: ["AI Agent 商业化", "商业模式", "调研", "定价", "outcome pricing"],
  versions: [
    { id: "v1", date: "2026-09-15", cutoff: "2026-09-14", conclusion: "订阅制仍占主导", evidenceIds: ["E4"] },
    { id: "v2", date: "2026-10-12", cutoff: "2026-10-11", conclusion: "Outcome-based pricing 开始出现明显增长", evidenceIds: ["E5", "E6", "E7"] },
  ],
};

export const preferences = {
  explicit: ["AI / 技术", "产品", "有明确证据的观点"],
  inferred: ["近期关注评测实践"],
  temporary: [
    { label: "本周优先关注 Agent 产品界面", state: "active", meta: "有效至 9 月 20 日" },
    { label: "关注多模态模型发布", state: "expired", meta: "已过期 · 当前不再生效" },
  ],
};

export function getFollowing(id: string) {
  return followings.find(item => item.id === id);
}

export function getContent(id: string) {
  return contents.find(item => item.id === id);
}

export function getEvidence(id: string) {
  return evidence.find(item => item.id === id);
}

export function assertFixtureRelationships(): string[] {
  const errors: string[] = [];
  const validGroups = new Set<FollowingGroup>(["AI 模型", "AI Agent", "产品与商业", "学习", "个人收藏"]);
  for (const item of followings) {
    if (!validGroups.has(item.group)) errors.push(`following:${item.id}:group`);
    if (!item.focus.length) errors.push(`following:${item.id}:focus`);
    for (const id of item.intelligenceIds) if (!intelligence.some(value => value.id === id)) errors.push(`following:${item.id}:intelligence:${id}`);
    for (const id of item.topicIds) if (id !== topic.id) errors.push(`following:${item.id}:topic:${id}`);
  }
  for (const item of contents) {
    const following = getFollowing(item.followingId);
    if (!following) errors.push(`content:${item.id}:following`);
    else if (following.provider !== item.provider) errors.push(`content:${item.id}:provider`);
    for (const id of item.intelligenceIds) if (!intelligence.some(value => value.id === id)) errors.push(`content:${item.id}:intelligence:${id}`);
    for (const id of item.topicIds) if (id !== topic.id) errors.push(`content:${item.id}:topic:${id}`);
    if (item.summary) {
      if (item.summary.keyPoints.length < 5 || item.summary.keyPoints.length > 10) errors.push(`content:${item.id}:summary-key-points`);
      if (item.summary.chapters.length < 3) errors.push(`content:${item.id}:summary-chapters`);
      if (new Set(item.summary.chapters.map(chapter => chapter.time)).size !== item.summary.chapters.length) errors.push(`content:${item.id}:summary-chapter-position`);
    }
    if (item.translatedTranscript && item.translatedTranscript.length !== item.transcript.length) errors.push(`content:${item.id}:translated-transcript-length`);
  }
  if (contents.filter(item => item.summary).length < 3) errors.push("content:summary-fixture-coverage");
  if (!contents.some(item => item.sourceLanguage === "English" && item.summary)) errors.push("content:english-source-with-chinese-output-coverage");
  for (const item of evidence) {
    const content = getContent(item.contentId);
    const following = getFollowing(item.followingId);
    if (!content) errors.push(`evidence:${item.id}:content`);
    else {
      if (content.followingId !== item.followingId) errors.push(`evidence:${item.id}:following-link`);
      if (content.provider !== item.provider) errors.push(`evidence:${item.id}:provider`);
      if (content.sourceLanguage !== item.sourceLanguage) errors.push(`evidence:${item.id}:source-language`);
      if (!content.transcript.some(line => line.evidenceId === item.id)) errors.push(`evidence:${item.id}:transcript`);
    }
    if (!following) errors.push(`evidence:${item.id}:following`);
    else if (following.provider !== item.provider) errors.push(`evidence:${item.id}:following-provider`);
    if (item.sourceLanguage === "English" && !item.translatedQuote) errors.push(`evidence:${item.id}:missing-translation`);
    if (item.sourceLanguage === "简体中文" && item.translatedQuote) errors.push(`evidence:${item.id}:unexpected-translation`);
  }
  for (const item of intelligence) {
    const governedEvidenceIds = [
      ...item.supportingEvidenceIds,
      ...item.contradictingEvidenceIds,
      ...item.conditionalEvidenceIds,
    ];
    if (new Set(governedEvidenceIds).size !== governedEvidenceIds.length) errors.push(`intelligence:${item.id}:duplicate-stance`);
    if ([...governedEvidenceIds].sort().join(",") !== [...item.evidenceIds].sort().join(",")) errors.push(`intelligence:${item.id}:stance-coverage`);
    for (const id of item.evidenceIds) {
      const linkedEvidence = getEvidence(id);
      if (!linkedEvidence) errors.push(`intelligence:${item.id}:evidence:${id}`);
      else {
        if (!(item.contentIds as readonly string[]).includes(linkedEvidence.contentId)) errors.push(`intelligence:${item.id}:evidence-content:${id}`);
        if (!(item.followingIds as readonly string[]).includes(linkedEvidence.followingId)) errors.push(`intelligence:${item.id}:evidence-following:${id}`);
      }
    }
    for (const id of item.contentIds) if (!getContent(id)) errors.push(`intelligence:${item.id}:content:${id}`);
    for (const id of item.followingIds) if (!getFollowing(id)) errors.push(`intelligence:${item.id}:following:${id}`);
    if (item.topicId !== topic.id) errors.push(`intelligence:${item.id}:topic`);
  }
  for (const id of topic.followingIds) if (!getFollowing(id)) errors.push(`topic:following:${id}`);
  for (const id of topic.intelligenceIds) if (!intelligence.some(item => item.id === id)) errors.push(`topic:intelligence:${id}`);
  for (const id of topic.evidenceIds) if (!getEvidence(id)) errors.push(`topic:evidence:${id}`);
  for (const version of research.versions) {
    for (const id of version.evidenceIds) if (!getEvidence(id)) errors.push(`research:${version.id}:evidence:${id}`);
  }
  return errors;
}

/**
 * Search index — browser-state only.
 *
 * This is a fixture-driven locator, not a real index. No database, no
 * embeddings, no external service. Each entry carries a pre-baked `text`
 * blob (title + summary + curated tags) that the demo filters with a simple
 * case-insensitive substring / tokenized-AND match.
 */
export type SearchIndexEntry = {
  id: string;
  type: SearchResultType;
  title: string;
  /** Where it came from — e.g. provider · following · position. */
  context: string;
  /** Why it matched — rendered as a snippet in results. */
  snippet: string;
  /** Route to navigate to when the result is clicked. */
  route: string;
  /** Concatenated searchable text (lowercased at query time). */
  text: string;
  sourceLanguage?: Language;
  outputLanguage?: Language;
  /** True when the entry's sources span more than one language. */
  crossLanguage?: boolean;
};

function joinText(...parts: Array<string | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function buildSearchIndex(): SearchIndexEntry[] {
  const entries: SearchIndexEntry[] = [];

  for (const item of followings) {
    entries.push({
      id: `following:${item.id}`,
      type: "关注",
      title: item.name,
      context: `${item.provider} · ${item.objectType} · ${item.group}`,
      snippet: item.summary,
      route: item.id,
      text: joinText(item.name, item.handle, item.summary, item.group, item.objectType, item.provider, item.focus.join(" "), (item.searchTags ?? []).join(" ")),
    });
  }

  for (const item of contents) {
    const following = getFollowing(item.followingId);
    entries.push({
      id: `content:${item.id}`,
      type: "内容",
      title: item.title,
      context: `${item.kind} · ${following?.name ?? item.followingId} · ${item.publishedAt}`,
      snippet: item.summary?.oneLine ?? (item.transcript[0]?.text ?? `${item.kind} · ${item.positionLabel}`),
      route: item.id,
      sourceLanguage: item.sourceLanguage,
      outputLanguage: "简体中文",
      crossLanguage: item.sourceLanguage === "English",
      text: joinText(item.title, item.summary?.oneLine, item.summary?.keyPoints.join(" "), item.summary?.chapters.map(chapter => `${chapter.title} ${chapter.context}`).join(" "), item.transcript.map(line => line.text).join(" "), following?.name, item.kind, (item.searchTags ?? []).join(" ")),
    });
  }

  for (const item of evidence) {
    const content = getContent(item.contentId);
    const following = getFollowing(item.followingId);
    entries.push({
      id: `evidence:${item.id}`,
      type: "Evidence",
      title: `${item.id} · ${item.quote.slice(0, 48)}${item.quote.length > 48 ? "…" : ""}`,
      context: `${item.provider} · ${following?.name ?? item.followingId} · ${item.position}`,
      snippet: item.context,
      route: content?.id ?? item.contentId,
      sourceLanguage: item.sourceLanguage,
      outputLanguage: item.sourceLanguage === "English" ? "简体中文" : item.sourceLanguage,
      crossLanguage: item.sourceLanguage === "English",
      text: joinText(item.quote, item.translatedQuote, item.context, item.translatedContext, item.strength, following?.name, content?.title, (item.searchTags ?? []).join(" ")),
    });
  }

  for (const item of intelligence) {
    const sourceLanguages = new Set(item.evidenceIds.map(id => getEvidence(id)?.sourceLanguage).filter(Boolean) as Language[]);
    entries.push({
      id: `intelligence:${item.id}`,
      type: "洞察",
      title: item.title,
      context: `${item.importance} · ${item.followingIds.length} 个关注对象 · ${item.evidenceIds.length} 条 Evidence`,
      snippet: item.summary,
      route: item.id === "intel-outcome-pricing" ? "intelligence-detail-pricing" : "intelligence-detail",
      outputLanguage: item.outputLanguage,
      crossLanguage: sourceLanguages.size > 1,
      text: joinText(item.title, item.summary, item.why, item.confidence, item.retentionReasons.join(" "), item.stillNeedsValidation.join(" "), (item.searchTags ?? []).join(" ")),
    });
  }

  entries.push({
    id: `topic:${topic.id}`,
    type: "主题",
    title: topic.name,
    context: `${topic.lifecycle} · ${topic.trend}`,
    snippet: topic.summary,
    route: "topic-detail",
    outputLanguage: topic.outputLanguage,
    crossLanguage: true,
    text: joinText(topic.name, topic.summary, topic.currentUnderstanding, topic.recentChange, topic.openQuestions.join(" "), topic.evolution.map(entry => entry.text).join(" "), (topic.searchTags ?? []).join(" ")),
  });

  entries.push({
    id: `research:${research.id}`,
    type: "调研",
    title: research.question,
    context: `${research.versions.length} 个版本 · 最近 ${research.versions[research.versions.length - 1].date}`,
    snippet: research.conclusion,
    route: "research-result",
    outputLanguage: research.outputLanguage,
    text: joinText(research.question, research.conclusion, research.findings.join(" "), research.perspectives.join(" "), research.unknowns.join(" "), research.versions.map(version => version.conclusion).join(" "), (research.searchTags ?? []).join(" ")),
  });

  return entries;
}

/**
 * Fixture-only matcher. Case-insensitive substring on the whole query, with a
 * tokenized-AND fallback so multi-word Chinese queries like "Agent 商业化"
 * still match entries that carry both tokens separately.
 */
export function searchIndexMatches(entry: SearchIndexEntry, query: string): boolean {
  const trimmed = query.trim().toLowerCase();
  if (!trimmed) return false;
  const haystack = entry.text.toLowerCase();
  if (haystack.includes(trimmed)) return true;
  const tokens = trimmed.split(/\s+/).filter(Boolean);
  return tokens.length > 1 && tokens.every(token => haystack.includes(token));
}
