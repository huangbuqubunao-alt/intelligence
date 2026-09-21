import { useMemo, useState } from "react";
import { contents, evidence, followings, getContent, getEvidence, getFollowing, intelligence, preferences, research, topic, type ContentItem, type EvidenceItem, type Following, type FollowingGroup } from "./fixtures";
import { contentRoutes, followingRoutes, type AsyncState, type EvidenceDisplay, type FollowingTab, type Language, type ResearchContext, type ResearchScopeMode, type Route, type SettingsSection, type SpecifiedScope } from "./model";
import { resolveEvidenceText, useLanguage } from "./LanguageContext";
import { Button, MetaRow, ProviderLabel, SectionHeader, StatusLine } from "./ui";

type Navigate = (route: Route) => void;
type OpenResearch = (context: ResearchContext) => void;

function IntelligenceCard({ item = intelligence[0], navigate, compact = false }: { item?: typeof intelligence[number]; navigate: Navigate; compact?: boolean }) {
  const detailRoute: Route = item.id === "intel-outcome-pricing" ? "intelligence-detail-pricing" : "intelligence-detail";
  return <article className={`intel-card ${compact ? "compact" : ""}`}>
    <div className="intel-card-top"><span className="importance">{item.importance}</span><span className="muted">{item.time}</span></div>
    <button className="card-link" aria-label={`查看洞察：${item.title}`} onClick={() => navigate(detailRoute)}><h3>{item.title}</h3><p>{item.summary}</p></button>
    <MetaRow><span>{item.followingIds.length} 个关注对象</span><span>{item.evidenceIds.length} 条 Evidence</span><button onClick={() => navigate("topic-detail")}>{topic.name}</button></MetaRow>
  </article>;
}

function FollowingMini({ item, navigate }: { item: Following; navigate: Navigate }) {
  return <button className="following-mini" aria-label={`查看关注：${item.name}`} onClick={() => navigate((followingRoutes[item.id] ?? item.id) as Route)}>
    <div><ProviderLabel provider={item.provider} type={item.objectType} /><h3>{item.name}</h3></div>
    <p>{item.newContent} 个新内容 · 参与 {item.intelligenceIds.length} 条洞察 · {item.topicIds.length} 个相关主题</p>
  </button>;
}

const evidenceDisplayOptions: Array<{ id: EvidenceDisplay; label: string }> = [
  { id: "译文", label: "译文" },
  { id: "双语", label: "双语" },
  { id: "原文", label: "原文" },
];

/**
 * Display switch for Evidence excerpts. Only meaningful when the source
 * language differs from the output language; otherwise all three modes render
 * the same original excerpt. The toggle never creates a new Evidence record —
 * the original excerpt + source position stay authoritative.
 */
function EvidenceDisplayToggle({ value, onChange, label = "Evidence 显示" }: { value: EvidenceDisplay; onChange: (next: EvidenceDisplay) => void; label?: string }) {
  return <div className="evidence-display-toggle" role="group" aria-label={label}>
    <span className="evidence-display-label">{label}</span>
    {evidenceDisplayOptions.map(option => <button
      key={option.id}
      aria-pressed={value === option.id}
      className={value === option.id ? "active" : ""}
      onClick={() => onChange(option.id)}
    >{option.label}</button>)}
  </div>;
}

/** Renders one Evidence excerpt under the active display mode. */
function EvidenceExcerpt({ item, display, outputLanguage }: { item: EvidenceItem; display: EvidenceDisplay; outputLanguage: Language }) {
  const resolved = resolveEvidenceText(item, display, outputLanguage);
  return <div className="evidence-excerpt">
    <blockquote>{resolved.primary}</blockquote>
    {resolved.secondary && <blockquote className="evidence-original" lang={item.sourceLanguage === "English" ? "en" : "zh"}>{resolved.secondary}</blockquote>}
    {resolved.showTranslationNote && <p className="evidence-translation-note">
      {item.sourceLanguage === "English"
        ? <>原文为 English · 译文仅供阅读，原摘录与位置仍为权威来源。</>
        : <>源语言与输出语言一致，无需翻译。</>}
    </p>}
  </div>;
}

/** Surfaces 源语言 / 内容输出语言 without exposing detection internals. */
function LanguageBadge({ sourceLanguage, outputLanguage }: { sourceLanguage: Language; outputLanguage: Language }) {
  return <div className="language-badge" aria-label="语言信息">
    <span>源语言<strong>{sourceLanguage}</strong></span>
    <span className="language-badge-arrow" aria-hidden="true">→</span>
    <span>内容输出语言<strong>{outputLanguage}</strong></span>
    {sourceLanguage !== outputLanguage && <small>生成物已按输出语言呈现；原始内容仍按源语言保留。</small>}
  </div>;
}

export function HomePage({ navigate }: { navigate: Navigate }) {
  return <>
    <section className="brief-hero">
      <p className="eyebrow">9 月 15 日 · Morning Brief</p>
      <h1>早上好，今天有 3 件事值得关注</h1>
      <p>12 个新内容，其中 9 个已生成摘要，3 条形成新 Intelligence。内容处理与知识沉淀是两件事。</p>
      <div className="brief-note"><strong>最重要的变化</strong><span>Agent 产品的竞争焦点正在从聊天质量转向可核验的任务完成。</span></div>
    </section>
    <section className="dashboard-section">
      <div className="section-title"><div><p className="eyebrow">From your Following</p><h2>来自你的关注</h2></div><Button variant="quiet" onClick={() => navigate("following")}>查看全部关注</Button></div>
      <div className="following-strip">{followings.slice(0, 3).map(item => <FollowingMini key={item.id} item={item} navigate={navigate} />)}</div>
    </section>
    <section className="dashboard-section">
      <div className="section-title"><div><p className="eyebrow">Priority Intelligence</p><h2>最值得关注的洞察</h2></div><Button variant="quiet" onClick={() => navigate("intelligence")}>查看全部洞察</Button></div>
      <IntelligenceCard navigate={navigate} />
      <button className="evidence-preview" onClick={() => navigate("intelligence-detail")}><span>Evidence preview · 3 种 Provider</span><strong>“目标、进度、证据和交付物正在成为 Agent 界面的共同骨架。”</strong><small>YouTube · B站 · X</small></button>
    </section>
    <div className="dashboard-grid">
      <section className="topic-preview"><p className="eyebrow">正在变化的 Topic</p><h2>{topic.name}</h2><p>{topic.recentChange}</p><Button variant="quiet" onClick={() => navigate("topic-detail")}>查看主题</Button></section>
      <section className="recent-processing"><p className="eyebrow">最近处理</p><h2>内容处理</h2>
        <div className="processing-rows"><button onClick={() => navigate("content-youtube-task-ui")}><span>从聊天助手到任务执行系统</span><small>已分析</small></button><button onClick={() => navigate("content-local-conference")}><span>2026 AI 产品会议</span><small>处理中</small></button></div>
      </section>
    </div>
    <section className="run-summary" aria-label="运行摘要"><div><p className="eyebrow">运行摘要</p><h2>本周处理 184 条内容</h2></div><p><strong>79% 本地处理</strong><span>26 次云端分析</span><span>预计成本 ¥3.80</span></p></section>
    <details className="quiet-health"><summary>运行正常 · 最后处理 8 分钟前</summary><p>YouTube、B站、X 与本地内容在此 Demo 中只展示模拟状态；没有真实连接或处理。</p></details>
  </>;
}

