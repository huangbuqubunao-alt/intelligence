# Release SBOM — Controlled Source/Wheel/Sdist and Target Runtime

- Status: `COMPLETE FOR THE CURRENT CONTROLLED TARGET — NOT A PUBLIC-RELEASE APPROVAL`
- Evidence baseline: `main@d198be7`, `pyproject.toml`, `uv.lock`, locked offline sync, and a fresh offline wheel/sdist build inspected on 2026-08-31.
- This is a technical inventory, not legal advice, legal approval, or a change to ADR-008 or ADR-028.

## Frozen distribution boundary

The present, and only present, controlled-release boundary is **first-party source repository, project sdist, and project wheel**. Python dependencies are declared in project metadata and normally resolved as separate distributions by the environment package manager. This release does not distribute a materialized virtualenv/site-packages tree, dependency wheels, an application bundle, container image, or OS installer. A future source repository is not a grant for public publication; the controlled posture remains private/proprietary.

| Candidate form | Current target? | Physical relationship |
| --- | --- | --- |
| A. First-party source repository | Yes, controlled | First-party source only; no vendored Python dependency tree. |
| B. Project sdist | Yes, controlled | First-party source and package metadata; no dependency wheel/site-packages copy. |
| C. Project wheel | Yes, controlled | First-party package and dependency declarations; no dependency wheel/site-packages copy. |
| D. Separately installed Python dependencies | Yes, runtime consequence | Resolver installs separately; not physically distributed by this project. |
| E. Materialized virtualenv/site-packages | No | Local installation state, not a project artifact. |
| F. Application bundle | No | Not authorized. |
| G. Container image | No | Not authorized. |
| H. Installer image/package | No | Not authorized. |

ADR-028 continues to exclude `o200k_base.tiktoken` from A–C. Its classification `C` is preserved; a user/admin-provisioned runtime file is neither a project artifact nor a dependency record below.

## SBOM-A — distributed-artifact SBOM

Fresh `uv build --offline` output contained a 62-entry wheel and a 68-entry sdist. Direct archive inspection found **no** `mutagen`, `yt_dlp`, GPL/COPYING payload, dependency `.whl`, or `site-packages` tree. Both artifacts contain first-party package files and dependency declarations only. Therefore:

| Item | Version / status | Physically distributed by project | Notice set |
| --- | --- | --- | --- |
| `youtube-intel` | `0.1.0` | Yes | A — root `NOTICE` / package metadata; `墨竹` is the current pseudonymous owner-attribution identifier, not a verified legal identity. |
| `o200k_base.tiktoken` | Not applicable | No | None; ADR-028 explicit user/admin provisioning only. |
| All Python dependencies, including `mutagen` and `yt-dlp` | Not applicable | No | None physically copied into the wheel/sdist. |
| Dependency declarations | Locked references | Yes, as metadata only | The runtime inventory (SBOM-B) is supplied for truthful installation information. |

## SBOM-B — target installed-runtime dependency inventory

This is the deterministic normal supported-install closure for **CPython 3.12 on macOS arm64**, reconstructed by `uv tree --locked --no-dev --no-dedupe --python-platform aarch64-apple-darwin`. It contains 74 separately installed third-party distributions: 9 direct runtime dependencies and 65 transitives. `D` means direct and `T` transitive. Every record below is **runtime**, is **not physically distributed by this project**, and is **normally installed separately by the package manager**. Its license evidence is the locked installed distribution's PEP 639 `License-Expression`/`License` field and packaged metadata/license files, with lock identity in `uv.lock`; `NOASSERTION` honestly means that the installed metadata did not supply a license expression. For every registry row, the upstream source is the exact named PyPI record and artifact hash in `uv.lock`; `en-core-web-sm` is the explicit Explosion release URL in `pyproject.toml`/`uv.lock`. Installed `Project-URL` metadata is retained as supplemental upstream evidence. This rule applies to every row below.

