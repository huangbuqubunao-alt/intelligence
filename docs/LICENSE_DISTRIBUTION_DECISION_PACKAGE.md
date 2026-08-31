# PO/TL License and Distribution Decision Package — 2026-08-31

## Status and boundary

**IMPLEMENTED POSTURE / CURRENT-TARGET LICENSING BLOCKER RESOLVED.** The Product
Owner / Tech Lead selected private, proprietary, controlled limited
source/wheel/sdist distribution. This document is technical evidence, not legal
advice; it does not authorize public distribution.

This package now reconciles `main@d198be7` against `pyproject.toml`, `uv.lock`, the
offline wheel/sdist build, `docs/SBOM.md`, `docs/THIRD_PARTY_NOTICES.md`,
ADR-007, ADR-008, and the reuse register. It does not change the release
decision: public distribution remains `NO-GO`.

## 2026-08-31 target-runtime scope freeze

The current controlled target is exactly source, sdist, and wheel. Dependencies
are separately resolved/installed by the environment package manager; a fully
materialized virtualenv, application bundle, container, installer, dependency
wheel cache, and copied `site-packages` tree are **not** current artifacts and
are **not authorized**. The fresh offline artifact evidence and complete,
separate runtime inventory are recorded in [SBOM](SBOM.md).

This resolves the technical `target installed-runtime SBOM / NOTICE + mutagen`
blocker for this bounded current form. The current first-party attribution is
recorded separately below; verified legal identity for future qualifying actions,
model-source, security, privacy, provider, operations, signature, and public
release gates remain distinct.

## Objective artifact inventory

An offline `uv build --offline` inspection establishes the current artifact
boundary below. It is a build fact, not permission to distribute.

| Item | Current distribution fact | Bundled in wheel/sdist | Decision status |
| --- | --- | --- | --- |
| First-party Python source and CLI metadata | Current project artifact | Yes | First-party license required before publication. |
| Python dependency declarations | Wheel metadata / sdist project metadata | References only; dependency wheels are not vendored | Final install/bundle mode determines the actual resolved dependency set. |
| Lockfile | Repository/reproducibility input | No | Not automatically a shipped asset. |
| `o200k_base.tiktoken` | Used only after explicit user/admin provisioning; SHA fixed by ADR-008/ADR-028 | **No**; no project artifact carries the file | File-level origin is recorded as classification C; the project does not claim or exercise downstream redistribution. |
| `en_core_web_sm` | Direct URL runtime dependency | No; package manager may install it | Not current first-party redistribution; model-source review is a future bundle/distribution gate. |
| MLX Whisper converted weights | Controlled runtime data path under `data/models/...` | No | Do not distribute without a separate source/license decision. |
| Ollama / Qwen model artifacts | External user/runtime installation reference | No | Do not distribute without a separate model/tool decision. |
| ffmpeg | External system tool reference | No | Do not bundle or redistribute without a separate decision. |
| OpenAI SDK | Normal Python runtime dependency | No vendored SDK; installed by resolver when selected | Apache-2.0 evidence exists; final NOTICE/component set depends on mode. |
| Kimi adapter | First-party source using no additional declared Kimi SDK | Yes as project code | No credential or provider payload is packaged. |
| Tests, fixtures, public-sample evidence | Repository QA/evidence material | No in inspected wheel/sdist | Do not treat test fixtures as runtime assets. |
| Generated release docs | Repository records | Only operations material is source-included | Final public source-repository policy remains a PO/TL decision. |
| Credentials, private Vault data, raw subtitle bodies | Not tracked package inputs | No | Must remain excluded. |

The current root contains `NOTICE`, the approved license-equivalent private
distribution notice. It records `墨竹` only as a pseudonymous first-party
project-owner/copyright attribution identifier for this controlled posture; it
does not claim verified legal identity, legal-entity status, registration, or IP
assignment. `pyproject.toml` points its PEP 621 license field to that file; the
current build backend embeds its restrictive text in wheel metadata as
`License:`, and the sdist carries the root `NOTICE` file. The wheel and sdist
contain no matching model-weight, tokenizer-other-than-BPE, fixture, or
dependency-wheel payload.

## First-party owner attribution disposition — 2026-08-31

