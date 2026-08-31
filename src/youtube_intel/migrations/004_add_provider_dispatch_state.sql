-- A local receipt cannot prove whether a cloud request was externally executed.
-- Existing PENDING calls predate this protocol and are conservatively marked
-- AMBIGUOUS so migration never authorizes their automatic redispatch.

CREATE TABLE provider_dispatch_states (
    request_hash TEXT PRIMARY KEY REFERENCES provider_calls(request_hash) ON DELETE RESTRICT
        CHECK (length(request_hash) = 64 AND request_hash NOT GLOB '*[^0-9a-f]*'),
    status TEXT NOT NULL CHECK (
        status IN (
            'NOT_DISPATCHED',
            'DISPATCH_INTENT_DURABLE',
            'DISPATCHED_RESULT_UNKNOWN',
            'SUCCESS_DURABLY_RECORDED',
            'FAILED_KNOWN',
            'AMBIGUOUS'
        )
    ),
    updated_at TEXT NOT NULL
);

INSERT INTO provider_dispatch_states (request_hash, status, updated_at)
SELECT
    request_hash,
    CASE status
        WHEN 'SUCCEEDED' THEN 'SUCCESS_DURABLY_RECORDED'
        WHEN 'PENDING' THEN 'AMBIGUOUS'
        ELSE 'FAILED_KNOWN'
    END,
    updated_at
FROM provider_calls;
