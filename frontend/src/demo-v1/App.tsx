import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Onboarding } from "./Onboarding";
import { Logo } from "./Logo";
import { LanguageProvider } from "./LanguageContext";
import { SearchPage, SearchTrigger } from "./Search";
import type { Experience, ResearchContext, Route, SettingsSection } from "./model";
import { AddFollowingPage, ContentDetailPage, DemoStateDrawer, FollowingDetailPage, FollowingPage, HomePage, IntelligenceDetailPage, IntelligenceListPage, ResearchPage, SettingsPage, TopicDetailPage, TopicListPage } from "./WorkspacePages";

const navItems: Array<{ route: Route; label: string }> = [
  { route: "home", label: "首页" },
  { route: "following", label: "关注" },
  { route: "intelligence", label: "洞察" },
  { route: "topics", label: "主题" },
  { route: "research", label: "调研" },
  { route: "settings", label: "设置" },
];

const routeLabels: Partial<Record<Route, string>> = {
  home: "首页",
  following: "关注",
  "following-add": "添加关注",
  "following-ai-explained": "关注详情",
  "following-bilibili-creator": "关注详情",
  "following-agentbuilder": "关注详情",
  "following-local-conference": "关注详情",
  "following-practical-ai": "关注详情",
  intelligence: "洞察",
  "intelligence-detail": "洞察详情",
  "intelligence-detail-pricing": "洞察详情",
  topics: "主题",
  "topic-detail": "主题详情",
  "search": "搜索",
  settings: "设置",
};

function activeRoute(route: Route): Route {
  if (route.startsWith("following") || route.startsWith("content")) return "following";
  if (route.startsWith("intelligence")) return "intelligence";
  if (route.startsWith("topic")) return "topics";
  if (route.startsWith("research")) return "research";
  return route;
}

function WorkspaceShell({ route, navigate, children, drawerOpen, setDrawerOpen }: { route: Route; navigate: (route: Route) => void; children: ReactNode; drawerOpen: boolean; setDrawerOpen: (open: boolean) => void }) {
  return <div className="app-shell">
    <aside className="sidebar">
      <button className="brand" onClick={() => navigate("home")}><span className="brand-row"><Logo className="brand-logo" /><span className="brand-wordmark">Intelligence</span></span><span className="brand-tagline">Evidence-led knowledge workspace</span></button>
      <nav aria-label="主导航">{navItems.map(item => <button key={item.route} className={activeRoute(route) === item.route ? "active" : ""} onClick={() => navigate(item.route)}>{item.label}</button>)}</nav>
      <div className="sidebar-foot"><button onClick={() => setDrawerOpen(true)}>演示异常状态</button><p>V1 Pre-freeze · Clickable Demo</p><small>无真实连接、处理或数据写入</small></div>
    </aside>
    <div className="workspace">
      <header className="topbar">
        <span className="topbar-title">{routeLabels[route] ?? (route.startsWith("following-") ? "关注详情" : "内容详情")}</span>
        <div className="topbar-actions">
          <SearchTrigger navigate={navigate} />
          <span className="system-ok">运行正常</span>
          <span className="demo-label">DEMO</span>
        </div>
      </header>
      <div className="page">{children}</div>
    </div>
    {drawerOpen && <DemoStateDrawer onClose={() => setDrawerOpen(false)} navigate={navigate} />}
  </div>;
}

export function DemoApp({ initialExperience = "onboarding" }: { initialExperience?: Experience }) {
  const [experience, setExperience] = useState<Experience>(initialExperience);
  const hashRoute = useMemo(() => window.location.hash.replace("#", "") as Route, []);
  const [route, setRoute] = useState<Route>(hashRoute && (routeLabels[hashRoute] || hashRoute.startsWith("content-") || hashRoute.startsWith("following-")) ? hashRoute : "home");
  const [settingsSection, setSettingsSection] = useState<SettingsSection>("ai");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [researchContext, setResearchContext] = useState<ResearchContext>({ kind: "Topic", label: "AI Agent 商业化" });

  const navigate = (next: Route) => {
    setRoute(next);
    window.history.replaceState({}, "", `#${next}`);
    if (!window.navigator.userAgent.includes("jsdom")) window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const openResearch = (context: ResearchContext) => { setResearchContext(context); navigate("research"); };
  const completeOnboarding = (next: Route) => { setExperience("workspace"); navigate(next); };

  useEffect(() => { document.title = "Intelligence · V1 Pre-freeze UX Demo"; }, []);
  if (experience === "onboarding") return <Onboarding onComplete={completeOnboarding} />;

  let content: ReactNode;
  if (route === "home") content = <HomePage navigate={navigate} />;
  else if (route === "following") content = <FollowingPage navigate={navigate} />;
  else if (route === "following-add") content = <AddFollowingPage navigate={navigate} />;
  else if (route.startsWith("following-")) content = <FollowingDetailPage followingId={route} navigate={navigate} openResearch={openResearch} />;
  else if (route.startsWith("content-")) content = <ContentDetailPage key={route} contentId={route} navigate={navigate} openResearch={openResearch} />;
  else if (route === "intelligence") content = <IntelligenceListPage navigate={navigate} />;
  else if (route === "intelligence-detail" || route === "intelligence-detail-pricing") content = <IntelligenceDetailPage intelligenceId={route === "intelligence-detail-pricing" ? "intel-outcome-pricing" : "intel-task-interface"} navigate={navigate} openResearch={openResearch} />;
  else if (route === "topics") content = <TopicListPage navigate={navigate} />;
  else if (route === "topic-detail") content = <TopicDetailPage navigate={navigate} openResearch={openResearch} />;
  else if (route === "search") content = <SearchPage navigate={navigate} />;
  else if (route === "research" || route === "research-result") content = <ResearchPage route={route} navigate={navigate} context={researchContext} />;
  else content = <SettingsPage section={settingsSection} setSection={setSettingsSection} />;

  return <LanguageProvider>
    <WorkspaceShell route={route} navigate={navigate} drawerOpen={drawerOpen} setDrawerOpen={setDrawerOpen}>{content}</WorkspaceShell>
  </LanguageProvider>;
}
