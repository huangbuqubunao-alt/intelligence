# Release SBOM — TASK-014 Phase A

- 状态：`DRAFT — NOT A DISTRIBUTION APPROVAL`
- 生成依据：已提交的 `pyproject.toml`、`uv.lock`、ADR-007、ADR-008、ADR-009、
  `docs/REUSE_REGISTER.md` 与已有 handoff/验收记录。
- 范围：锁文件解析到的 Python 分发包，以及条件性模型、系统工具和固定资源边界。
- TASK-016B 补充：已对 spaCy 新增依赖执行锁定安装、离线构建、包 metadata/LICENSE
  清点与模型哈希核验；其余 Phase A 组件仍沿用原证据边界。
- 2026-08-31 离线 wheel/sdist 检查确认当前产物包含项目源码、operations/launchd 示例和
  `o200k_base.tiktoken`，不包含模型 weights、ffmpeg、Ollama、tests/fixtures 或依赖 wheel；
  这仅是产物边界事实，不构成任何分发许可。决策矩阵见
  [LICENSE_DISTRIBUTION_DECISION_PACKAGE.md](LICENSE_DISTRIBUTION_DECISION_PACKAGE.md)。

本清单是发行决策输入，不是法律意见，也不表示任何锁定组件、资源或其组合已经获准
分发。`uv.lock` 记录版本、来源与工件哈希，但不携带完整的许可证文本、NOTICE、版权
归属或组合分发结论。

## 项目与直接依赖

| 组件 | 锁定版本 / 关系 | 已有许可证或来源证据 | 发行缺口与处理 |
|---|---|---|---|
| `youtube-intel` | `0.1.0`；项目根 | `pyproject.toml` | 本任务不选择、创建或暗示项目自身 LICENSE。 |
| `en-core-web-sm` | `3.8.0`；固定 URL 直接运行依赖 | Explosion 官方 wheel；MIT；12,806,118 bytes；SHA-256 `1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85` | 仅用于本地英文依存分析；训练来源含 Explosion 授权的 OntoNotes 5 与 WordNet 3.0，最终分发前须完成模型级 NOTICE/许可复核。运行时禁止下载或网络 fallback。 |
| `jinja2` | `3.1.6`；直接运行依赖 | ADR-009 / Reuse Register：BSD-3-Clause | 收集发行包的版权与 NOTICE 证据；其传递 `markupsafe` 单列。 |
| `mlx-whisper` | `0.4.3`；直接运行依赖 | ADR-007 / Reuse Register：MIT | 仅条件性本地转写能力；模型、ffmpeg、传递包与真实资源另行审批。 |
| `openai` | `2.46.0`；直接运行依赖 | ADR-008 / Reuse Register：Apache-2.0 | 收集 SDK 与所有传递项的发行 NOTICE；不含真实密钥、响应或云验证。 |
| `pydantic` | `2.13.4`；直接运行依赖 | 锁定安装的 distribution metadata 声明 `License-Expression: MIT`，并携带 license 文件 | 发布前记录最终发行物所需的版权/NOTICE 呈现。 |
| `pyyaml` | `6.0.3`；直接运行依赖 | 锁定安装的 distribution metadata 声明 MIT | 发布前记录最终发行物所需的版权/NOTICE 呈现。 |
| `spacy` | `3.8.15`；直接运行依赖 | 固定 wheel metadata/LICENSE：MIT；© 2015 Matthew Honnibal、2016 spaCy GmbH、2016–2024 ExplosionAI GmbH | 固定本地 CPU 解析能力；21 个新增传递项逐项证据见 `THIRD_PARTY_NOTICES.md`。Local-only 已闭合；公开 bundle 仍阻断。 |
| `tiktoken` | `0.13.0`；直接运行依赖 | ADR-008 / Reuse Register：MIT | 收集其发行 NOTICE；不能据此推断附带 BPE 文件的文件级许可。 |
| `yt-dlp[default,deno]` | `2026.7.4`；直接运行依赖 | Reuse Register：DIRECT；锁定安装 metadata 声明 `License-Expression: Unlicense`；锁文件固定 extras | `default` 会带入 `mutagen`；二进制/捆绑发行被其 GPL 门禁阻断。 |
| `mypy` / `pytest` / `ruff` | `2.3.0` / `9.1.1` / `0.15.21`；直接开发依赖 | 锁文件版本 | 开发工具不自动进入运行时发行物；若随发行物提供，仍须组件级清单与许可证证据。 |

## 已识别的条件性资源与系统边界

