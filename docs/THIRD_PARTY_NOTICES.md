# Third-Party NOTICE Inventory — TASK-014 Phase A

- 状态：`DRAFT — RELEASE BLOCKED`
- 用途：列出已证实的归属/许可证事实和待补证据；除下方必须随副本保留的 WordNet
  Release 3.0 notice 外，不复制第三方 LICENSE 全文。
- 非结论：本文件不是项目自身 LICENSE，不授予再分发权，也不替代律师、TL 或发布负责人
  对最终发行物的审核。
- 2026-08-31 的产物边界和 PO/TL 选择项已整理在
  [LICENSE_DISTRIBUTION_DECISION_PACKAGE.md](LICENSE_DISTRIBUTION_DECISION_PACKAGE.md)；该包不选择
  项目许可证，也不将本清单提升为发行批准。

| 组件或资源 | 已证实的许可证/来源事实 | NOTICE / 分发状态 |
|---|---|---|
| `yt-dlp[default,deno]==2026.7.4` | 直接锁定依赖；锁定安装 metadata 声明 `License-Expression: Unlicense`；`default`/`deno` extra 由 `uv.lock` 记录。 | 必须在最终目标发行物中逐项确定它和 extra 依赖的归属/NOTICE；尚未签署。 |
| `mutagen==1.48.1` | `uv.lock` 显示它由 `yt-dlp` 的 `default` extra 引入；任务卡/Scout 输入将其标为 GPL-2.0-or-later。 | **BLOCKER**：TL/发布负责人须书面决定源码、二进制、bundle/容器的兼容分发方案。结论前不发布任何捆绑依赖物。 |
| OpenAI Python SDK `openai==2.46.0` | ADR-008、Reuse Register：Apache-2.0。 | 收集 SDK 及传递项的版权/NOTICE；SDK 隔离导入不等于可分发签署。 |
| `tiktoken==0.13.0` | ADR-008、Reuse Register：MIT。 | 收集包级 NOTICE；不得把此结论延伸到 `o200k_base.tiktoken` 文件。 |
| `Jinja2==3.1.6` | ADR-009、Reuse Register：BSD-3-Clause。 | 收集发行物所需归属/NOTICE；传递 `MarkupSafe==3.0.3` 独立补证。 |
| `spaCy==3.8.15` | Explosion 官方 Python 包；上游 LICENSE 与 PyPI 元数据声明 MIT；TASK-016B 固定版本和锁文件工件哈希。 | 本地英文依存分析的直接依赖；新增传递项的 Local-only 版权/NOTICE 清单已在下方逐项闭合。公开 bundle 仍待许可证文本装载与 release-owner sign-off；运行时不得下载模型或联网 fallback。 |
| `en_core_web_sm==3.8.0` | Explosion 官方模型 wheel；MIT；12,806,118 bytes；SHA-256 `1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85`。模型来源清单包含 OntoNotes 5（commercial，licensed by Explosion）、ClearNLP conversion reference 与 WordNet 3.0 License。 | **RELEASE REVIEW REQUIRED**：Local-only 可从固定包加载；公开发行前须保留模型 LICENSE/来源归属、满足 WordNet NOTICE，并由发布负责人确认模型随 wheel/sdist/安装缓存的分发方式。缺失时只能 fail-closed，不得自动下载。 |
| `MarkupSafe==3.0.3` | 锁定安装 metadata 声明 `License-Expression: BSD-3-Clause`，并携带 license 文件。 | 发布前记录最终发行物所需的版权/NOTICE 呈现。 |
| `mlx-whisper==0.4.3` | ADR-007、Reuse Register：MIT。 | 条件性本地转写组件；解析后的 MLX/torch/Numba/NumPy 等及最终目标平台包必须逐项审查。 |
| MLX Community Whisper 转换模型 | ADR-007：固定来源/revision/权重哈希；转换仓库 model card 未声明 license。 | **BLOCKER**：不得假定转换模型可再分发或纳入发布物。 |
| ffmpeg | ADR-007：参考的 Homebrew `ffmpeg 8.1.2` 构建标记为 GPL-3.0-or-later。 | 不安装、不调用、不捆绑、不重新分发，直至单独许可与发行决策完成。 |
| Ollama / `qwen3:8b` | ADR-007：Ollama MIT；上游 Qwen3-8B 为 Apache-2.0，固定本机模型 digest 已登记。 | 程序、模型层、拉取与本机服务都需独立供应链审查；不得因 loopback 而跳过。 |
| `o200k_base.tiktoken` | `O200K_BASE_REDISTRIBUTION_EVIDENCE.md` verifies exact Blob identity and classifies the reviewed first-party evidence as `C`: rightsholder distribution, downstream grant ambiguous. | **BLOCKER**：the repository MIT license is not extended to the separate Blob data; file-level redistribution and NOTICE terms remain unresolved. ADR-008 cannot safely remove it; no controlled source/wheel/sdist distribution. |

