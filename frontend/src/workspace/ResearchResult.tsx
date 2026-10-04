import { OpenResearchSource, ResearchResult as Result } from "./ResearchTypes";
import { useUiLanguage } from "./uiLanguage";

const clock = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}`;
const claimCopy: Record<string, string> = {
  EVIDENCE_BACKED_STATEMENT: "Evidence-backed statement", OPINION: "Attributed opinion",
  SYSTEM_INFERENCE: "System inference", PREDICTION: "Prediction",
  RUMOR: "Unverified rumor", FACT: "Recorded fact classification",
};
const stateCopy: Record<string, string> = {
  NEW: "New", PENDING_CONFIRMATION: "Pending confirmation", CONFIRMED: "Confirmed",
  DISPUTED: "Disputed", UPDATED: "Updated",
};
const stanceCopy: Record<string, string> = {
  supporting: "Supporting", contradicting: "Contradicting", conditional: "Conditional",
};

export function ResearchResult({ result, onOpen }: { result: Result; onOpen: OpenResearchSource }) {
  const { t, language } = useUiLanguage();
  const packet = result.packet;
  const title = (id: string) => packet.scope.find(item => item.content_id === id)?.title || t("Untitled Content");
  return <div className="research-result" aria-label={t("Research result")}>
    <section className="panel">
      <h2 className="research-question">{packet.question}</h2>
      <p className="reading-meta">{t("Library packet assembled")} · {new Date(packet.assembled_at).toLocaleString(language)} · {t("Output language")}: {packet.output_language === "en" ? "English" : t("Simplified Chinese")}</p>
      <p>{t("Original source material and recorded interpretations are verified below. No Research synthesis model ran; this packet does not establish a new conclusion.")}</p>
      <h3>{t("Selected library scope")}</h3>
      <ul className="research-scope-list">{packet.scope.map(item => <li key={item.content_id}>
        <button className="research-source-link" onClick={() => onOpen("content", item.content_id)}>{item.title || t("Untitled Content")}</button>
      </li>)}</ul>
    </section>
    <section className="panel">
      <h2>{t("What you can inspect")}</h2>
      {packet.material_status === "INSUFFICIENT_MATERIAL"
        ? <p className="empty-state" role="status">{t("No matching authoritative Evidence was found in this scope. Refine the question, choose more Content, or add material to your library.")}</p>
        : <p>{language === "zh-CN" ? `已收集 ${packet.evidence.length} 条原始证据和 ${packet.intelligence.length} 条已有洞察解释。` : `${packet.evidence.length} original Evidence references and ${packet.intelligence.length} existing Intelligence interpretations assembled.`}</p>}
      {packet.intelligence.length > 0 && <>
        <h3>{t("Recorded Intelligence interpretations")}</h3>
        <p className="hint">{t("These are existing interpretations with their recorded validation state. Opening Intelligence shows its current state.")}</p>
        {packet.intelligence.map(finding => <article className="research-finding" key={finding.revision_id}>
          <p className="reading-meta">{t(claimCopy[finding.claim_kind] || "Recorded interpretation")} · {t("Recorded state")}: {t(stateCopy[finding.state] || "Validation state unavailable")}</p>
          <p>{finding.conclusion}</p>
          <p className="hint">{title(finding.content_id)}</p>
          <div className="button-row">
            <button className="button button-secondary" onClick={() => onOpen("intelligence", finding.intelligence_id)}>{t("Open Intelligence")}</button>
            {finding.evidence_ids.map((id, index) => <a className="evidence-source-link" key={id} href={`#research-evidence-${encodeURIComponent(id)}`} onClick={event => {
              event.preventDefault(); document.getElementById(`research-evidence-${id}`)?.scrollIntoView({ block: "center" });
            }}>{t("Evidence")} {packet.evidence.findIndex(e => e.evidence_id === id) + 1} · {t(stanceCopy[finding.stances[index] || ""] || "Relation not determined")}</a>)}
          </div>
        </article>)}
      </>}
      {packet.evidence.length > 0 && <>
        <h3>{t("Original Evidence by Content")}</h3>
        {packet.scope.filter(item => packet.evidence.some(ref => ref.content_id === item.content_id)).map(item => <div className="research-source-group" key={item.content_id}>
          <h4>{item.title || t("Untitled Content")}</h4>
          {packet.evidence.filter(ref => ref.content_id === item.content_id).map(ref => <article className="evidence-item" id={`research-evidence-${ref.evidence_id}`} key={ref.evidence_id}>
            <p className="reading-meta">{t("Evidence")} {packet.evidence.indexOf(ref) + 1} · {ref.locator_type === "TEXT_RANGE" ? `${t("Lines")} ${ref.start_line}–${ref.end_line}` : ref.start_ms != null && ref.end_ms != null ? `${clock(ref.start_ms)}–${clock(ref.end_ms)}` : t("Position unavailable")} · {ref.provider === "LOCAL" ? t("Local") : ref.provider === "BILIBILI" ? t("Bilibili") : "YouTube"} · {t("Source language")}: {ref.source_language}</p>
            <blockquote>{ref.excerpt}</blockquote>
            <p className="hint">{t(ref.locator_type === "TEXT_RANGE" ? "Original source text" : ref.lineage_kind === "EXTRACTION" ? "Extracted evidence" : "Original transcript")}</p>
            <button className="button button-secondary" onClick={() => onOpen("content", ref.content_id, ref.evidence_id)}>{t("Open Content and Evidence")}</button>
          </article>)}
        </div>)}
      </>}
    </section>
    <section className="panel">
      <h2>{t("Unresolved points")}</h2>
      <ul>
        <li>{t("The research question remains open for your judgment; no model-authored answer is available.")}</li>
        <li>{t("Retrieval matches words in the question. It may miss differently phrased relevant material; matching is not proof of relevance or truth.")}</li>
        {packet.retrieval_truncated && <li>{t("This packet is bounded and is not exhaustive. Narrow the scope or refine the question to inspect more material.")}</li>}
      </ul>
      <p className="hint">{language === "zh-CN" ? `检索范围内有 ${packet.evidence_candidates} 条词语匹配证据候选和 ${packet.intelligence_candidates} 条洞察候选；证据包最多包含 24 条证据和 6 条洞察。` : `${packet.evidence_candidates} word-matched Evidence candidates and ${packet.intelligence_candidates} Intelligence candidates in scope; the packet contains at most 24 Evidence references and 6 interpretations.`}</p>
    </section>
  </div>;
}
