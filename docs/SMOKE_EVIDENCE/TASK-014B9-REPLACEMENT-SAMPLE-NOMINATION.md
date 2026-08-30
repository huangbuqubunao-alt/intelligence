# TASK-014B9 replacement sample nomination

- Nomination authority: Product Owner / Tech Lead nomination-only authorization, 2026-08-31.
- Contract baseline: ADR-022 at `7f0915944a64879785e53a1993ddf0e6897e3350`; prior selection-disposition
  evidence is `d8a7f2aee2b8683e6a75bdea0b39243b26fe0b74`.
- Historical B9 sample: `eIho2S0ZahI` is `RETIRED / NOT RENOMINATED`; its `CONTENT_UNAVAILABLE` and
  `INVALID_RESPONSE` evidence remains preserved and consumed.
- Legal discovery budget: one public metadata-only operation under ADR-022 D-03 (the task-level maximum of
  three does not override that stricter committed limit). Actual rounds: `1`.
- Discovery boundary: one flat public YouTube search result from the official TED source class. It collected only
  listing metadata needed for identity and eligibility. It did not invoke the project smoke entrypoint, enumerate
  a subtitle directory, request a subtitle body, download media, authenticate, or validate the B9 contract.
- Candidates considered: retired B9 ID `eIho2S0ZahI` (rejected); prior B-1 IDs `--khbXchTeE` and `JTxsNm9IdYU`
  (rejected: preserved prior directory failures); recovery-drill fixture `dQw4w9WgXcQ` (rejected: not a B9
  public-sample candidate); `5MWT_doo68k` (selected).
- Selection rule: select the first single result from the sole legal discovery operation if it is a new,
  deterministically identifiable public TED-source ID with no known credential gate, retirement, or prior
  directory failure. No qualification outcome influenced selection.
- Replacement sample: `5MWT_doo68k`.
- Sample status: `PRE-FROZEN / ELIGIBLE FOR QUALIFICATION` — public listing metadata identifies an official TED
  source, stable ID, non-private listing, no account-specific requirement, and a completed (not currently live)
  item. Subtitle-directory response validity, subtitle availability, track kind, language, and all B9 pass
  conditions are `UNKNOWN UNTIL QUALIFICATION`.
- Completed-live listing status is not a disqualifier in ADR-022 and was not used to infer subtitle availability,
  directory validity, or a B9 qualification outcome.
- Nomination accounting: subtitle body reads `0`; project enumerate operations `0`; project read operations `0`;
  B9 qualification calls `0`; semantic retries `0`; substitutions `0`; fallback `NO`.
- Result: `PASS` for nomination only. TASK-014B9 remains `BLOCKED / READY FOR FINAL ONE-SHOT QUALIFICATION`;
  it is not qualified and this evidence is not release approval.