## TASK-016B spaCy dependency NOTICE inventory

以下 23 项是 TASK-016B 相对原锁文件新增的完整集合。来源、许可证与版权取自本次锁定
环境内对应 distribution metadata 和随包 LICENSE；`Local-only: verified` 表示固定
锁定安装与离线运行已验证，不表示允许公开分发。所有项目的公开 bundle 状态均为
`BLOCKED`，直至发行物携带相应 LICENSE/版权文本并由发布负责人签署。

| 锁定组件 | 许可证 / 版权归属 | 固定来源 | 分发状态 |
|---|---|---|---|
| `annotated-doc==0.0.5` | MIT；© 2025 Sebastián Ramírez | `github.com/fastapi/annotated-doc` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `blis==1.3.3` | BSD-3-Clause；© University of Texas at Austin、HPE、AMD、ExplosionAI | `github.com/explosion/cython-blis` | Local-only verified；binary/source redistribution must retain BSD notice；public bundle blocked. |
| `catalogue==2.0.10` | MIT；© 2019 ExplosionAI GmbH | `github.com/explosion/catalogue` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `cloudpathlib==0.24.0` | MIT；© 2020 DrivenData Inc. | `github.com/drivendataorg/cloudpathlib` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `confection==1.3.3` | MIT；© 2019 ExplosionAI GmbH | `github.com/explosion/confection` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `cymem==2.0.13` | MIT；© 2014 Matthew Honnibal、2016–2022 ExplosionAI GmbH | `github.com/explosion/cymem` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `en-core-web-sm==3.8.0` | MIT；© 2021 ExplosionAI GmbH；另含下方 OntoNotes/WordNet 来源义务 | Explosion official model release wheel | Local-only verified；**public distribution blocked pending model-source rights/NOTICE sign-off**. |
| `markdown-it-py==4.2.0` | MIT；© 2020 ExecutableBookProject；含上游 markdown-it notice | `github.com/executablebooks/markdown-it-py` | Local-only verified；public bundle blocked pending both LICENSE notices. |
| `mdurl==0.1.2` | MIT；© 2015 Vitaly Puzrin/Alex Kocharin、© 2021 Taneli Hukkinen | `github.com/executablebooks/mdurl` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `murmurhash==1.0.15` | MIT；© 2014–2015 Matthew Honnibal、2016 ExplosionAI/spaCy GmbH | `github.com/explosion/murmurhash` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `preshed==3.0.13` | MIT；© 2014 Matthew Honnibal、2016 ExplosionAI GmbH | `github.com/explosion/preshed` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `rich==15.0.0` | MIT；© 2020 Will McGugan | `github.com/Textualize/rich` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `shellingham==1.5.4` | ISC；© 2018 Tzu-ping Chung | `github.com/sarugaku/shellingham` | Local-only verified；public bundle blocked pending ISC notice inclusion/sign-off. |
| `smart-open==8.0.1` | MIT；© 2015 Radim Řehůřek | `github.com/piskvorky/smart_open` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `spacy==3.8.15` | MIT；© 2015 Matthew Honnibal、2016 spaCy GmbH、2016–2024 ExplosionAI GmbH；含 Croatian lemma lookup notice | `github.com/explosion/spaCy` | Local-only verified；public bundle blocked pending all shipped LICENSE notices. |
| `spacy-legacy==3.0.12` | MIT；© 2021 ExplosionAI GmbH | `spacy.io` / installed package metadata | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `spacy-loggers==1.0.5` | MIT；© 2021 ExplosionAI GmbH | `github.com/explosion/spacy-loggers` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `srsly==2.5.3` | MIT；© 2018 ExplosionAI UG | `github.com/explosion/srsly` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `thinc==8.3.13` | MIT；© 2015 Matthew Honnibal、2016 spaCy/ExplosionAI GmbH | `github.com/explosion/thinc` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `typer==0.27.1` | MIT；© 2019 Sebastián Ramírez；含 Click LICENSE | `github.com/fastapi/typer` | Local-only verified；public bundle blocked pending both LICENSE notices. |
| `wasabi==1.1.3` | MIT；© 2018 Ines Montani | `github.com/explosion/wasabi` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `weasel==1.0.0` | MIT；© 2022 ExplosionAI GmbH | `github.com/explosion/weasel` | Local-only verified；public bundle blocked pending LICENSE inclusion/sign-off. |
| `wrapt==2.3.0` | BSD-2-Clause；© 2013–2026 Graham Dumpleton | `github.com/GrahamDumpleton/wrapt` | Local-only verified；binary/source redistribution must retain BSD notice；public bundle blocked. |