| Record | Current controlled-artifact fact |
| --- | --- |
| First-party owner / copyright attribution identifier | `墨竹` |
| Attribution type | Pseudonymous project-owner identifier |
| Legal real-name verification in repository | Not recorded |
| Legal entity verification | Not established by this record |
| Copyright registration | Not claimed |
| IP assignment | Not claimed |

This closes the **owner-attribution blocker for the current private,
proprietary, controlled source/wheel/sdist posture**. It is not proof of legal
ownership beyond this internal attribution record. No legal name, government
identifier, phone number, address, personal email, or other unnecessary PII is
added to Git, NOTICE, wheel, sdist, or release documentation.

Verified legal identity must be established separately in an appropriately
controlled legal record before any action that actually requires it, such as a
commercial license agreement, copyright registration, IP assignment, corporate
ownership transfer, legally binding third-party authorization, or a distribution
mode whose governing policy requires it. This repository neither establishes nor
fabricates that record.

## Dependency and copyleft facts

`pyproject.toml` declares nine direct runtime dependencies and three direct
development dependencies. The locked environment resolves 107 packages across
platform/extra/dev markers; that lockfile is not a target-artifact manifest.

| Direct runtime item | Evidence-backed fact | Distribution consequence to decide |
| --- | --- | --- |
| `en-core-web-sm==3.8.0` | MIT model wheel; separate source/WordNet evidence in THIRD_PARTY_NOTICES | Decide installation reference versus any bundled model package; retain required model-source notices if shipped. |
| Jinja2 3.1.6 | BSD-3-Clause evidence | Include appropriate license/notice for the selected artifact set. |
| `mlx-whisper` 0.4.3 | MIT evidence; local transcription is conditional | Its transitive native/ML stack must be resolved for the target mode; no converted weights ship now. |
| OpenAI 2.46.0 | Apache-2.0 evidence; optional cloud capability | Package distribution is distinct from credential use; no key may be included. |
| Pydantic 2.13.4 | Locked distribution metadata declares `License-Expression: MIT` and carries a packaged license file | Record the required copyright/notice presentation for any target that installs it. |
| PyYAML 6.0.3 | Installed locked metadata declares MIT | Copyright/notice presentation for the final artifact remains to be recorded. |
| spaCy 3.8.15 | MIT evidence; 23 related locked component records exist | Public bundle remains blocked pending all applicable license/notice/model-source review. |
| tiktoken 0.13.0 | MIT package evidence | Does not decide the separately shipped BPE file. |
| `yt-dlp[default,deno]` 2026.7.4 | Locked distribution metadata declares `License-Expression: Unlicense`; `default` resolves `mutagen==1.48.1`, whose metadata and upstream tag declare GPL-2.0-or-later | Current source/wheel/sdist do not embed either package; separately installed runtime is inventoried. Any bundled/container/dependency-copy form remains a separate compliance gate. |

`mypy`, `pytest`, and `ruff` are the three direct development dependencies.
They do not become runtime package payload merely because they are locked.

### GPL/copyleft-sensitive component

**Technical fact:** `mutagen==1.48.1` is introduced by the `yt-dlp[default]`
extra in the locked runtime tree. `ffmpeg` is an external Homebrew/system-tool
reference and is not in the inspected artifacts. No claim is made here about
legal effect beyond the existing documented GPL labels.

**Distribution consequence:** the current normal wheel/sdist does not vendor
these dependency files, while a bundle, executable, container, or redistributed
dependency set would physically carry them. The current target is frozen as the
former; the latter remains unauthorized pending its own compliance package.

**Human decision retained:** before any future bundle/container/dependency-copy
distribution, the release owner and legal reviewer must identify the applicable
source, license-text, attribution, and GPL-sensitive compliance obligations.

## Model and tokenizer boundary

- The current package does **not** ship `o200k_base.tiktoken`. ADR-028 preserves
  ADR-008's local fail-closed accounting: an administrator explicitly provisions
  the canonical file at `storage.data_dir/tokenizers/o200k_base.tiktoken` before
  cloud analysis can run; runtime never downloads or substitutes it.
- The closed-loop rightsholder investigation is recorded in
  [`O200K_BASE_REDISTRIBUTION_EVIDENCE.md`](O200K_BASE_REDISTRIBUTION_EVIDENCE.md).
  It classifies the asset as **C — rightsholder distributed but downstream grant
  ambiguous**: origin and hash are verified, but no explicit file-level
  redistribution or NOTICE term was found.
