import { useEffect, useMemo, useRef, useState } from "react";
import { buildSearchIndex, searchIndexMatches, type SearchIndexEntry } from "./fixtures";
import type { Route, SearchScope } from "./model";
import { Button, SectionHeader } from "./ui";

/**
 * Global Search — V1 concept: "Search my Intelligence library."
 *
 * Strict boundary: fixture / browser-state filtering only. No real index, no
 * database, no embeddings, no semantic retrieval, no external search, no AI
 * chat answers. Cross-language behavior is demonstrated through curated
 * fixture tags, not real multilingual matching.
 */

const scopeFilters: Array<{ id: SearchScope; label: string }> = [
  { id: "all", label: "全部" },
  { id: "following", label: "关注" },
  { id: "content", label: "内容" },
  { id: "intelligence", label: "洞察" },
  { id: "topic", label: "主题" },
  { id: "research", label: "调研" },
  { id: "evidence", label: "Evidence" },
];

const typeToScope: Record<SearchIndexEntry["type"], SearchScope> = {
  "关注": "following",
  "内容": "content",
  "洞察": "intelligence",
  "主题": "topic",
  "调研": "research",
  "Evidence": "evidence",
};

/** Compact search control rendered in the workspace topbar. */
export function SearchTrigger({ navigate }: { navigate: (route: Route) => void }) {
  return <button
    className="search-trigger"
    aria-label="搜索你的 Intelligence"
    onClick={() => navigate("search")}
  >
    <span className="search-trigger-icon" aria-hidden="true">⌕</span>
    <span className="search-trigger-placeholder">搜索你的 Intelligence...</span>
    <kbd className="search-trigger-hint">Demo</kbd>
  </button>;
}

export function SearchPage({ navigate, initialQuery = "" }: { navigate: (route: Route) => void; initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [scope, setScope] = useState<SearchScope>("all");
  const inputRef = useRef<HTMLInputElement>(null);
  const index = useMemo(() => buildSearchIndex(), []);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const results = useMemo(() => {
    const trimmed = query.trim();
    if (!trimmed) return [] as SearchIndexEntry[];
    return index.filter(entry => {
      if (scope !== "all" && typeToScope[entry.type] !== scope) return false;
      return searchIndexMatches(entry, trimmed);
    });
  }, [index, query, scope]);

  const counts = useMemo(() => {
    const trimmed = query.trim();
    if (!trimmed) return {} as Record<SearchScope, number>;
    const matched = index.filter(entry => searchIndexMatches(entry, trimmed));
    const next: Record<SearchScope, number> = { all: matched.length, following: 0, content: 0, intelligence: 0, topic: 0, research: 0, evidence: 0 };
    for (const entry of matched) next[typeToScope[entry.type]] += 1;
    return next;
  }, [index, query]);

  const openResult = (entry: SearchIndexEntry) => navigate(entry.route as Route);
  const clearFilters = () => setScope("all");
  const showEmpty = query.trim().length > 0 && results.length === 0;
  const showPrompt = !query.trim();

  return <>
    <SectionHeader
      eyebrow="Global Search · V1"
      title="搜索你的 Intelligence"
      description="在本地资料库中定位已经积累的关注、内容、Evidence、洞察、主题与调研。V1 只做定位，不做生成式回答。"
    />
    <section className="search-console" aria-label="全局搜索">
      <label className="search-field">
        <span className="search-field-label">搜索关键词</span>
        <input
          ref={inputRef}
          type="search"
          placeholder="搜索你的 Intelligence..."
          value={query}
          onChange={event => setQuery(event.target.value)}
        />
      </label>
      <div className="search-filters" role="group" aria-label="搜索范围筛选">
        {scopeFilters.map(filter => <button
          key={filter.id}
          aria-pressed={scope === filter.id}
          className={scope === filter.id ? "active" : ""}
          onClick={() => setScope(filter.id)}
        >
          {filter.label}
          {query.trim() && counts[filter.id] !== undefined && <small>{counts[filter.id]}</small>}
        </button>)}
      </div>
      <p className="search-scope-note" role="status">
        {query.trim()
          ? `找到 ${results.length} 条结果${scope !== "all" ? ` · 范围：${scopeFilters.find(item => item.id === scope)?.label}` : ""}`
          : "输入关键词开始搜索；Demo 只在本地 fixture 中匹配，不会访问网络或调用模型。"}
      </p>
    </section>

    {showPrompt && <section className="search-prompt">
      <p className="eyebrow">可以搜索的对象</p>
      <div className="search-prompt-grid">
        {[["关注", "频道、账号、本地文件夹"], ["内容", "视频、帖子与处理状态"], ["Evidence", "可追溯的原文摘录"], ["洞察", "跨来源的长期判断"], ["主题", "持续演进的知识认知"], ["调研", "某个时间点的研究快照"]].map(([title, copy]) => <article key={title}><strong>{title}</strong><span>{copy}</span></article>)}
      </div>
      <p className="search-example">试试：<button onClick={() => setQuery("Agent 商业化")}>Agent 商业化</button> · <button onClick={() => setQuery("任务执行界面")}>任务执行界面</button> · <button onClick={() => setQuery("outcome pricing")}>outcome pricing</button></p>
    </section>}

    {showEmpty && <section className="search-empty" role="status">
      <h2>没有找到匹配内容。</h2>
      <p>可以尝试：</p>
      <ul>
        <li><button onClick={() => { setQuery(""); inputRef.current?.focus(); }}>换一个关键词</button></li>
        {scope !== "all" && <li><button onClick={clearFilters}>清除筛选，回到「全部」</button></li>}
        <li>检查是否拼写完整，或改用更宽泛的词，例如「Agent」「定价」「任务执行界面」。</li>
      </ul>
      <p className="search-empty-boundary">V1 搜索只覆盖你的本地 Intelligence 资料库，不会跳转到互联网，也不会生成新的回答。</p>
    </section>}

    {!showEmpty && !showPrompt && <section className="search-results" aria-label="搜索结果">
      {results.map(entry => <article className="search-result" key={entry.id}>
        <div className="search-result-head">
          <span className={`search-type type-${typeToScope[entry.type]}`}>{entry.type}</span>
          {entry.crossLanguage && <span className="search-cross-language" title="来源包含其他语言的 Evidence">跨语言</span>}
          {entry.sourceLanguage && <span className="search-language">源语言 · {entry.sourceLanguage}</span>}
        </div>
        <button className="search-result-link" aria-label={`打开${entry.type}：${entry.title}`} onClick={() => openResult(entry)}>
          <h3>{entry.title}</h3>
          <p className="search-result-snippet">{entry.snippet}</p>
        </button>
        <footer className="search-result-context">
          <span>{entry.context}</span>
          <Button variant="quiet" aria-label={`打开${entry.type}结果：${entry.title}`} onClick={() => openResult(entry)}>打开</Button>
        </footer>
      </article>)}
    </section>}
  </>;
}
