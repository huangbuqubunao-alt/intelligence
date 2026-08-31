# `o200k_base.tiktoken` File-Level Redistribution Evidence — 2026-08-31

## Scope and conclusion

This is an evidence record, not legal advice and not a distribution approval.
It assesses only the committed resource used by ADR-008. It neither changes
ADR-008 nor permits a network fallback.

**Classification: C — RIGHTSHOLDER DISTRIBUTED BUT DOWNSTREAM GRANT
AMBIGUOUS.** OpenAI publicly hosts the exact file and its official `tiktoken`
code loads it, but the reviewed authoritative material does not expressly grant
downstream redistribution of this separately hosted data file or identify its
file-level NOTICE obligation. ADR-028 consequently excludes the Blob from the
current project source/wheel/sdist artifact; it does not claim a downstream
license or change this classification.

## Exact file identity

| Field | Evidence |
| --- | --- |
| Historical repository / packaged path | Before ADR-028: `src/youtube_intel/resources/o200k_base.tiktoken` / `youtube_intel/resources/o200k_base.tiktoken` |
| Current project artifact path | None. The runtime verifies an explicitly user/admin-provisioned file at `storage.data_dir/tokenizers/o200k_base.tiktoken`; this is not a project-distributed path. |
| Size | 3,613,922 bytes |
| Local SHA-256 | `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d` |
| Canonical URL | `https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken` |
| Authoritative expected SHA-256 | The same value in [`openai_public.py` at tiktoken 0.13.0](https://github.com/openai/tiktoken/blob/0.13.0/tiktoken_ext/openai_public.py#L95-L100) |
| Project acquisition record | ADR-008 A-16 and `d95745f`: one authenticated-free GET, hash verification, then commit |

The historical local hash matched the fixed upstream value. Under ADR-028,
`analysis.load_provisioned_o200k_encoding()` only admits the fixed local
provisioning path when it has that expected hash; missing, malformed, changed,
or unsafe data fails locally before any provider, credential, or network action.

## Authoritative evidence reviewed

| Tier | Source and result | Rights conclusion |
| --- | --- | --- |
| 1 | [`tiktoken` 0.13.0 source](https://github.com/openai/tiktoken/blob/0.13.0/tiktoken_ext/openai_public.py#L95-L100) maps `o200k_base` to the canonical Blob and fixed hash. | Establishes identity and OpenAI-hosted provenance, not a downstream redistribution grant. |
| 1 | [`tiktoken` MIT license](https://github.com/openai/tiktoken/blob/0.13.0/LICENSE) grants rights to the repository's “Software” and associated documentation. | The current repository tree and its `MANIFEST.in` contain no `.tiktoken` data file, so this source does not expressly attach that grant to the separately hosted Blob. |
| 1 | Official Blob `HEAD` response: 200, `application/octet-stream`, 3,613,922-byte content length, Azure ETag and MD5; `?comp=metadata` returned no `x-ms-meta-*` license, copyright, or NOTICE field. | Public read access and origin are not redistribution permission. |
| 2 | `tiktoken==0.13.0` source distribution contains its `LICENSE` but zero `.tiktoken` data entries; its `MANIFEST.in` lists source/test assets only. | Supporting evidence that the package license boundary does not include the exact data file. |
| 1 | Official OpenAI Cookbook/help documentation and `openai/tiktoken` model mappings describe use of `o200k_base`; repository issues/PRs and collaborator comments reviewed discuss release, caching, and tokenizer behavior. | No reviewed official documentation or maintainer statement grants mirroring, vendoring, packaging, or downstream redistribution of `o200k_base.tiktoken`. |
| 2 | OpenAI's public Blob distribution and package runtime download behavior. | Strong provenance and rightsholder distribution, but insufficient by itself for downstream rights. |

The search intentionally does **not** rely on downstream SBOMs, package forks,
or copied MIT notices. No third-party source was used to close this gate.

### Official search record

- The [official OpenAI Cookbook token-counting page](https://developers.openai.com/cookbook/examples/how_to_count_tokens_with_tiktoken)
  identifies `o200k_base` as an encoding, but supplies no data-file license or
  redistribution term.
- Official `openai/tiktoken` searches for `redistribut` and for `license`
  together with `o200k` returned no source result. The relevant issue/PR corpus
  was searched for `license`, `redistribution`, `mirror`, `vendored`, `cache`,
  and `o200k`. The collaborator comments in
  [#295](https://github.com/openai/tiktoken/issues/295),
  [#334](https://github.com/openai/tiktoken/issues/334), and
  [#368](https://github.com/openai/tiktoken/issues/368) concern release,
  functionality, or tokenizer quality—not downstream data-file rights.
- This is a bounded negative result, not proof that no rightsholder statement
  exists anywhere. A future direct OpenAI/rightsholder license confirmation can
  supersede this disposition.

## License and NOTICE determination

- The `tiktoken` repository license is MIT. Its generic copyright/license text
  is authoritative for code and associated documentation that are within its
  scope, but no authoritative reviewed statement connects the external Blob data
  file to that scope.
- The exact file is absent from the official repository tree and from the 0.13.0
  source distribution. The official package fetches it at runtime instead.
- No explicit file-level redistribution grant, copyright-holder attribution,
  or required NOTICE text was found in the Blob headers/metadata, source
  distribution, official documentation, or relevant official issue/PR
  discussions.

Accordingly, downstream redistribution is **not established** and file-specific
NOTICE obligations are **unresolved**. Adding an attribution or the repository
MIT text would not supply missing permission.

## ADR-008-compatible BPE artifact strategy — decision history

The table below was the bounded decision input after direct rightsholder
confirmation was not established.

| Option | ADR-008 / offline / fail-closed effect | Packaging, security, privacy, and licensing effect | Migration and test impact |
| --- | --- | --- | --- |
| 1. Operator provisions a local file before first run | Replace the fixed package resource with an explicit preflight path; validate the same SHA-256 and fail closed when absent/invalid. No application network access. | Removes the BPE data from wheel/sdist. The operator remains responsible for obtaining a lawful copy; no silent download or artifact redistribution occurs. | New configuration/path-safety contract, install instructions, package-exclusion test, hash/missing/tamper tests, and upgrade guidance. |
| 2. Explicit setup/installer provisioning | Could preserve runtime no-network behavior only if acquisition is a separately consented, bounded setup action. | Does not solve rights without a terms decision; increases supply-chain and user-consent surface. | Requires a new setup protocol, integrity/timeout/error policy, offline setup behavior, and tests. |
| 3. Clearly redistributable tokenizer data or implementation | Requires a fresh model-to-tokenizer compatibility decision and deterministic-token-count proof. | Could remove the ambiguous asset, but replacement licensing and packaging must be independently verified. | Broad compatibility, budget-boundary, regression, and migration work. |
| 4. Amend ADR-008 for a formal provisioning flow | May preserve no-silent-network-at-runtime semantics, but changes the accepted architecture. | Requires explicit PO/TL security, privacy, and licensing approval. | ADR revision plus implementation and end-to-end validation. |

**Selected and implemented:** Option 1, by the PO/TL-authorized ADR-028. It
preserves deterministic local tokenization, the exact hash check, offline
operation after provisioning, and fail-closed semantics while removing the
ambiguous file from shipped artifacts. It does not acquire, mirror, or license
the file for the operator.

## ADR-028 implementation disposition

- The project no longer vendors, mirrors, proxies, embeds, re-hosts, or copies
  this Blob into distributable source, wheel, or sdist artifacts.
- A user or administrator must explicitly and lawfully provision the exact file
  before normal cloud analysis. Runtime makes no network request, accepts no
  caller-supplied expected hash, and has no alternate tokenizer fallback.
- Archive inspection confirms no `o200k_base.tiktoken`, `.tiktoken` asset, or
  same-hash copy appears in the target wheel or sdist. Golden token-ID vectors
  still match when a separately provisioned canonical copy is supplied.
- This is a distribution-boundary mitigation, **not** a rightsholder grant.
  Classification C and unresolved file-level NOTICE obligations for any future
  project-distributed copy remain unchanged.

## ADR-028 validation record

- Explicit-provisioning boundary tests cover missing, wrong-hash, malformed,
  file-symlink, directory-symlink, fixed-hash admission, no-network behavior,
  safe doctor diagnostics, and external canonical golden token IDs.
- The provisioned canonical asset matches the historical fixed hash; ASCII,
  Chinese, multilingual, emoji, punctuation, and long-input token-ID/count
  vectors remain exact.
- `uv lock --check`, `uv sync --locked --offline`, offline wheel/sdist builds,
  direct archive inspection, `uv run mypy src`, Ruff, scanner regression, and
  `git diff --check` pass. Full pytest is `1918 passed, 1 warning`.
- The canonical security scanner still exits `1` only for the documented eleven
  TASK-016 fixtures; ADR-028 introduces zero findings and does not alter scanner
  policy.

## Status

- Current BPE artifact redistribution: **NOT APPLICABLE — PROJECT DOES NOT
  REDISTRIBUTE THE FILE**.
- ADR-008: **CORE REQUIREMENTS PRESERVED**; ADR-028 replaces only A-16's
  package-storage detail with explicit verified local provisioning.
- Any future decision to ship a copy requires direct rightsholder/legal
  confirmation covering this exact file and its NOTICE terms.
