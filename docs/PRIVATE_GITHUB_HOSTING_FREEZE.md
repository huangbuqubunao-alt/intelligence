# Private GitHub Hosting and Version Freeze

## Status and scope

**Status: prepared for private-source hosting only; product release remains
`NO-GO`.** This record implements the Product Owner's narrowly scoped
authorization to create a private GitHub repository and push `main` after the
checks recorded here succeed. It is not a public/open-source release, package
registry publication, GitHub Release, or distribution-scope change.

- **Pre-publication freeze anchor:** `main@838ac1df8263c361098b8e98343b0d740c9b89d2`
- **Repository/package identity:** `youtube-intel` / YouTube Intelligence Agent
- **Required hosting visibility:** GitHub **PRIVATE**
- **Current distribution posture:** `PRIVATE / PROPRIETARY / CONTROLLED
  DISTRIBUTION`
- **Product release readiness:** `NO-GO`
- **Live Deep Analysis provider:** none qualified; OpenAI is `0/2` and blocked
  on a future PO-approved ephemeral credential, while Kimi and Local retries
  remain unauthorized.
- **TASK-016G:** unauthorized.

The authorization is limited to a normal push of the audited local `main` to an
empty, ownership-verified private GitHub repository. It does not authorize a
GitHub Release, public visibility, PyPI, container/bundle/installer publishing,
provider qualification, credential access, TASK-016G, or operational
validation.

## Version decision

| Item | Decision |
| --- | --- |
| Previous package version | `0.1.0` |
| Selected package version | `0.1.0` (unchanged) |
| SemVer rationale | The existing project is already on a pre-1.0 SemVer lineage and this task changes only private-source-hosting evidence, not package behavior or public API. A version increment would communicate a product/package change that did not occur. |
| Why not `1.0.0` | The release remains `NO-GO`; no live Deep Analysis provider is qualified, no real qualified-provider output is eligible for PO acceptance, and TASK-016G is unauthorized. |
| Tag decision | **TAG DEFERRED — RELEASE NO-GO.** Existing tags are task/phase acceptance markers, not a SemVer package-release convention. No GitHub Release may be created. |

GitHub hosting is a controlled source backup/collaboration location. It is not
product release evidence and does not alter technical, provider, operational,
privacy, licensing, or Product Owner gates.

## Security and privacy audit boundary

Before any push, the audit must cover tracked files, all reachable commits,
tags, build metadata, and freshly built wheel/sdist archives. The following
facts are required for this private-hosting action:

1. No real credential, private key, runtime Vault data, provider output,
   transcript, SQLite/cache/log artifact, media artifact, or `.env` content is
   present in the current tracked tree or reachable history.
2. The canonical scanner remains exit `1` with exactly the existing eleven
   accepted intentional-positive **test** fixtures, zero new findings, and no
   claim that the scanner passed. Its finite disposition is unchanged.
3. Fresh wheel and sdist archives contain none of the above runtime/private
   material and do not contain `o200k_base.tiktoken`.
4. Root `NOTICE` and `pyproject.toml` preserve the proprietary controlled-use
   posture and the pseudonymous first-party attribution `墨竹`; no legal identity
   or first-party open-source license is introduced.
5. ADR-028's external-provisioning boundary remains intact: the project does
   not redistribute `o200k_base.tiktoken` in source, wheel, or sdist.

The audit also records the pre-existing historical controlled-Git hygiene P2:
some reachable historical documents contain machine-local absolute-path
metadata, and commit metadata contains historical personal/machine identity
information. This is neither a credential nor Vault/runtime payload. The
authoritative privacy disposition scopes it as a re-review trigger before
broader/public source distribution. It remains visible and is not waived by
this private-hosting action.

## Push prerequisites and post-push proof

The push may occur only after all of these are verified:

- the GitHub account and target repository ownership are known;
- the target repository is proven **PRIVATE** by GitHub API/CLI evidence;
- the remote is empty or otherwise has exactly the trusted local history (no
  unfamiliar history is overwritten);
- local `main`, the remote `main`, and the recorded pre-push commit agree after
  push; and
- the worktree remains clean.

The separate post-push evidence record is
[`PRIVATE_GITHUB_HOSTING_RESULT.md`](PRIVATE_GITHUB_HOSTING_RESULT.md). It must
record the exact pre-push commit, remote, private visibility proof, final
remote/local head comparison, artifact checks, and the continuing `NO-GO`
state.

## Non-authorizations preserved

This hosting freeze does **not** authorize OpenAI live qualification, a Kimi or
Local retry, credential use, TASK-016G, real Vault or launchd work, recovery
operations, a public release, public GitHub visibility, a GitHub Release,
PyPI, or container/bundle/installer distribution.