export function FollowingPage({ navigate }: { navigate: Navigate }) {
  const groups: Array<"全部" | FollowingGroup> = ["全部", "AI 模型", "AI Agent", "产品与商业", "学习", "个人收藏"];
  const filters = ["全部", "有更新", "产生新洞察", "需要处理", "已暂停"] as const;
  const [group, setGroup] = useState<(typeof groups)[number]>("全部");
  const [filter, setFilter] = useState<(typeof filters)[number]>("全部");
  const [query, setQuery] = useState("");
  const visibleFollowings = useMemo(() => followings.filter(item => {
    const inGroup = group === "全部" || item.group === group;
    const matchesFilter = filter === "全部"
      || (filter === "有更新" && item.newContent > 0)
      || (filter === "产生新洞察" && item.newIntelligence > 0)
      || (filter === "需要处理" && item.status === "需要处理")
      || (filter === "已暂停" && item.status === "已暂停");
    return inGroup && matchesFilter && item.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
  }), [filter, group, query]);
  return <>
    <SectionHeader eyebrow="Following" title="Intelligence Agent 现在在帮我关注什么？" description="关注是你主动选择的信息入口；洞察与主题会跨多个关注对象形成。" action={<Button onClick={() => navigate("following-add")}>+ 添加关注</Button>} />
    <section className="following-library" aria-label="关注资料库">
      <div className="following-organizer">
        <div><p className="eyebrow">Following Groups</p><nav className="group-tabs" aria-label="关注分组">{groups.map(item => <button key={item} aria-label={item === "全部" ? "全部" : item} aria-pressed={group === item} className={group === item ? "active" : ""} onClick={() => setGroup(item)}>{item}</button>)}</nav></div>
        <p className="organizer-note"><strong>分组整理“我关注什么”</strong><span>Topic 表达系统长期形成“我知道什么”，两者不会互相替代。</span></p>
      </div>
      <div className="following-tools">
        <label className="following-search"><span>搜索</span><input type="search" aria-label="搜索关注对象" placeholder="按名称搜索关注对象" value={query} onChange={event => setQuery(event.target.value)} /></label>
        <div className="following-filters" aria-label="关注状态筛选">{filters.map(item => <button key={item} aria-label={item === "全部" ? "筛选：全部" : item} aria-pressed={filter === item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>{item}</button>)}</div>
      </div>
      <p className="following-result-count" role="status">{visibleFollowings.length} 个关注对象</p>
    </section>
    <div className="following-list">{visibleFollowings.map(item => <article key={item.id}><button aria-label={`查看关注：${item.name}`} onClick={() => navigate(item.id as Route)}><div className="following-identity"><ProviderLabel provider={item.provider} type={item.objectType} /><h2>{item.name}</h2><p>{item.summary}</p><div className="following-context"><span>{item.group}</span><small>关注重点：{item.focus.join(" · ")}</small></div></div><div className="following-stats"><span>{item.lastUpdated}<small>最近更新</small></span><span>{item.newContent}<small>新内容</small></span><span>{item.newIntelligence}<small>新 Intelligence</small></span><span>{item.topicIds.length}<small>相关 Topic</small></span><span>{item.status}<small>状态</small></span></div></button></article>)}</div>
    {visibleFollowings.length === 0 && <Empty title="没有匹配的关注对象" copy="调整分组、筛选或搜索词后再试。" />}
  </>;
}

export function AddFollowingPage({ navigate }: { navigate: Navigate }) {
  const [provider, setProvider] = useState("YouTube");
  const [kind, setKind] = useState("频道");
  const [url, setUrl] = useState("");
  const [check, setCheck] = useState<AsyncState>("idle");
  const fullProvider = provider === "YouTube" || provider === "B站";
  const test = () => { setCheck("checking"); window.setTimeout(() => setCheck(url.trim() ? "success" : "error"), 140); };
  return <>
    <div className="breadcrumbs"><button onClick={() => navigate("following")}>关注</button><span>/</span><span>添加关注</span></div>
    <SectionHeader eyebrow="Add Following · Demo" title="添加关注" description="先选择 Provider，再选择你想持续关注的对象。" />
    <div className="form-surface">
      <fieldset className="provider-picker"><legend>选择类型</legend>{["YouTube", "B站", "X", "抖音", "小红书", "本地视频"].map(item => <button key={item} className={provider === item ? "selected" : ""} onClick={() => { setProvider(item); setKind(item === "B站" ? "UP主" : "频道"); setCheck("idle"); }}>{item}<small>{item === "YouTube" ? "完整 Demo flow" : item === "B站" ? "结构模拟" : "Demo preview · 后续 Provider"}</small></button>)}</fieldset>
      {!fullProvider && <StatusLine title={`${provider} 将作为后续 Provider`}>本轮只展示产品结构，不会假装已经接入或处理真实数据。请选择 YouTube 或 B站继续模拟。</StatusLine>}
      {fullProvider && <>
        <div className="segmented" aria-label="关注对象类型">{(provider === "YouTube" ? ["频道", "视频", "播放列表"] : ["UP主", "视频"]).map(item => <button key={item} className={kind === item ? "active" : ""} onClick={() => setKind(item)}>{item}</button>)}</div>
        <label className="field"><span>{provider} URL</span><input aria-label={`${provider} URL`} value={url} onChange={event => { setUrl(event.target.value); setCheck("idle"); }} placeholder={provider === "YouTube" ? "https://youtube.com/@practicalai" : "https://space.bilibili.com/..."}/></label>
        <div className="two-fields"><label className="field"><span>检查频率</span><select defaultValue="daily"><option value="daily">每天</option><option>每周</option><option>手动</option></select></label><label className="field"><span>每次最多处理</span><select defaultValue="5"><option value="5">5 个内容</option><option>10 个内容</option></select></label></div>
        <Button onClick={test} disabled={!url || check === "checking"}>{check === "checking" ? "正在模拟测试…" : "测试关注"}</Button>
        {check === "error" && <StatusLine tone="danger" title="无法识别这个对象">确认 URL 对应公开的{kind}后重试。已输入内容不会丢失。</StatusLine>}
        {check === "success" && <><StatusLine tone="success" title={provider === "YouTube" ? "找到频道：Practical AI Engineering" : "找到 UP 主：某 AI UP 主"}>可以读取公开内容；这是 Demo 结果，没有访问真实平台。</StatusLine><Button onClick={() => navigate(provider === "YouTube" ? "following-practical-ai" : "following-bilibili-creator")}>保存关注（Demo）</Button></>}
      </>}
    </div>
  </>;
}

export function FollowingDetailPage({ followingId, navigate, openResearch }: { followingId: string; navigate: Navigate; openResearch: OpenResearch }) {
  const item = getFollowing(followingId) ?? followings[0];
  const [tab, setTab] = useState<FollowingTab>("overview");
  const ownContents = contents.filter(content => content.followingId === item.id);
  const relatedIntelligence = intelligence.filter(intel => item.intelligenceIds.includes(intel.id));
  return <>
    <div className="breadcrumbs"><button onClick={() => navigate("following")}>关注</button><span>/</span><span>{item.name}</span></div>
    <SectionHeader eyebrow="Following Detail" title={item.name} description={`${item.provider} · ${item.objectType} · ${item.group} · ${item.summary}`} action={<Button onClick={() => openResearch({ kind: "关注", label: item.name })}>调研这个关注对象</Button>} />
    <nav className="detail-tabs" aria-label="关注详情">{([["overview", "概览"], ["content", "内容"], ["intelligence", "洞察"], ["topics", "相关主题"]] as Array<[FollowingTab, string]>).map(([id, label]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>)}</nav>
    {tab === "overview" && <><div className="summary-band"><span><strong>{item.newContent + 10}</strong>最近 30 天新内容</span><span><strong>{item.intelligenceIds.length}</strong>参与形成的洞察</span><span><strong>{item.topicIds.length}</strong>贡献过的主题</span></div><FollowingFocusSettings item={item} /><FollowingLanguageSettings item={item} /><section className="understanding"><p className="eyebrow">最值得关注</p><h2>{item.intelligenceIds.length ? intelligence[0].title : "新关注正在等待首轮处理"}</h2><p>{item.intelligenceIds.length ? "这条关注提供了关键 Evidence，但该洞察同时由其他关注对象支持。" : "保存成功后，新内容会进入模拟处理队列。"}</p></section></>}
    {tab === "content" && <ContentList items={ownContents} navigate={navigate} />}
    {tab === "intelligence" && <section><p className="section-intro">该关注对象参与形成的 Intelligence；它们可能同时由其他关注对象支持。</p>{relatedIntelligence.length ? relatedIntelligence.map(value => <IntelligenceCard key={value.id} item={value} navigate={navigate} />) : <Empty title="还没有参与形成的洞察" copy="内容处理完成后，相关发现会在这里出现。" />}</section>}
    {tab === "topics" && <section className="topic-preview"><p className="eyebrow">相关主题</p><h2>{item.topicIds.length ? topic.name : "还没有相关主题"}</h2><p>{item.topicIds.length ? "这个关注对象贡献过 Evidence / Intelligence，但主题并不归属于它。" : "当跨内容洞察形成长期联系时，主题会出现。"}</p>{item.topicIds.length > 0 && <Button variant="quiet" onClick={() => navigate("topic-detail")}>查看主题</Button>}</section>}
  </>;
}

function FollowingFocusSettings({ item }: { item: Following }) {
  const choices = ["Agent", "商业化", "模型能力", "Benchmark", "技术实现"];
  const [mode, setMode] = useState<"default" | "custom">(item.focusMode);
  const [selectedFocus, setSelectedFocus] = useState(item.focus.filter(value => choices.includes(value)));
  const [processing, setProcessing] = useState(item.processing);
  const toggleFocus = (value: string) => setSelectedFocus(current => current.includes(value) ? current.filter(item => item !== value) : [...current, value]);
  const toggleProcessing = (key: keyof Following["processing"]) => setProcessing(current => ({ ...current, [key]: !current[key] }));
  return <section className="following-focus-panel">
    <div className="focus-intro"><div><p className="eyebrow">Following Focus · 输入偏好</p><h2>关注重点</h2><p>关注重点决定哪些内容值得处理；Topic 是长期形成的知识认知。内容仍需经过 Evidence 与 Intelligence 才可能进入 Topic。</p></div><div className="focus-tags" aria-label="当前关注重点">{item.focus.map(value => <span key={value}>{value}</span>)}</div></div>
    <fieldset className="focus-mode"><legend>分析重点</legend><label><input type="radio" name={`focus-mode-${item.id}`} aria-label="使用我的默认设置" checked={mode === "default"} onChange={() => setMode("default")} /><span><strong>使用我的默认设置</strong><small>沿用 Settings 中的全局 Preferences</small></span></label><label><input type="radio" name={`focus-mode-${item.id}`} aria-label="为这个关注单独设置" checked={mode === "custom"} onChange={() => setMode("custom")} /><span><strong>为这个关注单独设置</strong><small>只覆盖这个关注对象</small></span></label></fieldset>
    {mode === "custom" && <div className="focus-override"><fieldset><legend>这个关注的分析重点</legend><div className="check-options">{choices.map(value => <label key={value}><input type="checkbox" aria-label={value} checked={selectedFocus.includes(value)} onChange={() => toggleFocus(value)} />{value}</label>)}</div></fieldset><div className="processing-settings"><h3>内容处理</h3><p>持续关注的频道会先判断内容是否值得处理，再按这些偏好生成产物。</p><div className="processing-options"><label><input type="checkbox" aria-label="生成摘要" checked={processing.summary} onChange={() => toggleProcessing("summary")} />生成摘要</label><label><input type="checkbox" aria-label="提取值得关注的洞察" checked={processing.intelligence} onChange={() => toggleProcessing("intelligence")} />提取值得关注的洞察</label><label><input type="checkbox" aria-label="自动关联主题" checked={processing.topics} onChange={() => toggleProcessing("topics")} />自动关联主题</label></div></div><p className="demo-state-note">仅更新当前页面状态，不写入真实设置。</p></div>}
  </section>;
}

/**
 * Per-Following language override (progressive disclosure).
 *
 * Default inherits the global content output language. Optionally a single
 * Following can output in a different language — e.g. general sources stay in
 * 简体中文 while an English-learning source outputs English. This only changes
 * the language of generated artifacts for this Following; it never rewrites
 * how source content is stored. Browser-state only.
 */
function FollowingLanguageSettings({ item }: { item: Following }) {
  const { settings, followingOverrides, setFollowingOverride } = useLanguage();
  const stored = followingOverrides[item.id];
  const mode = stored?.mode ?? "global";
  const customLanguage = stored?.outputLanguage ?? "English";
  const effective = mode === "custom" ? customLanguage : settings.outputLanguage;
  const chooseMode = (next: "global" | "custom") => setFollowingOverride(item.id, { mode: next, outputLanguage: next === "custom" ? customLanguage : settings.outputLanguage });
  const chooseLanguage = (language: Language) => setFollowingOverride(item.id, { mode: "custom", outputLanguage: language });
  return <section className="following-language-panel">
    <div className="focus-intro"><div><p className="eyebrow">Following Language · 输出语言</p><h2>这个关注的内容输出语言</h2><p>源内容始终按原始语言保留；这里只决定这个关注对象生成的摘要、要点、章节与洞察使用哪种语言。</p></div><div className="focus-tags" aria-label="当前输出语言"><span>{effective}</span></div></div>
    <fieldset className="focus-mode"><legend>输出语言</legend>
      <label><input type="radio" name={`language-mode-${item.id}`} aria-label="使用全局语言设置" checked={mode === "global"} onChange={() => chooseMode("global")} /><span><strong>使用全局语言设置</strong><small>当前全局输出语言：{settings.outputLanguage}</small></span></label>
      <label><input type="radio" name={`language-mode-${item.id}`} aria-label="为这个关注单独设置输出语言" checked={mode === "custom"} onChange={() => chooseMode("custom")} /><span><strong>为这个关注单独设置</strong><small>只覆盖这个关注对象的输出语言</small></span></label>
    </fieldset>
    {mode === "custom" && <div className="focus-override">
      <fieldset><legend>这个关注的内容输出语言</legend><div className="radio-options">{(["简体中文", "English"] as Language[]).map(language => <label key={language}><input type="radio" name={`language-override-${item.id}`} aria-label={`输出语言 ${language}`} checked={customLanguage === language} onChange={() => chooseLanguage(language)} />{language}</label>)}</div></fieldset>
      <p className="language-override-example">示例：一般来源输出简体中文，英语学习类来源单独输出 English。</p>
      <p className="demo-state-note">仅更新当前页面状态，不写入真实设置，也不会改变源内容的存储语言。</p>
    </div>}
  </section>;
}

function ContentList({ items, navigate }: { items: ContentItem[]; navigate: Navigate }) {
  return <section><div className="section-title"><div><p className="eyebrow">Content</p><h2>内容</h2></div></div><div className="content-list">{items.map(item => <button key={item.id} aria-label={`查看内容：${item.title}`} onClick={() => navigate(contentRoutes[item.id])}><div><ProviderLabel provider={item.kind} /><h3>{item.title}</h3><p>{item.publishedAt} · {item.positionLabel}</p></div><div><strong>{item.status}</strong><small>{item.summary ? "摘要已生成" : "摘要未生成"} · {item.intelligenceIds.length} 条 Intelligence</small></div></button>)}</div></section>;
}

export function ContentDetailPage({ contentId, navigate, openResearch }: { contentId: string; navigate: Navigate; openResearch: OpenResearch }) {
  const item = getContent(contentId) ?? contents[0];
  const following = getFollowing(item.followingId)!;
  const itemEvidence = evidence.filter(value => value.contentId === item.id);
  const { settings, effectiveOutputLanguage } = useLanguage();
  const outputLanguage = effectiveOutputLanguage(item.followingId);
  const [retry, setRetry] = useState<AsyncState>("idle");
  const [selectedChapter, setSelectedChapter] = useState<{ time: string; title: string; context: string } | null>(null);
  const [sourceLinkOpened, setSourceLinkOpened] = useState(false);
  const [detailSummary, setDetailSummary] = useState<AsyncState>("idle");
  const [evidenceDisplay, setEvidenceDisplay] = useState<EvidenceDisplay>(settings.evidenceDisplay);
  const [transcriptTranslation, setTranscriptTranslation] = useState<AsyncState>("idle");
  const retryAnalysis = () => { setRetry("checking"); window.setTimeout(() => setRetry("success"), 150); };
  const generateDetailedSummary = () => { setDetailSummary("checking"); window.setTimeout(() => setDetailSummary("success"), 150); };
  const translateTranscript = () => { setTranscriptTranslation("checking"); window.setTimeout(() => setTranscriptTranslation("success"), 150); };
  const relatedIntelligence = intelligence.filter(value => item.intelligenceIds.includes(value.id));
  const openIntelligence = () => navigate(relatedIntelligence[0]?.id === "intel-outcome-pricing" ? "intelligence-detail-pricing" : "intelligence-detail");
  const transcriptLines = transcriptTranslation === "success" && item.translatedTranscript ? item.translatedTranscript : item.transcript;
  const canTranslateTranscript = item.sourceLanguage !== outputLanguage && Boolean(item.translatedTranscript) && transcriptTranslation !== "success";
  return <>
    <div className="breadcrumbs"><button onClick={() => navigate("following")}>关注</button><span>/</span><button onClick={() => navigate(followingRoutes[following.id])}>{following.name}</button><span>/</span><span>内容</span></div>
    <SectionHeader eyebrow={item.kind} title={item.title} description={`${following.name} · ${item.publishedAt} · ${item.positionLabel}`} />
    {item.status !== "失败" && <>
      <section className="content-source-bar" aria-label="内容来源"><div><ProviderLabel provider={item.provider} type={following.objectType} /><span>来源：{following.name}</span><span>发布：{item.publishedAt}</span><span>时长 / 位置：{item.positionLabel}</span></div><Button variant="secondary" onClick={() => setSourceLinkOpened(true)}>打开原内容（Demo）</Button></section>
      <LanguageBadge sourceLanguage={item.sourceLanguage} outputLanguage={outputLanguage} />
      {sourceLinkOpened && <StatusLine title="原内容链接已定位（Demo）">没有打开网页或请求真实 Provider；此交互只验证原内容入口。</StatusLine>}
      {item.summary ? <>
        <section className="content-summary"><div className="summary-heading"><div><p className="eyebrow">视频笔记 · Content-level artifact</p><h2>视频摘要</h2></div><span>{item.summary.detailLevel}摘要</span></div><p className="summary-policy">单个视频默认可以生成摘要；持续关注的频道会先判断是否值得处理，再按关注设置生成。</p><div className="one-line-summary"><strong>一句话总结</strong><p>{item.summary.oneLine}</p></div><div className="artifact-distinction"><strong>Summary 回答“这个内容讲了什么”</strong><span>Intelligence 回答“发现了什么值得长期追踪的判断”</span></div>{item.summary.detailLevel === "简要" && detailSummary !== "success" && <Button variant="secondary" onClick={generateDetailedSummary} disabled={detailSummary === "checking"}>{detailSummary === "checking" ? "正在生成（Demo）…" : "生成详细摘要（Demo）"}</Button>}{detailSummary === "success" && <StatusLine tone="success" title="详细摘要已生成（Demo）">只更新当前页面状态，没有调用模型或保存数据。</StatusLine>}</section>
        <section className="summary-section"><p className="eyebrow">Key points</p><h2>核心要点</h2><ul>{item.summary.keyPoints.map(point => <li key={point}>{point}</li>)}</ul></section>
        <section className="summary-section"><p className="eyebrow">Timestamp chapters</p><h2>时间戳章节</h2><div className="chapter-list">{item.summary.chapters.map(chapter => <button key={chapter.time} aria-label={`跳到 ${chapter.time}：${chapter.title}`} className={selectedChapter?.time === chapter.time ? "active" : ""} onClick={() => setSelectedChapter(chapter)}><time>{chapter.time}</time><span><strong>{chapter.title}</strong><small>{chapter.context}</small></span></button>)}</div>{selectedChapter && <StatusLine tone="success" title={`已定位到 ${selectedChapter.time} · ${selectedChapter.title}（Demo）`}>{selectedChapter.context} 没有播放或请求真实视频。</StatusLine>}</section>
      </> : <section className="content-summary summary-pending"><p className="eyebrow">Content notes</p><h2>{item.provider === "X" ? "内容摘要" : "视频摘要"}</h2><StatusLine title={item.status === "分析中" ? "正在判断是否值得处理" : "摘要尚未生成"}>持续关注不会默认给每个内容生成长摘要；用户可在关注设置中调整处理方式。</StatusLine></section>}
      <details className="transcript"><summary>{item.provider === "X" ? "查看原帖文本" : "查看可追溯内容文本"}</summary>
        <div className="transcript-translation">
          <p className="transcript-policy">为减少模型使用量，默认只翻译摘要、要点、章节和 Evidence。完整字幕可按需翻译。</p>
          {canTranslateTranscript && <Button variant="secondary" aria-label="翻译完整字幕" onClick={translateTranscript} disabled={transcriptTranslation === "checking"}>{transcriptTranslation === "checking" ? "正在翻译完整字幕（Demo）…" : "翻译完整字幕"}</Button>}
          {transcriptTranslation === "success" && <StatusLine tone="success" title="完整字幕已翻译（Demo）">只切换当前页面展示，没有调用模型、网络或写入数据；原始字幕仍按源语言保留。</StatusLine>}
          {!canTranslateTranscript && transcriptTranslation !== "success" && <p className="transcript-no-translation">当前内容的源语言与输出语言一致，或没有可翻译的完整字幕 fixture。</p>}
        </div>
        {transcriptLines.length ? transcriptLines.map(line => <p className={line.evidenceId ? "highlight" : ""} key={line.position}><time>{line.position}</time>{line.text}{line.evidenceId && <small>Evidence {line.evidenceId}</small>}</p>) : <StatusLine title="正在处理内容">完成后会在这里显示可追溯文本。</StatusLine>}
      </details>
      <section className="content-evidence" aria-label="内容 Evidence"><div className="content-evidence-head"><div><p className="eyebrow">Evidence</p><h2>从这条内容保留的 Evidence</h2></div>{itemEvidence.length > 0 && itemEvidence.some(value => value.sourceLanguage !== outputLanguage) && <EvidenceDisplayToggle value={evidenceDisplay} onChange={setEvidenceDisplay} />}</div>{itemEvidence.length ? itemEvidence.map(value => <article className="content-evidence-item" key={value.id}><EvidenceExcerpt item={value} display={evidenceDisplay} outputLanguage={outputLanguage} /><footer>Evidence {value.id} · {value.position}<span className="evidence-source-lang"> · 源语言 {value.sourceLanguage}</span></footer></article>) : <StatusLine title="没有需要长期保留的 Evidence">内容摘要仍然可用；没有 Evidence 不代表摘要失败。</StatusLine>}</section>
      <section className="content-intelligence"><p className="eyebrow">Intelligence · 长期判断</p><h2>由该内容参与形成的 Intelligence</h2>{relatedIntelligence.length ? <><p>{relatedIntelligence[0].title}</p><p className="content-contribution">这条视频贡献 {itemEvidence.length} 条 Evidence，并参与 {relatedIntelligence.length} 条跨来源 Intelligence。</p><Button onClick={openIntelligence}>查看参与形成的洞察</Button></> : <StatusLine title="未发现值得长期保留的新洞察">摘要已成功生成，这不是处理失败。这个内容仍作为视频笔记保留，但不会因为有摘要就自动进入 Intelligence。</StatusLine>}</section>
      <section className="topic-preview content-topic"><p className="eyebrow">Related Topics · 长期认知</p><h2>{item.topicIds.length ? topic.name : "尚无相关主题"}</h2><p>{item.topicIds.length ? "Topic 由长期 Evidence 与 Intelligence 形成，不等同于这条内容的摘要。" : "只有形成可长期追踪的 Intelligence 后，内容才可能参与 Topic。"}</p>{item.topicIds.length > 0 && <Button variant="quiet" onClick={() => navigate("topic-detail")}>查看相关主题</Button>}</section>
      <section className="content-research"><div><p className="eyebrow">Research</p><h2>围绕这条内容继续调研</h2><p>以当前 Content 为范围进入资料库优先的 Research；不会默认探索外部网络。</p></div><Button onClick={() => openResearch({ kind: "内容", label: item.title })}>围绕此内容调研</Button></section>
      {itemEvidence[0] && <p className="location-note">定位到 {itemEvidence[0].position} · Evidence {itemEvidence[0].id}</p>}
      {item.intelligenceIds.length > 0 && <Button variant="quiet" onClick={openIntelligence}>返回洞察</Button>}
    </>}
    {item.status === "失败" && <section className="failure-card"><p className="eyebrow">需要关注</p><h2>字幕读取在处理中断</h2><p>分析没有完成，但关注对象和已保存资料没有丢失。</p><div className="explanation-grid"><div><strong>发生了什么</strong><p>这个内容的字幕响应暂时不完整，Demo 停止了后续分析。</p></div><div><strong>你可以做什么</strong><p>稍后重新分析，或返回关注对象继续查看其他内容。</p></div></div>{retry === "idle" && <Button onClick={retryAnalysis}>重新分析（Demo）</Button>}{retry === "checking" && <StatusLine title="正在重新分析（Demo）…">不会创建真实处理任务。</StatusLine>}{retry === "success" && <StatusLine tone="success" title="重新分析完成（Demo）">模拟字幕已恢复，可以继续生成洞察。</StatusLine>}</section>}
  </>;
}

export function IntelligenceListPage({ navigate }: { navigate: Navigate }) {
  const [filter, setFilter] = useState("全部");
  return <><SectionHeader eyebrow="Global Intelligence" title="从我所有关注的信息中，Agent 发现了什么？" description="洞察按判断组织，而不是按平台分组；同一判断可以由多个来源共同支持。" /><div className="filter-tabs">{["全部", "重要", "最新", "收藏"].map(item => <button key={item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>{item}</button>)}</div><div className="intel-stack">{intelligence.map(item => <IntelligenceCard key={item.id} item={item} navigate={navigate} />)}</div></>;
}

function EvidenceGroup({ title, ids, navigate, display, outputLanguage }: { title: string; ids: readonly string[]; navigate: Navigate; display: EvidenceDisplay; outputLanguage: Language }) {
  if (!ids.length) return null;
  return <section className="evidence-group"><h2>{title}</h2>{ids.map(id => { const ev = getEvidence(id)!; const content = getContent(ev.contentId)!; const following = getFollowing(ev.followingId)!; return <article className={`evidence-item stance-${ev.stance}`} key={id}><div className="evidence-meta"><ProviderLabel provider={ev.provider} /><span>{ev.strength}</span><span className="evidence-source-tag">源语言 {ev.sourceLanguage}</span></div><EvidenceExcerpt item={ev} display={display} outputLanguage={outputLanguage} /><dl><div><dt>关注</dt><dd>{following.name}</dd></div><div><dt>内容</dt><dd>{content.title}</dd></div><div><dt>位置</dt><dd>{ev.position}</dd></div></dl><p>{display === "译文" && ev.translatedContext && ev.sourceLanguage !== outputLanguage ? ev.translatedContext : ev.context}</p><Button variant="secondary" aria-label={`查看证据来源：${ev.provider} ${ev.position}`} onClick={() => navigate(contentRoutes[content.id])}>查看证据来源 · {ev.position}</Button></article>; })}</section>;
}

export function IntelligenceDetailPage({ intelligenceId, navigate, openResearch }: { intelligenceId: string; navigate: Navigate; openResearch: OpenResearch }) {
  const item = intelligence.find(value => value.id === intelligenceId) ?? intelligence[0];
  const conflicted = item.contradictingEvidenceIds.length > 0;
  const { settings } = useLanguage();
  const [evidenceDisplay, setEvidenceDisplay] = useState<EvidenceDisplay>(settings.evidenceDisplay);
  const outputLanguage = settings.outputLanguage;
  const sourceLanguages = useMemo(() => new Set(item.evidenceIds.map(id => getEvidence(id)?.sourceLanguage).filter(Boolean) as Language[]), [item.evidenceIds]);
  const crossLanguage = sourceLanguages.size > 1;
  return <>
    <div className="breadcrumbs"><button onClick={() => navigate("intelligence")}>洞察</button><span>/</span><span>详情</span></div>
    <div className="evidence-layout"><main className="claim-column">
      <SectionHeader eyebrow={`Current judgment · ${item.importance}`} title={item.title} description={item.summary} action={<Button onClick={() => openResearch({ kind: "洞察", label: item.title })}>深入调研</Button>} />
      <section className="reasoning"><p className="eyebrow">Why it matters</p><h2>为什么值得关注</h2><p>{item.why}</p></section>
      <section className="retention-reasons"><p className="eyebrow">为什么这条内容成为洞察？</p><h2>为什么值得保留</h2><ul>{item.retentionReasons.map(reason => <li key={reason}>✓ {reason}</li>)}</ul></section>
      <section className="confidence-block"><div><p className="eyebrow">当前支持程度</p><h2>{item.confidence}</h2></div><p>{conflicted ? "当前证据存在分歧。系统保留支持与反对观点，不强行统一。" : "多个独立来源支持当前判断，但它仍会随新 Evidence 更新。"}</p></section>
      <section className="source-chain"><p className="eyebrow">Sources</p><h2>{item.followingIds.length} 个关注对象共同参与</h2>{item.followingIds.map(id => { const following = getFollowing(id)!; return <button key={id} onClick={() => navigate(followingRoutes[following.id])}><ProviderLabel provider={following.provider} type={following.objectType} /><strong>{following.name}</strong><small>贡献 Evidence，洞察不归属于单一来源</small></button>; })}</section>
      <section className="topic-link"><p className="eyebrow">Related Topics</p><h2>{topic.name}</h2><p>{topic.currentUnderstanding}</p><Button variant="quiet" onClick={() => navigate("topic-detail")}>查看主题：{topic.name}</Button></section>
      <section className="uncertainty"><p className="eyebrow">仍需验证</p><h2>这不是最终事实</h2><ul>{item.stillNeedsValidation.map(value => <li key={value}>{value}</li>)}</ul><p className="last-updated">Last updated · {item.lastUpdated}</p><Button onClick={() => openResearch({ kind: "洞察", label: item.title })}>继续 Research</Button></section>
    </main><aside className="evidence-panel"><div className="panel-head"><p className="eyebrow">Evidence Spine</p><h2>为什么这样判断？</h2><p>支持、反对与条件性证据分别保留，并可回到原始位置。</p>{crossLanguage && <p className="cross-language-note">这条洞察由多种语言的来源共同支持；生成判断使用{outputLanguage}，每条 Evidence 仍保留各自的源语言与原始位置。</p>}<EvidenceDisplayToggle value={evidenceDisplay} onChange={setEvidenceDisplay} label="Evidence 显示" /></div><EvidenceGroup title="Supporting Evidence" ids={item.supportingEvidenceIds} navigate={navigate} display={evidenceDisplay} outputLanguage={outputLanguage} /><EvidenceGroup title="Contradicting Evidence" ids={item.contradictingEvidenceIds} navigate={navigate} display={evidenceDisplay} outputLanguage={outputLanguage} /><EvidenceGroup title="Conditional Evidence" ids={item.conditionalEvidenceIds} navigate={navigate} display={evidenceDisplay} outputLanguage={outputLanguage} /></aside></div>
  </>;
}

export function TopicListPage({ navigate }: { navigate: Navigate }) {
  const [suggestion, setSuggestion] = useState<"visible" | "followed" | "ignored">("visible");
  return <><SectionHeader eyebrow="Topics" title="跨来源长期累积的认知主题" description="Topic 不是关注对象的文件夹，而是多个洞察与 Evidence 形成的持续理解。" /><article className="topic-list-card"><button aria-label={`查看主题：${topic.name}`} onClick={() => navigate("topic-detail")}><div><p className="eyebrow">状态：{topic.lifecycle} · {topic.trend}</p><h2>{topic.name}</h2><p>{topic.summary}</p></div><div className="topic-counts"><span><strong>{topic.intelligenceIds.length}</strong>洞察</span><span><strong>{topic.followingIds.length}</strong>关注对象</span><span><strong>{topic.evidenceIds.length}</strong>Evidence</span></div></button></article>{suggestion !== "ignored" && <section className="suggested-topic"><div><p className="eyebrow">系统建议主题</p><h2>AI Agent Outcome Pricing</h2><p>近期出现 3 条相关 Evidence。只有关注后才会进入长期 Topic workspace。</p></div>{suggestion === "visible" ? <div className="actions"><Button onClick={() => setSuggestion("followed")}>关注这个主题</Button><Button variant="quiet" onClick={() => setSuggestion("ignored")}>暂时忽略</Button></div> : <StatusLine tone="success" title="已加入长期关注（Demo）">之后可重命名、合并、拆分或归档。</StatusLine>}</section>}</>;
}

export function TopicDetailPage({ navigate, openResearch }: { navigate: Navigate; openResearch: OpenResearch }) {
  const contributing = topic.followingIds.map(id => getFollowing(id)!);
  const [governance, setGovernance] = useState("");
  return <>
    <div className="breadcrumbs"><button onClick={() => navigate("topics")}>主题</button><span>/</span><span>{topic.name}</span></div>
    <SectionHeader eyebrow="Knowledge Topic · 跨来源" title={topic.name} description={topic.summary} action={<Button onClick={() => openResearch({ kind: "Topic", label: topic.name })}>深入调研</Button>} />
    <div className="topic-state"><strong>状态：{topic.lifecycle}</strong><span>{topic.trend}</span><span>{topic.lifecycleChange}</span></div>
    <section className="understanding"><p className="eyebrow">Current understanding</p><h2>我们现在对这个主题知道什么？</h2><p>{topic.currentUnderstanding}</p></section>
    <div className="topic-detail-grid"><section><p className="eyebrow">最近变化</p><h2>从单一观察升级为跨来源趋势</h2><p>{topic.recentChange}</p></section><section><p className="eyebrow">仍需验证</p><h2>关键未知</h2><ul>{topic.openQuestions.map(item => <li key={item}>{item}</li>)}</ul></section></div>
    <section className="contributor-section"><p className="eyebrow">Following contribution</p><h2>主要贡献来源</h2><p>{topic.followingIds.length} 个关注对象共同贡献了这个主题的当前理解。</p><div>{contributing.map(item => <article key={item.id}><ProviderLabel provider={item.provider} type={item.objectType} /><h3>{item.name}</h3><p>{item.intelligenceIds.length} 条相关洞察</p></article>)}</div></section>
    <section className="research-evidence"><p className="eyebrow">Evidence</p><h2>支持与反对都保留在主题中</h2>{evidence.slice(4, 7).map(item => <article key={item.id}><strong>{item.id} · {item.provider} · {item.strength}</strong><p>{item.quote}</p><span>{getFollowing(item.followingId)?.name}</span></article>)}</section>
    <section className="dashboard-section"><div className="section-title"><div><p className="eyebrow">Important Intelligence</p><h2>重要洞察</h2></div></div><IntelligenceCard navigate={navigate} /></section>
    <section className="relationship-view"><p className="eyebrow">Compact relationship view</p><h2>知识如何汇聚</h2><ol><li><span>关注</span><strong>3 个跨平台对象</strong></li><li><span>内容</span><strong>视频与帖子</strong></li><li><span>Evidence</span><strong>E1 + E2 + E3</strong></li><li><span>洞察</span><strong>{intelligence[0].title}</strong></li><li><span>Topic</span><strong>{topic.name}</strong></li><li><span>Research</span><strong>{research.question}</strong></li></ol></section>
    <section className="timeline"><p className="eyebrow">Knowledge Evolution</p><h2>知识演进</h2><p>每次理解更新都保留触发它的 Evidence，而不是覆盖过去。</p><div>{topic.evolution.map(entry => <article key={entry.date}><time>{entry.date}</time><p>{entry.text}</p></article>)}</div></section>
    <section className="research-history"><p className="eyebrow">Research snapshots</p><h2>Research History</h2>{research.versions.map(version => <article key={version.id}><strong>{version.id} · {version.date}</strong><p>{version.conclusion}</p><button onClick={() => openResearch({ kind: "Topic", label: topic.name })}>查看变化</button></article>)}</section>
    <section className="topic-governance"><div><p className="eyebrow">Topic governance</p><h2>主题管理</h2><p>这些动作只影响 Demo 展示，不修改真实资料。</p></div><div className="actions"><Button variant="secondary" aria-label="重命名主题" onClick={() => setGovernance("重命名")}>Rename</Button><Button variant="secondary" aria-label="合并主题" onClick={() => setGovernance("合并")}>Merge</Button><Button variant="danger" aria-label="归档主题" onClick={() => setGovernance("归档")}>Archive</Button></div>{governance && <StatusLine title={`${governance}预览（Demo）`}>未执行真实 Topic 操作。</StatusLine>}</section>
  </>;
}

export function ResearchPage({ route, navigate, context }: { route: Route; navigate: Navigate; context: ResearchContext }) {
  const [question, setQuestion] = useState(research.question);
  const [scopeMode, setScopeMode] = useState<ResearchScopeMode>("library");
  const [specified, setSpecified] = useState<SpecifiedScope>("topic");
  const [specifiedEntity, setSpecifiedEntity] = useState(topic.name);
  const [selectedVersion, setSelectedVersion] = useState<"v1" | "v2">("v2");
  const labels: Record<SpecifiedScope, string> = { following: "关注对象", content: "内容", intelligence: "洞察", topic: "Topic" };
  const entities: Record<SpecifiedScope, string[]> = {
    following: followings.slice(0, 3).map(item => item.name),
    content: contents.slice(0, 3).map(item => item.title),
    intelligence: intelligence.map(item => item.title),
    topic: [topic.name],
  };
  const chooseSpecifiedType = (value: SpecifiedScope) => { setSpecified(value); setSpecifiedEntity(entities[value][0]); };
  const scopeLabel = scopeMode === "library" ? "我的资料库" : scopeMode === "current" ? `${context.kind} · ${context.label}` : `指定范围 · ${labels[specified]} · ${specifiedEntity}`;
  const version = research.versions.find(item => item.id === selectedVersion)!;
  if (route === "research-result") return <>
    <div className="breadcrumbs"><button onClick={() => navigate("research")}>调研</button><span>/</span><span>结果</span></div>
    <SectionHeader eyebrow={`Research snapshot · ${version.id}`} title={question} description={`研究范围：${scopeLabel}`} action={selectedVersion === "v1" ? <Button onClick={() => setSelectedVersion("v2")}>查看 v2</Button> : undefined} />
    <div className="snapshot-meta"><span>研究生成：{version.date}</span><span>Evidence 截止：{version.cutoff}</span><span>这是当时 Evidence 的研究快照</span></div>
    <section className="research-conclusion"><p className="eyebrow">结论</p><h2>{version.conclusion}</h2></section>
    {selectedVersion === "v2" && <section className="research-comparison"><p className="eyebrow">Version comparison</p><h2>Compared with previous research</h2><div><article><h3>新增 Evidence</h3><p>E5 · YouTube 定价观察<br />E6 · B站混合收费案例<br />E7 · X 企业采购反对观点</p></article><article><h3>删除 / 失效 Evidence</h3><p>无删除。v1 的单来源判断降级为历史背景。</p></article><article><h3>判断变化</h3><p>从“订阅制仍占主导”更新为“混合收费增加，但证据存在分歧”。</p></article><article><h3>仍未解决的问题</h3><p>结果定义、归因和企业采购接受度仍需验证。</p></article></div></section>}
    <div className="research-grid"><section><h2>关键发现</h2><ol>{research.findings.map(item => <li key={item}>{item}</li>)}</ol></section><section><h2>不同观点</h2><ul>{research.perspectives.map(item => <li key={item}>{item}</li>)}</ul></section></div>
    <section className="research-evidence"><h2>我的资料库证据</h2>{version.evidenceIds.map(id => getEvidence(id)!).map(item => { const following = getFollowing(item.followingId)!; return <article key={item.id}><strong>{item.id} · {item.provider} · {item.position}</strong><p>{item.quote}</p><span>{following.name}</span></article>; })}</section>
    <section className="uncertainty"><p className="eyebrow">仍需验证</p><h2>不确定信息</h2><ul>{research.unknowns.map(item => <li key={item}>{item}</li>)}</ul></section>
    <section className="contributor-section"><p className="eyebrow">Sources / Following</p><h2>本次使用的关注对象</h2><p>AI Explained · 某 AI UP 主 · @agentbuilder</p></section>
    <section className="external-placeholder"><h2>External exploration</h2><p>未启用。本次结果没有使用外部探索，也没有把外部发现写入已有 Topic。</p></section>
  </>;
  return <>
    <SectionHeader eyebrow="Research Setup" title="从已有资料出发，明确这次要研究什么" description="默认使用我的资料库。你可以改为当前对象或指定范围；不会默认探索整个互联网。" />
    <section className="research-history"><p className="eyebrow">Research snapshots</p><h2>Research History</h2><p>Research 是某个时间点基于当时 Evidence 的快照，不会覆盖旧结论。</p>{research.versions.map(item => <article key={item.id}><strong>{item.id} · {item.date}</strong><p>{item.conclusion}</p><button aria-label={`查看 Research ${item.id}`} onClick={() => { setSelectedVersion(item.id as "v1" | "v2"); navigate("research-result"); }}>查看快照</button></article>)}</section>
    <div className="research-form"><label className="field"><span>研究问题</span><textarea value={question} onChange={event => setQuestion(event.target.value)} rows={3} /></label>
      <fieldset className="scope-options"><legend>调研范围</legend>
        <label className={scopeMode === "library" ? "selected" : ""}><input aria-label="我的资料库" type="radio" name="scope" checked={scopeMode === "library"} onChange={() => setScopeMode("library")} /><span><strong>我的资料库</strong><small>使用已经处理的洞察、Evidence 和关注内容</small></span></label>
        <label className={scopeMode === "current" ? "selected" : ""}><input aria-label={`当前对象：${context.kind} · ${context.label}`} type="radio" name="scope" checked={scopeMode === "current"} onChange={() => setScopeMode("current")} /><span><strong>当前对象</strong><small>{context.kind} · {context.label}</small></span></label>
        <label className={scopeMode === "specified" ? "selected" : ""}><input aria-label="指定范围" type="radio" name="scope" checked={scopeMode === "specified"} onChange={() => setScopeMode("specified")} /><span><strong>指定范围</strong><small>选择关注对象、内容、洞察或 Topic</small></span></label>
        <label className="disabled"><input aria-label="扩展探索（后续能力）" type="radio" name="scope" disabled /><span><strong>扩展探索</strong><small>Coming later · 需要用户主动启用</small></span></label>
      </fieldset>
      {scopeMode === "specified" && <div className="two-fields"><label className="field"><span>范围类型</span><select aria-label="范围类型" value={specified} onChange={event => chooseSpecifiedType(event.target.value as SpecifiedScope)}><option value="following">关注对象</option><option value="content">内容</option><option value="intelligence">洞察</option><option value="topic">Topic</option></select></label><label className="field"><span>选择对象</span><select aria-label="选择具体范围" value={specifiedEntity} onChange={event => setSpecifiedEntity(event.target.value)}>{entities[specified].map(item => <option key={item}>{item}</option>)}</select></label></div>}
      <StatusLine title={scopeMode === "specified" ? `指定范围：${labels[specified]} · ${specifiedEntity}` : `当前范围：${scopeLabel}`}>Demo 只读取同一套本地 fixture，不会调用 AI 或外部搜索。</StatusLine>
      <Button onClick={() => navigate("research-result")} disabled={!question.trim()}>开始调研</Button>
    </div>
  </>;
}

function ModelStrategySettings() {
  const [strategy, setStrategy] = useState("automatic");
  const [advanced, setAdvanced] = useState(false);
  const strategies = [
    ["automatic", "自动", "根据任务复杂度、成本和可用能力自动选择"],
    ["local", "优先本地", "尽量在本机处理，必要时使用云模型"],
    ["quality", "质量优先", "更多高价值任务使用强模型"],
    ["cost", "成本优先", "尽量减少云模型使用"],
  ];
  return <><h2>AI 服务</h2><p className="panel-copy">先选择你在意的取向。系统会根据任务复杂度选择合适模型，不要求你配置每一步。</p>
    <fieldset className="strategy-options"><legend>模型策略</legend>{strategies.map(([id, label, copy]) => <label className={strategy === id ? "selected" : ""} key={id}><input aria-label={label} type="radio" name="model-strategy" checked={strategy === id} onChange={() => setStrategy(id)} /><span><strong>{label}</strong><small>{copy}</small></span></label>)}</fieldset>
    <StatusLine title={`当前策略：${strategies.find(item => item[0] === strategy)?.[1]}`}>{strategy === "local" ? "本地模型能完成的任务优先留在电脑上；必要时使用云模型。" : strategy === "cost" ? "预算只影响模型选择策略，不会让系统绕过最低质量要求。" : "低频高价值任务与频繁基础任务会使用不同能力层级。"}</StatusLine>
    <section className="connection-summary"><h3>当前配置</h3><div><span>本地模型<strong>已连接 · Ollama（Demo）</strong></span><span>云端模型<strong>已连接 · 2 个（Demo）</strong></span></div><p>本地模型在你的电脑上运行，可减少云端调用并提高隐私。实际可用性取决于设备性能与模型能力。</p><p>本地不等于低质量；云端也不会用于每个任务。系统按任务复杂度选择满足要求的模型。</p></section>
    <section className="usage-preferences"><div><p className="eyebrow">AI 使用偏好</p><h3>每月预算</h3><strong>¥50 / month</strong></div><div><span>本月预计<strong>¥18.70</strong></span><span>模型使用<strong>79% Local · 21% Cloud</strong></span></div><p>预算只影响模型选择策略，不会让系统绕过最低质量要求。</p></section>
    <Button variant="secondary" onClick={() => setAdvanced(value => !value)}>{advanced ? "收起高级模型设置" : "高级模型设置"}</Button>
    {advanced && <section className="advanced-routing"><div className="section-title"><div><p className="eyebrow">Advanced model settings</p><h2>任务与模型</h2></div><Button variant="quiet" onClick={() => setStrategy("automatic")}>恢复自动推荐</Button></div><p>按任务需要的能力选择模型类别，不需要配置内部 pipeline step。</p><div className="routing-table">{[["基础处理", "视频摘要、时间戳章节与基础要点（低成本任务）", "Ollama · Local"], ["Intelligence", "Evidence 比较与值得长期追踪的判断", "Standard reasoning"], ["深度分析", "冲突推理与重要洞察验证", "High-capability cloud"], ["Research", "跨来源综合与研究快照", "High-capability model"]].map(row => <div key={row[0]}><strong>{row[0]}</strong><span>{row[1]}</span><b>{row[2]}</b></div>)}</div><div className="capability-grid"><article><ProviderLabel provider="Cloud" /><h3>Kimi K3</h3><p className="muted">已验证能力 / 适合哪些任务</p><ul><li>✓ 长上下文、结构化输出</li><li>✓ 中文、深度推理</li><li>✓ Research 适用</li></ul></article><article><ProviderLabel provider="Local" /><h3>Local Small Model</h3><p className="muted">已验证能力 / 适合哪些任务</p><ul><li>✓ 视频摘要、章节、基础要点</li><li>✓ 本地运行</li><li>△ 普通 Intelligence</li><li>Deep Research 不适用</li></ul></article></div><details className="advanced"><summary>Diagnostics · 执行细节</summary><p>Capability、可用性判断与执行记录只在诊断层展示，不进入普通 Settings。</p><p>Provider 结构预览：OpenAI · Anthropic · Google · NVIDIA NIM · Other / Ollama · MLX · llama.cpp</p></details></section>}
  </>;
}

function DataSettings() {
  const [backup, setBackup] = useState<"idle" | "created" | "selecting" | "valid" | "corrupt" | "restored">("idle");
  const [vault, setVault] = useState<"idle" | "choosing" | "connected" | "published">("idle");
  const [exports, setExports] = useState(["视频笔记 / Content Notes", "Intelligence", "Topics", "Research", "Following / Sources"]);
  const connectVault = () => { setVault("choosing"); window.setTimeout(() => setVault("connected"), 140); };
  const publish = () => { window.setTimeout(() => setVault("published"), 140); };
  const toggleExport = (value: string) => setExports(current => current.includes(value) ? current.filter(item => item !== value) : [...current, value]);
  return <><h2>我的 Intelligence 数据存在哪里？</h2><p className="panel-copy">你的关注、处理记录、Evidence、洞察、主题、调研与偏好默认保存在本机。</p><section className="storage-card"><ProviderLabel provider="保存在本机" /><h3>本地数据存储</h3><p>SQLite 保存结构化运行数据；大文本与附件保存在本地文件中。</p><code>~/Library/Application Support/Intelligence/</code><div className="data-kinds">{["关注", "内容记录", "Evidence", "洞察", "主题", "调研", "偏好"].map(item => <span key={item}>{item}</span>)}</div><small>这是 Demo 表达，不会创建目录或写入数据库。</small></section>
    <section className="backup-card"><div><p className="eyebrow">Backup & Restore</p><h3>Intelligence Backup</h3><p>数据存在本机，所以你可以创建独立备份并在需要时恢复。Backup 不是 Cloud Sync。</p></div><div className="actions"><Button onClick={() => setBackup("created")}>创建备份</Button><Button variant="secondary" onClick={() => setBackup("selecting")}>恢复备份</Button></div>{backup !== "idle" && backup !== "selecting" && <div className="backup-summary"><strong>Last backup: Today 21:32</strong><span>Status: Healthy</span><p>包含：关注、内容记录、Evidence、洞察、主题、Research、偏好</p></div>}{backup === "selecting" && <div className="backup-picker"><p>选择一个 Demo backup 进行完整性检查：</p><div className="actions"><Button onClick={() => setBackup("valid")}>选择有效备份</Button><Button variant="secondary" onClick={() => setBackup("corrupt")}>选择损坏备份</Button></div></div>}{backup === "valid" && <><StatusLine tone="success" title="Backup valid">完整性检查通过。恢复前不会更改当前数据。</StatusLine><div className="backup-counts">{["5 Following", "126 Contents", "47 Evidence", "18 Intelligence", "4 Topics", "3 Research"].map(item => <span key={item}>{item}</span>)}</div><div className="actions"><Button onClick={() => setBackup("restored")}>恢复</Button><Button variant="secondary" onClick={() => setBackup("corrupt")}>选择损坏备份</Button></div></>}{backup === "corrupt" && <StatusLine tone="danger" title="这个备份未通过完整性检查，不会覆盖你当前的数据。"><button className="inline-action" onClick={() => setBackup("selecting")}>选择其他备份</button></StatusLine>}{backup === "restored" && <StatusLine tone="success" title="恢复完成（Demo）">只更新了页面状态，没有读取或写入文件。</StatusLine>}</section>
    <section className="obsidian-card"><div><p className="eyebrow">Optional publishing target</p><h3>Obsidian</h3><p>将视频笔记、洞察、主题和调研结果发布到 Obsidian Vault。</p></div>{vault === "idle" || vault === "choosing" ? <><p className="muted">状态：未连接</p><Button onClick={connectVault} disabled={vault === "choosing"}>{vault === "choosing" ? "正在模拟选择文件夹…" : "连接 Obsidian"}</Button></> : <><StatusLine tone="success" title="Obsidian Vault 已连接（Demo）">/Users/demo/Documents/Obsidian/Intelligence</StatusLine><strong className="one-way">单向发布：Intelligence → Obsidian</strong><fieldset className="export-options"><legend>发布内容</legend>{["视频笔记 / Content Notes", "Intelligence", "Topics", "Research", "Following / Sources", "Raw Transcript"].map(item => <label key={item}><input aria-label={item} type="checkbox" checked={exports.includes(item)} onChange={() => toggleExport(item)} />{item}</label>)}</fieldset><Button onClick={publish}>立即发布</Button>{vault === "published" && <StatusLine tone="success" title="已发布到 Obsidian（Demo）">没有创建真实 Obsidian 文件。</StatusLine>}</>}<p className="data-note">Obsidian 是单向发布目标，不是运行数据库，也不是双向实时同步。Intelligence 仍会在本机保留完整运行数据。</p></section>
  </>;
}

function LanguageSettingsPanel() {
  const { settings, setUiLanguage, setOutputLanguage, setEvidenceDisplay } = useLanguage();
  const languages: Language[] = ["简体中文", "English"];
  const displays: EvidenceDisplay[] = ["译文", "双语", "原文"];
  return <>
    <h2>常规 / 语言</h2>
    <p className="panel-copy">界面语言、源内容语言与内容输出语言是三个独立概念。源内容始终按原始语言保留；输出语言只决定生成物（摘要、要点、章节、洞察、主题、调研）的呈现语言。</p>
    <section className="language-setting">
      <div className="language-setting-head"><p className="eyebrow">UI language</p><h3>界面语言</h3><p>菜单、按钮与说明文字使用的语言。</p></div>
      <fieldset className="radio-options" aria-label="界面语言">{languages.map(language => <label key={language}><input type="radio" name="ui-language" aria-label={`界面语言 ${language}`} checked={settings.uiLanguage === language} onChange={() => setUiLanguage(language)} />{language}</label>)}</fieldset>
      <p className="language-note">Demo 界面文案当前以简体中文占位；切换界面语言不会改变内容或生成物的存储与语言。</p>
    </section>
    <section className="language-setting">
      <div className="language-setting-head"><p className="eyebrow">Content output language</p><h3>内容输出语言</h3><p>摘要、要点、章节、洞察、主题与调研结果使用的语言。</p></div>
      <fieldset className="radio-options" aria-label="内容输出语言">{languages.map(language => <label key={language}><input type="radio" name="output-language" aria-label={`内容输出语言 ${language}`} checked={settings.outputLanguage === language} onChange={() => setOutputLanguage(language)} />{language}</label>)}</fieldset>
      <p className="language-note">你可以关注 English 来源，同时用简体中文阅读所有生成内容；源内容仍按原始语言保留。</p>
    </section>
    <section className="language-setting">
      <div className="language-setting-head"><p className="eyebrow">Evidence display</p><h3>Evidence 默认显示</h3><p>当源语言与输出语言不同时，Evidence 摘录的默认呈现方式。</p></div>
      <fieldset className="radio-options" aria-label="Evidence 默认显示">{displays.map(display => <label key={display}><input type="radio" name="evidence-display" aria-label={`Evidence 默认显示 ${display}`} checked={settings.evidenceDisplay === display} onChange={() => setEvidenceDisplay(display)} />{display}</label>)}</fieldset>
      <p className="language-note">译文与双语只是阅读辅助；原摘录与来源位置始终是权威依据，翻译不会生成新的 Evidence 记录。</p>
    </section>
    <StatusLine title={`当前：界面 ${settings.uiLanguage} · 输出 ${settings.outputLanguage} · Evidence ${settings.evidenceDisplay}`}>这些设置只更新 Demo 浏览器状态，不会写入真实配置，也不会调用模型或网络。</StatusLine>
  </>;
}

export function SettingsPage({ section, setSection }: { section: SettingsSection; setSection: (section: SettingsSection) => void }) {
  const [inferred, setInferred] = useState([...preferences.inferred]);
  const nav = [["general", "常规 / 语言"], ["ai", "AI 服务"], ["providers", "内容 Provider"], ["analysis", "分析"], ["preferences", "偏好"], ["data", "数据"], ["system", "系统"]] as Array<[SettingsSection, string]>;
  return <>
    <SectionHeader eyebrow="Settings" title="设置" description="可配置项提供直接入口；系统判断说明当前动作与安全恢复方式。" />
    <div className="settings-layout"><nav aria-label="设置分组">{nav.map(([id, label]) => <button key={id} className={section === id ? "active" : ""} onClick={() => setSection(id)}>{label}</button>)}</nav><div className="settings-panel">
      {section === "general" && <LanguageSettingsPanel />}
      {section === "ai" && <ModelStrategySettings />}
      {section === "providers" && <><h2>内容 Provider</h2><p className="panel-copy">YouTube 是完整 Demo 示例；其余 Provider 只验证信息结构。</p>{["YouTube · 已配置", "B站 · Demo preview", "X · Demo preview", "Local · Demo preview"].map(item => <div className="settings-row" key={item}><strong>{item}</strong><span className="muted">在「关注」中管理</span></div>)}</>}
      {section === "analysis" && <><h2>分析</h2><label className="field"><span>分析方式</span><select defaultValue="evidence"><option value="evidence">证据优先</option><option>简洁总结</option><option>深度研究</option></select></label><label className="field"><span>Evidence 要求</span><select defaultValue="cross"><option value="cross">重要判断优先寻找交叉来源</option><option>至少 1 条证据</option></select></label></>}
      {section === "preferences" && <PreferenceCenter inferred={inferred} setInferred={setInferred} />}
      {section === "data" && <DataSettings />}
      {section === "system" && <><h2>系统</h2><StatusLine tone="success" title="运行正常">Provider 与处理队列均为模拟状态。</StatusLine><section className="quality-summary"><p className="eyebrow">过去 30 天 · Insights quality summary</p><h3>不是所有内容都会成为洞察</h3><div><span><strong>126</strong>内容</span><span>→ <strong>31</strong>候选</span><span>→ <strong>12</strong>Intelligence</span></div><p>9 个被保留 · 2 个被用户忽略 · 1 个合并到已有 Intelligence</p></section><details className="advanced"><summary>Advanced · Capability / Diagnostics</summary><div><p>内容分析能力 · Demo 已验证</p><p>最后状态检查 · 刚刚</p><p>内部调度与验证细节不进入普通用户主路径。</p></div></details></>}
    </div></div>
  </>;
}

function PreferenceCenter({ inferred, setInferred }: { inferred: string[]; setInferred: (items: string[]) => void }) {
  const [explicit, setExplicit] = useState([...preferences.explicit]);
  const [temporary, setTemporary] = useState([...preferences.temporary]);
  return <><h2>偏好</h2><p className="panel-copy">偏好的来源与生效范围始终可见，并可由你管理。</p><section className="preference-section"><div><p className="eyebrow">Explicit</p><h3>明确选择</h3><p>你主动选择的偏好。</p></div><div className="preference-items">{explicit.map(item => <article key={item}><span>{item}</span><button aria-label={`删除明确偏好：${item}`} onClick={() => setExplicit(explicit.filter(value => value !== item))}>删除</button></article>)}</div></section><section className="preference-section"><div><p className="eyebrow">Inferred</p><h3>推导得出</h3><p>这是系统根据你的使用反馈推导的。</p></div><div className="preference-items">{inferred.length ? inferred.map(item => <article key={item}><span>{item}</span><div><button aria-label={`确认推导偏好：${item}`} onClick={() => setInferred(inferred.filter(value => value !== item))}>确认</button><button aria-label={`忽略推导偏好：${item}`} onClick={() => setInferred(inferred.filter(value => value !== item))}>忽略</button></div></article>) : <p className="empty-inline">当前没有待确认的推导偏好。</p>}</div></section><section className="preference-section"><div><p className="eyebrow">Temporary</p><h3>临时</h3><p>到期后自动停止生效。</p></div><div className="preference-items">{temporary.map(item => <article className={item.state === "expired" ? "expired" : ""} key={item.label}><span>{item.label}<small>{item.meta}</small></span><button aria-label={`删除临时偏好：${item.label}`} onClick={() => setTemporary(temporary.filter(value => value.label !== item.label))}>删除</button></article>)}</div></section></>;
}

function Empty({ title, copy }: { title: string; copy: string }) {
  return <div className="empty-preview"><h3>{title}</h3><p>{copy}</p></div>;
}

export function DemoStateDrawer({ onClose, navigate }: { onClose: () => void; navigate: Navigate }) {
  const [state, setState] = useState("provider");
  const messages = useMemo(() => ({
    provider: ["AI 服务尚未配置", "前往 AI 服务设置即可继续；已保存资料不会丢失。", "前往设置"],
    providerUnavailable: ["AI 服务暂时不可用", "稍后重新检查。关注与已保存资料不会丢失。", "重新检查"],
    model: ["当前模型暂时无法用于内容分析", "系统无法用这个模型完成分析。可以重新验证，或在设置中更换模型。", "更换模型"],
    source: ["关注对象暂时无法访问", "Provider 没有返回公开内容。稍后重试或编辑 URL。", "编辑关注"],
    transcript: ["这个内容没有可用文本", "无法生成可追溯 Evidence，因此本次不会继续分析。", "返回关注"],
    processing: ["正在处理 3 个内容", "可以离开此页，完成后洞察会出现在首页。", "查看处理列表"],
    evidence: ["Evidence 暂时不可用", "当前判断缺少可追溯原文，因此不会作为可信洞察展示。", "查看内容状态"],
    research: ["还没有足够资料开始调研", "先积累洞察与 Evidence，再回到这里。", "查看关注"],
    offline: ["暂时无法连接本地服务", "本地数据没有丢失。恢复连接后可继续使用。", "重新检查"],
    emptyFollowing: ["还没有关注", "添加频道、账号、内容或本地资料后，Agent 才能开始工作。", "添加第一个关注"],
    emptyIntelligence: ["还没有洞察", "内容分析完成后，值得保留的发现会出现在这里。", "查看处理状态"],
    emptyTopic: ["还没有主题", "当多个洞察形成长期联系时，主题会自动出现。", "查看洞察"],
  }), []);
  const current = messages[state as keyof typeof messages];
  const recoveryRoute: Record<string, Route> = { provider: "settings", providerUnavailable: "settings", model: "settings", source: "following", transcript: "following", processing: "following", evidence: "intelligence", research: "following", offline: "home", emptyFollowing: "following-add", emptyIntelligence: "following", emptyTopic: "intelligence" };
  const recover = () => { onClose(); navigate(recoveryRoute[state]); };
  return <div className="drawer-overlay"><aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title"><div className="drawer-head"><div><p className="eyebrow">仅用于 UX Review</p><h2 id="drawer-title">异常 / 空 / Loading 状态</h2></div><button onClick={onClose}>关闭</button></div><p className="panel-copy">只切换前端预览，不触发真实操作。</p><div className="state-tabs">{Object.entries({ provider: "未配置", providerUnavailable: "Provider 不可用", model: "模型不可用", source: "关注不可用", transcript: "无文本", processing: "处理中", evidence: "无 Evidence", research: "Research 空", offline: "离线", emptyFollowing: "首次无关注", emptyIntelligence: "首次无洞察", emptyTopic: "无 Topic" }).map(([id, label]) => <button key={id} className={state === id ? "active" : ""} onClick={() => setState(id)}>{label}</button>)}</div><div className="state-preview"><h3>{current[0]}</h3><p>{current[1]}</p><Button onClick={recover}>{current[2]}</Button></div></aside></div>;
}
