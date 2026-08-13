# Third-Party NOTICE Inventory — TASK-014 Phase A

- 状态：`DRAFT — RELEASE BLOCKED`
- 用途：列出已证实的归属/许可证事实和待补证据，不复制任何第三方 LICENSE 全文。
- 非结论：本文件不是项目自身 LICENSE，不授予再分发权，也不替代律师、TL 或发布负责人
  对最终发行物的审核。

| 组件或资源 | 已证实的许可证/来源事实 | NOTICE / 分发状态 |
|---|---|---|
| `yt-dlp[default,deno]==2026.7.4` | 直接锁定依赖；`default`/`deno` extra 由 `uv.lock` 记录。 | 必须在最终目标发行物中逐项确定它和 extra 依赖的归属/NOTICE；尚未签署。 |
| `mutagen==1.48.1` | `uv.lock` 显示它由 `yt-dlp` 的 `default` extra 引入；任务卡/Scout 输入将其标为 GPL-2.0-or-later。 | **BLOCKER**：TL/发布负责人须书面决定源码、二进制、bundle/容器的兼容分发方案。结论前不发布任何捆绑依赖物。 |
| OpenAI Python SDK `openai==2.46.0` | ADR-008、Reuse Register：Apache-2.0。 | 收集 SDK 及传递项的版权/NOTICE；SDK 隔离导入不等于可分发签署。 |
| `tiktoken==0.13.0` | ADR-008、Reuse Register：MIT。 | 收集包级 NOTICE；不得把此结论延伸到 `o200k_base.tiktoken` 文件。 |
| `Jinja2==3.1.6` | ADR-009、Reuse Register：BSD-3-Clause。 | 收集发行物所需归属/NOTICE；传递 `MarkupSafe==3.0.3` 独立补证。 |
| `spaCy==3.8.15` | Explosion 官方 Python 包；上游 LICENSE 与 PyPI 元数据声明 MIT；TASK-016B 固定版本和锁文件工件哈希。 | 本地英文依存分析的直接依赖；其新增传递项仍须逐项补齐版权与 NOTICE。运行时不得下载模型或联网 fallback。 |
| `en_core_web_sm==3.8.0` | Explosion 官方模型 wheel；MIT；12,806,118 bytes；SHA-256 `1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85`。模型来源清单包含 OntoNotes 5（commercial，licensed by Explosion）、ClearNLP conversion reference 与 WordNet 3.0 License。 | **RELEASE REVIEW REQUIRED**：Local-only 可从固定包加载；公开发行前须保留模型 LICENSE/来源归属、满足 WordNet NOTICE，并由发布负责人确认模型随 wheel/sdist/安装缓存的分发方式。缺失时只能 fail-closed，不得自动下载。 |
| `MarkupSafe==3.0.3` | 锁文件中存在；本阶段输入没有其许可证/NOTICE 原始证据。 | **EVIDENCE GAP**：发布前补充组件级证据与义务。 |
| `mlx-whisper==0.4.3` | ADR-007、Reuse Register：MIT。 | 条件性本地转写组件；解析后的 MLX/torch/Numba/NumPy 等及最终目标平台包必须逐项审查。 |
| MLX Community Whisper 转换模型 | ADR-007：固定来源/revision/权重哈希；转换仓库 model card 未声明 license。 | **BLOCKER**：不得假定转换模型可再分发或纳入发布物。 |
| ffmpeg | ADR-007：参考的 Homebrew `ffmpeg 8.1.2` 构建标记为 GPL-3.0-or-later。 | 不安装、不调用、不捆绑、不重新分发，直至单独许可与发行决策完成。 |
| Ollama / `qwen3:8b` | ADR-007：Ollama MIT；上游 Qwen3-8B 为 Apache-2.0，固定本机模型 digest 已登记。 | 程序、模型层、拉取与本机服务都需独立供应链审查；不得因 loopback 而跳过。 |
| `o200k_base.tiktoken` | 官方 Blob 来源；固定 SHA-256 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`；运行时无网络回退。 | **BLOCKER**：文件级许可证、归属和 NOTICE 尚无书面结论；不能纳入二进制或捆绑发行物。 |

## 未逐项证明的锁定组件

`docs/SBOM.md` 列出其余锁定解析包和版本。对任何会进入最终发行物、但未在本文件或
既有 ADR 中有明示来源/许可证事实的组件，当前状态均为 `EVIDENCE GAP`。不得根据
registry URL、包名或先前经验填补此缺口。

## 发布负责人需要作出的书面决定

1. 最终发行形态：仅源代码、可安装源码包、wheel、二进制、容器或带依赖 bundle；哪些
   条件性组件/模型/系统工具被明确排除。
2. `mutagen` GPL-2.0-or-later 对所选形态的处置，以及提供相应源代码/NOTICE 的责任人。
3. 每个纳入组件的许可证文本、版权和 NOTICE 的取得位置及发行包呈现方式。
4. 固定 BPE 文件的文件级归属、NOTICE 与分发许可；无明确结论时从所有发行物排除它。

未完成任一项时，发布结论为 `NO-GO`。