| Dependency (relationship) | License declaration / evidence | Notice and compliance note |
| --- | --- | --- |
| `annotated-doc==0.0.5` (T) | MIT — installed METADATA | Runtime inventory only. |
| `annotated-types==0.7.0` (T) | NOASSERTION — installed METADATA | Runtime inventory only; no license conclusion inferred. |
| `anyio==4.14.2` (T) | MIT — installed METADATA | Runtime inventory only. |
| `blis==1.3.3` (T) | BSD — installed METADATA/LICENSE | Runtime inventory only. |
| `brotli==1.2.0` (T) | MIT — installed METADATA | Runtime inventory only. |
| `catalogue==2.0.10` (T) | MIT — installed METADATA | Runtime inventory only. |
| `certifi==2026.6.17` (T) | MPL-2.0 — installed METADATA | Runtime inventory only. |
| `charset-normalizer==3.4.9` (T) | MIT — installed METADATA | Runtime inventory only. |
| `click==8.4.2` (T) | BSD-3-Clause — installed METADATA | Runtime inventory only. |
| `cloudpathlib==0.24.0` (T) | NOASSERTION — installed METADATA | Runtime inventory only; no license conclusion inferred. |
| `confection==1.3.3` (T) | MIT — installed METADATA | Runtime inventory only. |
| `cymem==2.0.13` (T) | MIT — installed METADATA | Runtime inventory only. |
| `deno==2.9.2` (T; `yt-dlp[deno]`) | MIT — installed METADATA | Runtime inventory only. |
| `distro==1.9.0` (T) | Apache License 2.0 — installed METADATA | Runtime inventory only. |
| `en-core-web-sm==3.8.0` (D) | MIT — installed METADATA/LICENSE | Runtime inventory only; model-source/WordNet future bundle gate remains. |
| `filelock==3.31.0` (T) | MIT — installed METADATA | Runtime inventory only. |
| `fsspec==2026.6.0` (T) | BSD-3-Clause — installed METADATA | Runtime inventory only. |
| `h11==0.16.0` (T) | MIT — installed METADATA | Runtime inventory only. |
| `hf-xet==1.5.2` (T) | Apache-2.0 — installed METADATA | Runtime inventory only. |
| `httpcore==1.0.9` (T) | BSD-3-Clause — installed METADATA | Runtime inventory only. |
| `httpx==0.28.1` (T) | BSD-3-Clause — installed METADATA | Runtime inventory only. |
| `huggingface-hub==1.24.0` (T) | Apache-2.0 — installed METADATA | Runtime inventory only. |
| `idna==3.18` (T) | BSD-3-Clause — installed METADATA | Runtime inventory only. |
| `jinja2==3.1.6` (D) | NOASSERTION in field; BSD-3-Clause evidence in ADR-009 | Runtime inventory only. |
| `jiter==0.16.0` (T) | MIT — installed METADATA | Runtime inventory only. |
| `llvmlite==0.48.0` (T) | BSD-2-Clause AND Apache-2.0 WITH LLVM-exception — METADATA/LICENSE | Runtime inventory only. |
| `markdown-it-py==4.2.0` (T) | NOASSERTION in field; MIT evidence in installed license | Runtime inventory only. |
| `markupsafe==3.0.3` (T) | BSD-3-Clause — installed METADATA/LICENSE | Runtime inventory only. |
| `mdurl==0.1.2` (T) | NOASSERTION in field; MIT evidence in installed license | Runtime inventory only. |
| `mlx==0.32.0` (T) | MIT — installed METADATA | Runtime inventory only. |
| `mlx-metal==0.32.0` (T; macOS arm64) | MIT — installed METADATA | Platform-specific runtime item; not project-distributed. |
| `mlx-whisper==0.4.3` (D) | MIT — installed METADATA | Runtime inventory only; model artifacts excluded. |
| `more-itertools==11.1.0` (T) | MIT — installed METADATA | Runtime inventory only. |
| `mpmath==1.3.0` (T) | BSD — installed METADATA/LICENSE | Runtime inventory only. |
| `murmurhash==1.0.15` (T) | MIT — installed METADATA | Runtime inventory only. |
| `mutagen==1.48.1` (T; `yt-dlp[default]`) | GPL-2.0-or-later — installed METADATA and packaged `COPYING`; upstream tag `release-1.48.1` | Separately installed only; see Mutagen posture below. |
| `networkx==3.6.1` (T) | BSD-3-Clause — installed METADATA | Runtime inventory only. |
| `numba==0.66.0` (T) | BSD — installed METADATA/LICENSE | Runtime inventory only. |
| `numpy==2.4.6` (T) | Composite expression — installed METADATA/LICENSE | Runtime inventory only. |
| `openai==2.46.0` (D) | Apache-2.0 — installed METADATA | Runtime inventory only. |
| `packaging==26.2` (T) | Apache-2.0 OR BSD-2-Clause — installed METADATA | Runtime inventory only. |
| `preshed==3.0.13` (T) | MIT — installed METADATA | Runtime inventory only. |
| `pycryptodomex==3.23.0` (T) | BSD, Public Domain — installed METADATA/LICENSE | Runtime inventory only. |
| `pydantic==2.13.4` (D) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `pydantic-core==2.46.4` (T) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `pygments==2.20.0` (T) | BSD-2-Clause — installed METADATA | Runtime inventory only. |
| `pyyaml==6.0.3` (D) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `regex==2026.7.10` (T) | Apache-2.0 AND CNRI-Python — installed METADATA/LICENSE | Runtime inventory only. |
| `requests==2.34.2` (T) | Apache-2.0 — installed METADATA | Runtime inventory only. |
| `rich==15.0.0` (T) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `scipy==1.18.0` (T) | BSD-3-Clause plus wheel-bundled components — installed METADATA/LICENSE | Runtime inventory only; future bundle must inspect target binary contents. |
| `setuptools==83.0.0` (T) | MIT — installed METADATA | Runtime inventory only. |
| `shellingham==1.5.4` (T) | ISC — installed METADATA | Runtime inventory only. |
| `smart-open==8.0.1` (T) | NOASSERTION — installed METADATA | Runtime inventory only; no license conclusion inferred. |
| `sniffio==1.3.1` (T) | MIT OR Apache-2.0 — installed METADATA | Runtime inventory only. |
| `spacy==3.8.15` (D) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `spacy-legacy==3.0.12` (T) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `spacy-loggers==1.0.5` (T) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `srsly==2.5.3` (T) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `sympy==1.14.0` (T) | BSD — installed METADATA/LICENSE | Runtime inventory only. |
| `thinc==8.3.13` (T) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `tiktoken==0.13.0` (D) | MIT — installed METADATA/LICENSE | Package only; does not license the external BPE Blob. |
| `torch==2.13.0` (T) | Composite expression — installed METADATA/LICENSE | Runtime inventory only; future bundle must inspect target binary contents. |
| `tqdm==4.69.0` (T) | MPL-2.0 AND MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `typer==0.27.1` (T) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `typing-extensions==4.16.0` (T) | PSF-2.0 — installed METADATA/LICENSE | Runtime inventory only. |
| `typing-inspection==0.4.2` (T) | MIT — installed METADATA | Runtime inventory only. |
| `urllib3==2.7.0` (T) | MIT — installed METADATA | Runtime inventory only. |
| `wasabi==1.1.3` (T) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `weasel==1.0.0` (T) | MIT — installed METADATA/LICENSE | Runtime inventory only. |
| `websockets==16.1` (T) | BSD-3-Clause — installed METADATA | Runtime inventory only. |
| `wrapt==2.3.0` (T) | BSD-2-Clause — installed METADATA/LICENSE | Runtime inventory only. |
| `yt-dlp-ejs==0.8.0` (T; `yt-dlp[default]`) | Unlicense AND MIT AND ISC — installed METADATA/LICENSE | Runtime inventory only. |
| `yt-dlp==2026.7.4` (D; extras `default,deno`) | Unlicense — installed METADATA/LICENSE | Runtime inventory only. |

