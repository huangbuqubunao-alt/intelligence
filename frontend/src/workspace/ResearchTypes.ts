export type ResearchEvidence = {
  evidence_id: string; content_id: string; artifact_id: string; excerpt: string;
  start_ms: number; end_ms: number; source_language: string;
  lineage_kind: string; role: string; created_at: string;
};
export type ResearchPacket = {
  research_id: string; question: string; output_language: "zh-CN" | "en";
  assembled_at: string; scope: { content_id: string; title: string | null }[];
  material_status: "EVIDENCE_AVAILABLE" | "INSUFFICIENT_MATERIAL";
  evidence: ResearchEvidence[];
  intelligence: {
    intelligence_id: string; revision_id: string; content_id: string;
    conclusion: string; claim_kind: string; state: string;
    evidence_ids: string[]; stances: (string | null)[];
  }[];
  evidence_candidates: number; intelligence_candidates: number;
  retrieval_truncated: boolean;
};
export type ResearchResult = { result_identity: string; provenance_status: "VERIFIED"; packet: ResearchPacket };
export type ResearchItem = {
  research_id: string; question?: string; scope_count?: number;
  assembled_at?: string; output_language?: string; status: string;
};
export type ResearchListing = { research: ResearchItem[]; total: number; offset: number; limit: number };
export type ScopeOptions = { content: { content_id: string; title: string | null; channel_name: string }[]; total: number; offset: number; limit: number };
export type OpenResearchSource = (kind: "content" | "intelligence", id: string, evidenceId?: string) => void;

export function researchErrorCopy(code?: string) {
  return ({
    RESEARCH_INVALID_QUESTION: "Enter a question between 1 and 2,000 characters.",
    RESEARCH_EMPTY_SCOPE: "Select at least one Content item.",
    RESEARCH_INVALID_SCOPE: "Select up to 20 existing Content items.",
    RESEARCH_SCOPE_NOT_FOUND: "Selected Content no longer exists. Choose the scope again.",
    RESEARCH_NOT_FOUND: "This Research item is unavailable.",
    RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE: "Source authority is unavailable. This packet cannot be verified. Inspect the selected Content before assembling again.",
    RESEARCH_CORRUPTED_RESULT: "This saved Research result failed integrity checks. It cannot be presented as verified.",
    RESEARCH_EXECUTION_FAILED: "Research could not be assembled. Try again after checking the local library.",
  } as Record<string, string>)[code ?? ""] ?? "Research could not be loaded. Try again.";
}
