# PO/TL License and Distribution Decision Package — 2026-08-31

## Status and boundary

**DECISION-READY — no first-party license or distribution approval is made by
this document.** It is technical decision support, not legal advice.

This package reconciles `main@440c22e` against `pyproject.toml`, `uv.lock`, the
offline wheel/sdist build, `docs/SBOM.md`, `docs/THIRD_PARTY_NOTICES.md`,
ADR-007, ADR-008, and the reuse register. It does not change the release
decision: public distribution remains `NO-GO`.

## Objective artifact inventory

An offline `uv build --offline` inspection establishes the current artifact
boundary below. It is a build fact, not permission to distribute.

| Item | Current distribution fact | Bundled in wheel/sdist | Decision status |
| --- | --- | --- | --- |
| First-party Python source and CLI metadata | Current project artifact | Yes | First-party license required before publication. |
| Python dependency declarations | Wheel metadata / sdist project metadata | References only; dependency wheels are not vendored | Final install/bundle mode determines the actual resolved dependency set. |
| Lockfile | Repository/reproducibility input | No | Not automatically a shipped asset. |
| `o200k_base.tiktoken` | Committed `src/youtube_intel/resources` resource, SHA fixed by ADR-008 | **Yes**; 3,613,922 bytes | File-level origin, license, attribution, and redistribution decision are required. |
| `en_core_web_sm` | Direct URL runtime dependency | No; package manager may install it | Model-package/WordNet attribution and install-vs-bundle decision remain required. |
| MLX Whisper converted weights | Controlled runtime data path under `data/models/...` | No | Do not distribute without a separate source/license decision. |
| Ollama / Qwen model artifacts | External user/runtime installation reference | No | Do not distribute without a separate model/tool decision. |
| ffmpeg | External system tool reference | No | Do not bundle or redistribute without a separate decision. |
| OpenAI SDK | Normal Python runtime dependency | No vendored SDK; installed by resolver when selected | Apache-2.0 evidence exists; final NOTICE/component set depends on mode. |
| Kimi adapter | First-party source using no additional declared Kimi SDK | Yes as project code | No credential or provider payload is packaged. |
| Tests, fixtures, public-sample evidence | Repository QA/evidence material | No in inspected wheel/sdist | Do not treat test fixtures as runtime assets. |
| Generated release docs | Repository records | Only operations material is source-included | Final public source-repository policy remains a PO/TL decision. |
| Credentials, private Vault data, raw subtitle bodies | Not tracked package inputs | No | Must remain excluded. |

The inspection found no `LICENSE`, `COPYING`, or `NOTICE` file in the root or
in the generated wheel/sdist. The wheel and sdist contain no matching model
weight, tokenizer-other-than-BPE, fixture, or dependency-wheel payload.

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
| `yt-dlp[default,deno]` 2026.7.4 | Locked distribution metadata declares `License-Expression: Unlicense`; `default` resolves `mutagen==1.48.1`, recorded as GPL-2.0-or-later | Decide source/install-only versus any bundled binary/container/dependency distribution and required compliance process. |

`mypy`, `pytest`, and `ruff` are the three direct development dependencies.
They do not become runtime package payload merely because they are locked.

### GPL/copyleft-sensitive component

**Technical fact:** `mutagen==1.48.1` is introduced by the `yt-dlp[default]`
extra in the locked runtime tree. `ffmpeg` is an external Homebrew/system-tool
reference and is not in the inspected artifacts. No claim is made here about
legal effect beyond the existing documented GPL labels.

**Distribution consequence:** a normal wheel does not vendor these dependency
files, while a bundle, executable, container, or redistributed dependency set
could. The final artifact mode must name which interpretation applies and
identify the owner for corresponding source/notice obligations.

**Human decision:** TL/release owner confirms whether the product is private
execution only, source/install distribution, or a bundle; legal review confirms
the compliance plan before the latter is published.

## Model and tokenizer boundary

- The current package **does** ship `o200k_base.tiktoken`; ADR-008 requires it
  for fail-closed local token accounting and prohibits runtime download.
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
| B. Distribution mode | Internal/private execution; public source repository; wheel/sdist; bundled executable/container | Higher packaging modes require a target-artifact component/notice plan. | No wheel/sdist/bundle publication until C/D and the BPE decision are closed. |
| C. Model/tokenizer assets | Ship only current BPE; reference-install spaCy model; ship an approved model/tool; exclude optional model features | Current wheel/sdist already include BPE; no weights are shipped. | Do not add model weights, ffmpeg, or Ollama assets; decide BPE file rights before shipping the current artifact. |
| D. GPL/copyleft-sensitive components | Resolver-installed dependency set; separately distributed dependencies; bundle/container | `mutagen` is present through yt-dlp default; technical packaging facts do not replace legal analysis. | Avoid bundled/container distribution until a written compliance plan exists. |
| E. SBOM/NOTICE scope | Target runtime artifact only; target plus source repository; include dev tooling only when distributed | Dev tools are not automatically shipped; all actually installed/bundled runtime components need a final inventory. | Generate a target-specific runtime SBOM and NOTICE set; list dev tools separately as non-shipped. |

## Required PO/TL decisions

1. Select the first-party license, or explicitly keep the project private and
   forbid public artifact/source publication.
2. Select the intended first distribution mode: private execution, public
   source, wheel/sdist, or bundle/container.
3. Decide whether the current BPE-containing artifact may be distributed after
   file-level rights/NOTICE verification, or whether its packaging/design must
   be changed.
4. Decide whether spaCy model installation is supported in the chosen mode and
   obtain the required model-source/WordNet notice conclusion.
5. For any bundle/container, obtain a written `mutagen` GPL compliance decision
   and explicitly include or exclude ffmpeg, MLX, Ollama, and all model assets.
6. Confirm whether dev tools are distributed (default: no).

## Exact post-decision implementation plan

After those decisions—not before—make the following changes as applicable:

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

No license file, package license field, or third-party license text is added by
this decision-preparation package.

## Review outcome

Adversarial review found no silently selected license, fabricated legal
approval, bundled model-weight claim, dev-tool-as-runtime claim, or reduction
of other release gates. Technical P0: `0`; release-critical technical P1:
`0`; decision-dependent legal/release blockers remain open.