### `en_core_web_sm` model-source attribution

- Model package: MIT, © 2021 ExplosionAI GmbH.
- OntoNotes 5: Ralph Weischedel et al.; `https://catalog.ldc.upenn.edu/LDC2013T19`;
  commercial source licensed by Explosion. No OntoNotes code is separately packaged, but the
  model redistribution decision remains blocked pending release-owner confirmation.
- ClearNLP constituent-to-dependency conversion: Emory University;
  `github.com/clir/clearnlp-guidelines`; citation reference only, no code packaged with the model.
- WordNet Release 3.0: **Copyright 2006 by Princeton University. All rights reserved.**
  The WordNet 3.0 notice and disclaimer must appear on all distributed copies; Princeton's name
  must not be used in advertising or publicity. Source: `https://wordnet.princeton.edu/` and the
  fixed model wheel's `LICENSES_SOURCES`.

#### WordNet Release 3.0 required notice

The following text is retained verbatim from the fixed `en_core_web_sm==3.8.0` wheel's
`LICENSES_SOURCES` because the license requires it to appear on all copies, including modified
copies used internally or distributed:

```text
WordNet Release 3.0

This software and database is being provided to you, the LICENSEE, by
Princeton University under the following license. By obtaining, using
and/or copying this software and database, you agree that you have
read, understood, and will comply with these terms and conditions.:

Permission to use, copy, modify and distribute this software and
database and its documentation for any purpose and without fee or
royalty is hereby granted, provided that you agree to comply with
the following copyright notice and statements, including the disclaimer,
and that the same appear on ALL copies of the software, database and
documentation, including modifications that you make for internal
use or for distribution.

WordNet 3.0 Copyright 2006 by Princeton University. All rights reserved.

THIS SOFTWARE AND DATABASE IS PROVIDED "AS IS" AND PRINCETON
UNIVERSITY MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION, PRINCETON
UNIVERSITY MAKES NO REPRESENTATIONS OF MERCHANTABILITY OR FITNESS
FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF THE LICENSED SOFTWARE,
DATABASE OR DOCUMENTATION WILL NOT INFRINGE ANY THIRD PARTY PATENTS,
COPYRIGHTS, TRADEMARKS OR OTHER RIGHTS.

The name of Princeton University or Princeton may not be used in
advertising or publicity pertaining to distribution of the software
and/or database. Title to copyright in this software, database and
any associated documentation shall at all times remain with Princeton
University and LICENSEE agrees to preserve same.
```

TASK-016B dependency compliance conclusion: **Local-only implementation and offline build are
compliant with the frozen dependency evidence; public distribution remains NO-GO** until the
above license files/model-source attribution are included in the selected release form and the
release owner signs the OntoNotes/model redistribution decision.

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
