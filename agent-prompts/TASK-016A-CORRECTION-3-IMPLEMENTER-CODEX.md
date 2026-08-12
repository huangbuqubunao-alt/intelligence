# TASK-016A Correction 3 — composition-only trusted result boundary

固定 source HEAD 必须为 Reviewer 3 handoff-only evidence
`81ec5c6f9d015d5d48cc36053ca6a680be893acb`，唯一父为 `dfe0879…`，source 干净。

仅修 P1：`KnowledgeResult` 不得继承 `KnowledgeContent`。改为组合：Result 具有明确
`content: KnowledgeContent`、可信 `evidence_registry` 与 `provenance`，在 Result 边界
统一验证 content 中全部 Evidence ID。对象、Mapping、JSON 三种方式都不能把 Result/
Registry 当成模型 Content；只有显式 `result.content` 可作为 Content。

只允许 domain、contracts test、handoff 三路径。先 RED，再最小修复；原时间、配置、
Weekly、provenance 等契约不得退化。跑 focused/mypy/Ruff/full/build/diff，单父提交。
禁止依赖/Schema/Provider/runtime、真实资源、merge/push/016B–H。
