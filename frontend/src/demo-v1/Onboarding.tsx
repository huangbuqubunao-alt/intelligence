import { useState } from "react";
import type { AsyncState, Route } from "./model";
import { Button, StatusLine } from "./ui";

export function Onboarding({ onComplete }: { onComplete: (route: Route) => void }) {
  const [step, setStep] = useState(0);
  const [strategy, setStrategy] = useState("automatic");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceKind, setSourceKind] = useState("频道");
  const [sourceCheck, setSourceCheck] = useState<AsyncState>("idle");
  const [interests, setInterests] = useState(["AI / 技术", "产品"]);

  const testFollowing = () => {
    setSourceCheck("checking");
    window.setTimeout(() => setSourceCheck(sourceUrl.includes("youtube.com") ? "success" : "error"), 140);
  };
  const toggleInterest = (value: string) => setInterests(current => current.includes(value) ? current.filter(item => item !== value) : [...current, value]);
  const strategies = [
    ["automatic", "自动配置", "根据任务复杂度、成本和可用能力自动选择"],
    ["local", "优先本地", "尽量在本机处理，必要时使用云模型"],
    ["manual", "我自己选择模型", "稍后在高级设置中选择任务与模型"],
  ];

  return <main className="onboarding-shell">
    <div className="demo-ribbon">REVISION 3 · Clickable UX Demo · 所有连接、处理与存储均为模拟</div>
    <div className="onboarding-progress" aria-label={`设置进度 ${step + 1} / 5`}><span style={{ width: `${((step + 1) / 5) * 100}%` }} /></div>
    <section className="onboarding-card">
      {step === 0 && <>
        <p className="eyebrow">Intelligence</p>
        <h1 className="welcome-title">让你关注的信息，变成可追溯的洞察、主题与研究。</h1>
        <p className="welcome-copy">持续关注视频、帖子与本地内容，让不同来源的 Evidence 汇聚成长期理解。</p>
        <ol className="value-steps">
          <li><span>01</span><div><strong>关注</strong><p>选择频道、账号、内容或本地资料。</p></div></li>
          <li><span>02</span><div><strong>理解</strong><p>AI 提取可追溯的 Evidence 与跨来源洞察。</p></div></li>
          <li><span>03</span><div><strong>演进</strong><p>持续修正 Topic，并保留每次 Research 快照。</p></div></li>
        </ol>
        <Button onClick={() => setStep(1)}>开始设置</Button>
      </>}
      {step === 1 && <>
        <p className="step-count">1 / 4 · AI 服务</p><h1>你希望如何运行 AI？</h1>
        <p className="lede">不需要先理解模型。系统会把频繁的基础任务与高价值分析分开处理。</p>
        <fieldset className="strategy-options"><legend>模型策略</legend>{strategies.map(([id, label, copy]) => <label className={strategy === id ? "selected" : ""} key={id}><input aria-label={label} type="radio" name="onboarding-strategy" checked={strategy === id} onChange={() => setStrategy(id)} /><span><strong>{label}</strong><small>{copy}</small></span></label>)}</fieldset>
        <StatusLine title="本地模型不是必选项">本地模型在你的电脑上运行，可减少云端调用并提高隐私；你可以稍后再连接。</StatusLine>
        <div className="actions"><Button variant="quiet" onClick={() => setStep(0)}>返回</Button><Button onClick={() => setStep(2)}>继续添加关注</Button></div>
      </>}
      {step === 2 && <>
        <p className="step-count">2 / 4 · 第一个关注</p><h1>先关注一个 YouTube 频道</h1>
        <p className="lede">YouTube 是本 Demo 中最完整的 Provider 示例；不会访问真实平台。</p>
        <div className="segmented" aria-label="YouTube 对象类型">{["频道", "视频", "播放列表"].map(item => <button key={item} className={sourceKind === item ? "active" : ""} onClick={() => setSourceKind(item)}>{item}</button>)}</div>
        <label className="field"><span>YouTube URL</span><input aria-label="YouTube URL" value={sourceUrl} onChange={event => { setSourceUrl(event.target.value); setSourceCheck("idle"); }} placeholder="https://youtube.com/@aiexplained" /></label>
        <Button onClick={testFollowing} disabled={!sourceUrl || sourceCheck === "checking"}>{sourceCheck === "checking" ? "正在模拟检查…" : "测试关注"}</Button>
        {sourceCheck === "error" && <StatusLine tone="danger" title="没有识别到可用对象">请确认链接指向公开的 YouTube {sourceKind}，然后重试。</StatusLine>}
        {sourceCheck === "success" && <><div className="check-list"><p>找到频道：AI Explained</p><p>可以读取公开内容</p><p>字幕处理可用</p></div><Button onClick={() => setStep(3)}>继续设置偏好</Button></>}
      </>}
      {step === 3 && <>
        <p className="step-count">3 / 4 · 分析偏好</p><h1>什么内容值得 Intelligence 帮你留下？</h1>
        <fieldset className="preference-group"><legend>关注领域</legend><div className="check-options">{["AI / 技术", "产品", "商业机会", "行业趋势", "投资", "研究"].map(value => <label key={value}><input aria-label={value} type="checkbox" checked={interests.includes(value)} onChange={() => toggleInterest(value)} />{value}</label>)}</div></fieldset>
        <fieldset className="preference-group"><legend>分析方式</legend><div className="radio-options"><label><input type="radio" name="analysis" defaultChecked />证据优先</label><label><input type="radio" name="analysis" />简洁总结</label><label><input type="radio" name="analysis" />深度研究</label></div></fieldset>
        <Button onClick={() => setStep(4)}>保存偏好并继续</Button>
      </>}
      {step === 4 && <>
        <p className="step-count">Ready</p><h1>Intelligence 已经准备好了。</h1>
        <div className="ready-list"><p>模型策略：{strategy === "automatic" ? "自动配置" : strategy === "local" ? "优先本地" : "稍后自行选择"}</p><p>第一个关注可用（Demo）</p><p>分析偏好已保存在本页状态</p><p>没有连接真实模型或写入本地数据</p></div>
        <div className="actions"><Button onClick={() => onComplete("following-ai-explained")}>查看第一个关注</Button><Button variant="secondary" onClick={() => onComplete("home")}>进入首页</Button></div>
      </>}
    </section>
  </main>;
}
