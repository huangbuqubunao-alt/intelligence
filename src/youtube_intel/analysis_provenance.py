"""The one Analysis provider-call provenance contract.

Both trusted consumers of a persisted Summary artifact validate its provider-call
ledger entry through this module:

* :meth:`RuntimeOperations._validate_analysis_provenance` in
  ``youtube_intel.runtime``, which reuses a persisted Summary, and
* ``youtube_intel.reporting``'s trusted Weekly Report artifact read.

Keeping the field set here is what stops the two provenance definitions from
drifting apart.  A Summary artifact may only be trusted when the ledger entry
named by its artifact key is a *successful Analysis call* with matching
provider, model, prompt identity and schema identity -- not merely any
successful call, and not a scoring or other operation that happens to share a
provider and model.

This module owns no Summary semantics.  Candidate-local Summary eligibility
(legacy prompt identity, durable Evidence citations) stays in
``youtube_intel.summary_evidence_authority``; this module only decides whether a
ledger row legitimately claims to be an Analysis dispatch.
"""

from __future__ import annotations

from typing import Any, Final

from youtube_intel.state import ProviderCallStatus

#: The persisted Summary wire contract the Analysis operation dispatches against.
ANALYSIS_RESULT_SCHEMA_VERSION: Final = "analysis-result-v1"

#: Provider -> the only ledger operation that may legitimately have produced its
#: Analysis artifact.  Mirrors the runtime's own provider-derived expectation so
#: a local-scoring or cloud-scoring call can never be accepted as Analysis.
ANALYSIS_OPERATION_BY_PROVIDER: Final = {
    "ollama": "local-analysis",
    "openai": "cloud-analysis",
}

#: Provider/model identities the Analysis operation may legitimately use.
ANALYSIS_PROVIDER_SET: Final = frozenset(ANALYSIS_OPERATION_BY_PROVIDER)


class AnalysisProviderCallProvenanceError(ValueError):
    """The ledger entry is not a legitimate Analysis dispatch for this artifact."""


def analysis_operation_for(provider: str) -> str:
    """Return the only Analysis ledger operation permitted for ``provider``."""

    try:
        return ANALYSIS_OPERATION_BY_PROVIDER[provider]
    except KeyError:
        raise AnalysisProviderCallProvenanceError(
            "analysis artifact provider is not a known Analysis provider"
        ) from None


def require_analysis_provider_call(
    call: Any, *, request_hash: str, provider: str, model: str
) -> None:
    """Ledger-only: prove this row really is a successful Analysis dispatch.

    Every predicate here reads the ledger row and the artifact row identity
    only.  It never needs the Summary payload, so a malformed or unparseable
    payload can never mask a non-Analysis or mismatched ledger entry.

    Prompt identity is deliberately *not* asserted here.  Runtime decides legacy
    eligibility from the payload before it ever inspects the ledger, so a
    readable historical Summary is stale rather than forged.  The binding of
    prompt identity to this exact ledger row is therefore a payload-level
    concern, enforced by :func:`require_analysis_call_matches_payload`.
    """

    if provider not in ANALYSIS_PROVIDER_SET or not isinstance(model, str) or not model.strip():
        raise AnalysisProviderCallProvenanceError(
            "analysis artifact identity is not a known Analysis dispatch"
        )
    if call is None:
        raise AnalysisProviderCallProvenanceError("analysis provider call is missing")
    if call.request_hash != request_hash:
        raise AnalysisProviderCallProvenanceError("analysis provider call identity differs")
    if call.status is not ProviderCallStatus.SUCCEEDED:
        raise AnalysisProviderCallProvenanceError("analysis provider call did not succeed")
    if call.operation != analysis_operation_for(provider):
        # This is the non-Analysis binding: a scoring, or any other operation,
        # can never stand in for an Analysis call.
        raise AnalysisProviderCallProvenanceError(
            f"provider call is not an Analysis operation: {call.operation!r}"
        )
    if call.provider != provider:
        raise AnalysisProviderCallProvenanceError("analysis provider call provider differs")
    if call.model != model:
        raise AnalysisProviderCallProvenanceError("analysis provider call model differs")
    if call.schema_version != ANALYSIS_RESULT_SCHEMA_VERSION:
        raise AnalysisProviderCallProvenanceError(
            "analysis provider call schema identity is not the Analysis contract"
        )
    if not call.response_artifact_id:
        raise AnalysisProviderCallProvenanceError(
            "analysis provider call has no response artifact"
        )


def require_analysis_call_matches_payload(
    call: Any,
    *,
    request_hash: str,
    provider: str,
    model: str,
    prompt_version: str,
    schema_version: str,
) -> None:
    """Cross-check a decoded Summary payload against its ledger entry."""

    if (
        call.request_hash != request_hash
        or call.provider != provider
        or call.model != model
        or call.prompt_version != prompt_version
        or call.schema_version != schema_version
    ):
        raise AnalysisProviderCallProvenanceError(
            "analysis payload does not match its provider call provenance"
        )
