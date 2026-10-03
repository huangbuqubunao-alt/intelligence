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
    RESEARCH_REVISION_NOT_FOUND: "This Research version is unavailable.",
    RESEARCH_INVALID_CURSOR: "This History page is unavailable. Reopen Research History.",
    RESEARCH_NOT_FOUND: "This Research item is unavailable.",
    RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE: "Source authority is unavailable. This packet cannot be verified. Inspect the selected Content before assembling again.",
    RESEARCH_CORRUPTED_RESULT: "This saved Research result failed integrity checks. It cannot be presented as verified.",
    RESEARCH_EXECUTION_FAILED: "Research could not be assembled. Try again after checking the local library.",
    RESEARCH_DIFF_INVALID_REQUEST: "Choose two valid Research versions to compare.",
    RESEARCH_DIFF_BASE_NOT_FOUND: "The base version is unavailable. Reopen Research History.",
    RESEARCH_DIFF_TARGET_NOT_FOUND: "The target version is unavailable. Reopen Research History.",
    RESEARCH_DIFF_WRONG_RESEARCH: "Only versions of the same Research item can be compared.",
    RESEARCH_DIFF_UNTRUSTED_REVISION: "A version failed authority checks. This comparison is unavailable.",
    RESEARCH_DIFF_INCOMPATIBLE_CONTRACT: "These versions use an incompatible Research contract.",
  } as Record<string, string>)[code ?? ""] ?? "Research could not be loaded. Try again.";
}

// User-facing revision identity is the existing immutable result identity.
export type ResearchHistoryPage = {
  revisions: { revision_id: string; assembled_at: string; question: string;
    output_language: "zh-CN" | "en"; scope_count: number; evidence_count: number;
    intelligence_count: number; status: "EVIDENCE_AVAILABLE" | "INSUFFICIENT_MATERIAL" }[];
  current_revision_id: string | null; current_available: boolean; unavailable_count: number;
  has_more: boolean; next_cursor: string | null; limit: number;
};

export type DiffGroup<T> = { added: T[]; removed: T[]; unchanged_count: number };
export type DiffContent = { id: string; content_id: string; title: string | null };
export type DiffEvidence = DiffContent & { evidence_id: string; excerpt: string; start_ms: number; end_ms: number; source_language: string; lineage_kind: string };
export type DiffInterpretation = DiffContent & {
  intelligence_id: string; revision_id: string; conclusion: string; claim_kind: string; state: string;
  citations: { evidence_id: string; stance: string | null }[];
};
export type DiffRevision = { revision_id: string; execution_number: number; assembled_at: string; scope: { content_id: string; title: string | null }[] };
export type ResearchDiffProjection = {
  contract: "research-diff-v1"; packet_contract: "research-lite-v1"; research_id: string;
  question: string; output_language: "zh-CN" | "en"; base: DiffRevision; target: DiffRevision;
  summary: { added: number; removed: number; changed: number }; no_material_changes: boolean;
  content: DiffGroup<DiffContent>; evidence: DiffGroup<DiffEvidence>; interpretations: DiffGroup<DiffInterpretation>;
  packet_changes: { id: string; field: "material_status" | "evidence_candidates" | "intelligence_candidates" | "retrieval_truncated" | "unresolved"; base: string | number | boolean | string[]; target: string | number | boolean | string[] }[];
  complete: true; content_limit_per_side: number; evidence_limit_per_side: number; interpretation_limit_per_side: number;
};
