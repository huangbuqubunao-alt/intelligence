# LOCAL TXT/MD Intelligence contract

This isolated implementation uses the accepted LOCAL source snapshot, canonical
text, extractive Summary pointer and source Evidence resolver. A manual command
requires the actual LOCAL_LIBRARY/DISCOVER_ONLY source and current verified
Summary; it never enables automatic library processing. LOCAL Cloud routes stay
unavailable before credentials, payload construction or invocation.

`local-text-distillation-v1` references contain exact Evidence ID, TEXT_RANGE,
Unicode code-point half-open offsets, derived one-based lines, source/canonical/
excerpt hashes, and explicit NULL start/end times. Mixed or missing fields,
fabricated ranges/hashes, duplicate JSON keys, foreign Evidence and incomplete
NO_NEW coverage are rejected. The old YouTube v5/timed wire, card hashes and
timed card DTO remain unchanged.

Schema 38 is reused without migration. An immutable
`distillation:local-text-v1:<input hash>:<context hash>:<identity hash>` records
the independent wire/profile, sealed input and exact source/Summary context.
The identity hash binds the persisted command fields and exact profile hash;
the profile binds prompt, schema, model/digest and generation settings. The card
hash includes this input/context/profile binding plus the exact cited ranges.
The reader requires one checkpoint for the revision, matching successful ledger,
same Content/source, valid current resolver ranges and the exact card hash. It
does not infer versions from NULL timestamps or try alternative hashes.

At admission the source, canonical bytes, current Summary and complete coverage
are checked again in the transaction against the sealed context. Historical
cards preserve the admitted context commitment, while validating current source
authority; a legal later Summary refresh does not rewrite their hashes. The
specifically approved `read_current` hook applies the same card validator to
LOCAL text cards before Save/list/Topic consumes the verified revision. General,
YouTube and timed reads retain their existing behavior.

The existing Evidence display shows real lines (or honest unavailable text).
Internal navigation serializes only Content ID and Evidence ID. After refresh,
the current Content Evidence DTO must contain that same Evidence before focus
can occur; no URL parameter supplies offsets or timestamps. The view remains
the existing workspace layout documented in `frontend/src/workspace/DESIGN.md`.

`scripts/prepare_readiness_local_text.py` prepares the independent research
profile and optional exact request projection only. It has no model execution
entry point, runtime factory registration or qualification receipt. The pinned
9B model and original qualification remain failed; production qualification is
false, execution authority NONE, and real calls zero. Future LOCAL8 and genuine
ordinary Intelligence/save/Topic acceptance remain blocked by that prerequisite,
exact input/code freeze, independent pre-output review and a specific start
instruction. All positive tests in this task are explicitly offline fixtures.

User-facing reading steps: import TXT/MD, open Content and its original Evidence;
read the displayed line ranges; use Open Content from an Intelligence Evidence
reference to return to the same internal range. Refresh preserves that reference
identity and revalidates it. Cloud remains unavailable for local documents. A
WAITING_MODEL result reports the actual missing qualified model and can be
cancelled through the existing safe action; it does not manufacture a result.