- ADR-028 implemented the prepared explicit-provisioning alternative without
  runtime acquisition behavior. Missing or invalid local data fails closed before
  cloud-provider side effects. Classification C and the absence of a downstream
  grant remain recorded; the project avoids the ambiguous redistribution rather
  than claiming it was licensed.
- The current package does **not** ship MLX Whisper converted weights, Ollama
  model weights, ffmpeg, or an Ollama binary. Their recorded use is model/tool
  support, not current model redistribution.
- `en_core_web_sm` is a declared direct dependency, not a vendored wheel asset.
  Its installation/distribution and WordNet/model-source obligations must be
  resolved with the selected mode.
- Provider credentials, real provider responses, and private user data are not
  distribution assets and remain excluded.

## PO/TL decision matrix

| Decision | Options supported by current facts | Consequence | Lowest-scope technical default (not approval) |
| --- | --- | --- | --- |
| A. First-party license | Proprietary/all-rights-reserved internal use; MIT; Apache-2.0 | Defines the project’s public grant and the root/package metadata work. Apache-2.0 has an express patent-license component; MIT is shorter; proprietary use does not authorize public open-source publication. | Keep the project private until PO/TL selects a license and distribution intent. |
| B. Distribution mode | Internal/private execution; public source repository; wheel/sdist; bundled executable/container | Higher packaging modes require a target-artifact component/notice plan. | Controlled source/wheel/sdist only; current target SBOM/NOTICE is frozen, while public/bundle publication remains blocked. |
| C. Model/tokenizer assets | Explicitly provision BPE; reference-install spaCy model; ship an approved model/tool; exclude optional model features | Current wheel/sdist exclude BPE and all weights. | Preserve ADR-028; do not add model weights, ffmpeg, Ollama assets, or a BPE copy. |
| D. GPL/copyleft-sensitive components | Resolver-installed dependency set; separately distributed dependencies; bundle/container | `mutagen` is present through yt-dlp default, but absent from first-party archives. Technical packaging facts do not replace legal analysis. | Keep resolver-installed current target; bundle/container remains prohibited pending a written compliance package. |
| E. SBOM/NOTICE scope | Distributed artifact; separately installed target runtime; dev tooling | Dev tools are not shipped; source/wheel/sdist and runtime are separately reconciled in SBOM-A/B and NOTICE A/B/C. | Frozen for current controlled target. |

## Remaining PO/TL / legal inputs

1. Before any broader external distribution or action whose governing policy
   requires verified identity, establish the required legal identity separately;
   the current `墨竹` attribution is intentionally not that record.
2. Preserve ADR-028's explicit-provisioning boundary in any future distribution;
   a future proposal to ship the BPE requires a separate file-level
   redistribution/NOTICE conclusion.
3. For any future artifact that physically redistributes the spaCy model, obtain
   the required model-source/WordNet notice conclusion.
4. For any future bundle/container, obtain a written `mutagen` GPL compliance decision
   and explicitly include or exclude ffmpeg, MLX, Ollama, and all model assets.
5. Confirm any exception to the selected default that dev tools are not distributed.

## Exact post-decision implementation plan

After the remaining inputs—not before—make the following changes as applicable:

1. Add the PO/TL-selected root `LICENSE` text and `pyproject.toml` license
   metadata.
2. Generate a target-mode SBOM from the final build/install set; retain dev-only
   components in a separate non-shipped section.
3. Add only the third-party license/NOTICE texts and attributions required by
   the chosen artifact, including the BPE and model-source conclusions.
4. Update `docs/SBOM.md`, `docs/THIRD_PARTY_NOTICES.md`,
   `docs/RELEASE_BLOCKERS.md`, `docs/RELEASE_CHECKLIST.md`, and
   `docs/PROJECT_STATUS.md` with the signed decision and artifact evidence.
5. Rebuild in an isolated directory, inspect payload and metadata, and obtain
   the required Security/Privacy/QA/PO/TL release sign-offs.

The authorized private posture is encoded by root `NOTICE` and the package
license metadata. No open-source first-party license or third-party license
text is added by this package.

## Review outcome

Adversarial review found no fabricated verified owner identity or legal approval,
open-source implication, bundled model-weight claim, dev-tool-as-runtime claim,
or reduction of other release gates. Technical P0: `0`; release-critical
technical P1: `0`; the BPE sub-blocker and current owner-attribution blocker are
resolved, while future verified-identity and model-source requirements remain
separate.