| 项目 | 已证实事实 | 发布门禁 |
|---|---|---|
| `o200k_base.tiktoken` | OpenAI 官方 Blob 来源；固定 SHA-256 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`；运行时使用包内资源且无网络回退。 | 文件级许可证、归属、NOTICE 和可否纳入 sdist/wheel/二进制均未形成书面结论；含该文件的发行物 `BLOCKED`。 |
| MLX Community Whisper 转换模型 | ADR-007 固定 revision、大小和权重哈希；上游 OpenAI Whisper 资料为 MIT。 | 转换仓库 model card 缺少许可声明；不得推断转换产物许可或纳入任何发行物。 |
| ffmpeg | ADR-007 记录 Homebrew `ffmpeg 8.1.2` 构建标记为 GPL-3.0-or-later。 | 未获安装/调用/捆绑授权；不得捆绑或重新分发。 |
| Ollama 与 `qwen3:8b` | ADR-007 记录 Ollama MIT、固定 qwen digest；上游 Qwen3-8B 为 Apache-2.0。 | 程序版本、模型拉取、本机服务与模型分发均待单独供应链/授权审查。 |
| spaCy `en_core_web_sm` 英文模型 | 固定 `3.8.0` 官方 wheel、大小与 SHA-256；模型包声明 MIT；来源清单含 OntoNotes 5、ClearNLP 转换规则与 WordNet 3.0。 | 运行时只能加载已安装的固定包，缺失时 fail-closed；不得自动下载。公开分发前须复核训练来源归属、WordNet NOTICE 和模型随发行物策略。 |

## 锁定解析清单

TASK-016B 新增的 23 个包均已在 `docs/THIRD_PARTY_NOTICES.md` 明确记录版本、许可证、
版权、来源和分发状态；不再属于下述通用 `EVIDENCE GAP`。其余组件仍遵循本节限制。

以下是 `uv.lock` 中除上表已列直接依赖外的其余非根解析包（版本由锁文件直接给出）。
除本文件上表与 ADR 明确给出证据的组件外，许可证/版权/NOTICE 一律标为 `EVIDENCE GAP`，而非根据名称、
PyPI 来源或历史记忆推断。它们是直接依赖的传递解析项，或受平台/extra/dev marker
控制的解析项；锁文件本身不能证明某一目标发行形态实际会包含哪一个条件项。

```text
annotated-types 0.7.0        anyio 4.14.2                 ast-serialize 0.6.0
annotated-doc 0.0.5          blis 1.3.3                   catalogue 2.0.10
brotli 1.2.0                 brotlicffi 1.2.0.1           certifi 2026.6.17
cffi 2.1.0                   charset-normalizer 3.4.9     click 8.4.2
colorama 0.4.6               cuda-bindings 13.3.1         cuda-pathfinder 1.5.6
cloudpathlib 0.24.0          confection 1.3.3             cymem 2.0.13
cuda-toolkit 13.0.3.0        deno 2.9.2                   distro 1.9.0
filelock 3.31.0              fsspec 2026.6.0              h11 0.16.0
hf-xet 1.5.2                 httpcore 1.0.9               httpx 0.28.1
huggingface-hub 1.24.0       idna 3.18                    iniconfig 2.3.0
jiter 0.16.0                 librt 0.13.0                 llvmlite 0.48.0
markupsafe 3.0.3             mlx 0.32.0                   mlx-metal 0.32.0
markdown-it-py 4.2.0         mdurl 0.1.2                  murmurhash 1.0.15
more-itertools 11.1.0        mpmath 1.3.0                 mutagen 1.48.1
mypy-extensions 1.1.0        networkx 3.6.1               numba 0.66.0
numpy 2.4.6                  nvidia-cublas 13.1.1.3       nvidia-cuda-cupti 13.0.85
nvidia-cuda-nvrtc 13.0.88    nvidia-cuda-runtime 13.0.96  nvidia-cudnn-cu13 9.20.0.48
nvidia-cufft 12.0.0.61       nvidia-cufile 1.15.1.6       nvidia-curand 10.4.0.35
nvidia-cusolver 12.0.4.66    nvidia-cusparse 12.6.3.3     nvidia-cusparselt-cu13 0.8.1
nvidia-nccl-cu13 2.29.7      nvidia-nvjitlink 13.3.33     nvidia-nvshmem-cu13 3.4.5
nvidia-nvtx 13.0.85          packaging 26.2               pathspec 1.1.1
preshed 3.0.13               rich 15.0.0                  shellingham 1.5.4
pluggy 1.6.0                 pycparser 3.0                pycryptodomex 3.23.0
pydantic-core 2.46.4         pygments 2.20.0              regex 2026.7.10
requests 2.34.2              scipy 1.18.0                 setuptools 83.0.0
smart-open 8.0.1             sniffio 1.3.1                spacy-legacy 3.0.12
spacy-loggers 1.0.5          srsly 2.5.3                  sympy 1.14.0
thinc 8.3.13                 torch 2.13.0                 typer 0.27.1
tqdm 4.69.0                  triton 3.7.1                 typing-extensions 4.16.0
typing-inspection 0.4.2      urllib3 2.7.0                wasabi 1.1.3
weasel 1.0.0                 websockets 16.1              wrapt 2.3.0
yt-dlp-ejs 0.8.0
```

### 强制单列：`mutagen`

`uv.lock` 将 `mutagen==1.48.1` 列入 `yt-dlp` 的 `default` extra。任务包冻结输入与
TASK-014 任务卡均记录其为 GPL-2.0-or-later。源代码、二进制和捆绑依赖的具体分发方案
必须由 TL/发布负责人书面确认；在确认前，不得发布二进制、app bundle、容器或任何捆绑
依赖的发行物。

## 发行前完成条件

1. 针对最终目标平台和发行形态，生成可复现的组件包含清单，而不是仅复用锁文件的
   全平台解析集合。
2. 为每个会进入发行物的组件补齐许可证、版权、NOTICE、来源和适用义务的证据位置。
3. 对 `mutagen`、BPE 文件、模型、ffmpeg、Ollama、CUDA/NVIDIA 相关条件项给出明确的
   包含/排除与分发决策。
4. 由 PO、TL、QA 与隐私 Reviewer 在发布检查表签字；在此之前结论保持 `NO-GO`。