The lock's 107-package universal resolution additionally contains mutually exclusive platform-marker candidates. They are not silently counted as the macOS-arm64 target inventory. On another supported platform, a fresh target-platform SBOM-B reconstruction is required before distribution.

## Dev tooling — excluded from the runtime target

The direct dev dependencies are `mypy==2.3.0`, `pytest==9.1.1`, and `ruff==0.15.21`. Six additional packages are dev-only on this target: `ast-serialize==0.6.0`, `iniconfig==2.3.0`, `librt==0.13.0`, `mypy-extensions==1.1.0`, `pathspec==1.1.1`, and `pluggy==1.6.0`. `packaging`, `pygments`, and `typing-extensions` are shared with runtime and are already in SBOM-B. None of these dev-only packages belongs to a current wheel/sdist or installed-runtime NOTICE set.

## Mutagen relationship and GPL-sensitive technical posture

- `pyproject.toml` declares `yt-dlp[default,deno]>=2026.7.4,<2026.8`; the lock records the exact edge `youtube-intel -> yt-dlp[default] -> mutagen==1.48.1`.
- `mutagen==1.48.1` is GPL-2.0-or-later. This is supported by the locked distribution's PEP 639 `License-Expression`, its packaged `COPYING`, the upstream `quodlibet/mutagen` `release-1.48.1` tag, and the upstream project statement that it is GPL version 2 or later.
- First-party code does not import `mutagen`. It imports `yt_dlp` for metadata and subtitle-directory work only; both adapters use `download=False`, `skip_download=True`, disable subtitle/thumbnail/info writes, and do not call ffmpeg. yt-dlp documents Mutagen for `--embed-thumbnail` in certain media formats. That media-embedding feature is not part of current product behavior.
- Removing the `default` extra is technically possible in package metadata, but is **not authorized by this task** and was not done. It would remove the declared default-extra feature set (including Mutagen-backed thumbnail embedding) and requires a separate product/test decision; absence of a direct import is not a sufficient reason to change the dependency graph.
- **Current wheel/sdist:** Mutagen code and license files are not physically redistributed. **Normal installed environment:** the package manager installs Mutagen separately. **Future materialized venv, bundle, container, or installer:** it would physically include Mutagen and is not authorized until a target-specific GPL/notice/source-obligation compliance package is complete.

## SBOM conclusion

SBOM-A is complete for the controlled first-party artifact. SBOM-B is complete as a separately installed target-runtime inventory. The current target neither embeds nor claims to redistribute Mutagen, so this record makes no legal claim about GPL effects beyond the documented facts. Bundle/container compliance, model-source review, verified legal identity where a future action requires it, security/privacy, provider, operations, and formal signatures remain distinct release gates.
