-- TASK-016D: provider-aware, append-only Deep Analysis trusted-result audit
-- records.  Every cache candidate is independently integrity-verified on read.

CREATE TABLE deep_analysis_persisted_results (
    result_identity TEXT PRIMARY KEY CHECK (
        length(result_identity) = 64 AND result_identity NOT GLOB '*[^0-9a-f]*'
    ),
    cache_identity TEXT CHECK (
        cache_identity IS NULL
        OR (length(cache_identity) = 64 AND cache_identity NOT GLOB '*[^0-9a-f]*')
    ),
    cache_eligibility TEXT NOT NULL CHECK (
        cache_eligibility IN ('ELIGIBLE', 'INELIGIBLE_FLOATING_MODEL')
    ),
    a1_identity TEXT NOT NULL CHECK (length(a1_identity) = 64),
    a2_identity TEXT NOT NULL CHECK (length(a2_identity) = 64),
    a3_identity TEXT NOT NULL CHECK (length(a3_identity) = 64),
    validation_policy_identity TEXT NOT NULL CHECK (length(validation_policy_identity) = 64),
    validation_policy_json TEXT NOT NULL,
    provider_kind TEXT NOT NULL CHECK (length(trim(provider_kind)) > 0),
    provider_id TEXT NOT NULL CHECK (length(trim(provider_id)) > 0),
    adapter_identity TEXT NOT NULL CHECK (length(trim(adapter_identity)) > 0),
    adapter_version TEXT NOT NULL CHECK (length(trim(adapter_version)) > 0),
    endpoint_deployment_profile_identity TEXT NOT NULL CHECK (length(trim(endpoint_deployment_profile_identity)) > 0),
    model_id TEXT NOT NULL CHECK (length(trim(model_id)) > 0),
    model_identity_class TEXT NOT NULL CHECK (model_identity_class IN ('IMMUTABLE', 'VERSIONED', 'FLOATING')),
    model_resolved_revision TEXT,
    payload_scope TEXT NOT NULL CHECK (payload_scope IN ('SELECTED_EVIDENCE_ONLY', 'FULL_TRANSCRIPT')),
    scoring_request_hash TEXT NOT NULL CHECK (length(scoring_request_hash) = 64),
    scoring_success_provenance TEXT NOT NULL CHECK (scoring_success_provenance IN ('PRIMARY', 'REPAIR_H2C')),
    evidence_registry_identity TEXT NOT NULL CHECK (length(trim(evidence_registry_identity)) > 0),
    content_identity TEXT NOT NULL CHECK (length(content_identity) = 64),
    provider_envelope_identity TEXT NOT NULL CHECK (length(provider_envelope_identity) = 64),
    structured_payload_identity TEXT NOT NULL CHECK (length(structured_payload_identity) = 64),
    provenance_identity TEXT NOT NULL CHECK (length(provenance_identity) = 64),
    canonical_input_json TEXT NOT NULL,
    evidence_registry_json TEXT NOT NULL,
    authorized_payload_json TEXT NOT NULL,
    request_projection_json TEXT NOT NULL,
    execution_profile_json TEXT NOT NULL,
    payload_consent_json TEXT NOT NULL,
    context_budget_json TEXT NOT NULL,
    response_metadata_json TEXT NOT NULL,
    knowledge_content_json TEXT NOT NULL,
    fallback_attempts_json TEXT NOT NULL,
    fallback_policy_identity TEXT NOT NULL CHECK (length(fallback_policy_identity) = 64),
    timeout_profile_identity TEXT NOT NULL CHECK (length(trim(timeout_profile_identity)) > 0),
    response_envelope_bytes BLOB NOT NULL,
    structured_payload_kind TEXT NOT NULL CHECK (structured_payload_kind IN ('BYTES', 'JSON')),
    structured_payload_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    validated_at TEXT NOT NULL,
    CHECK (
        (cache_eligibility = 'ELIGIBLE' AND cache_identity IS NOT NULL)
        OR (cache_eligibility = 'INELIGIBLE_FLOATING_MODEL' AND cache_identity IS NULL)
    )
);

CREATE UNIQUE INDEX uq_deep_analysis_persisted_cache_identity
    ON deep_analysis_persisted_results(cache_identity)
    WHERE cache_identity IS NOT NULL;
