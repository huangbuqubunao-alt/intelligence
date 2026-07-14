# ADR-002：冻结 V1 配置与领域契约

## 状态

Accepted

## 日期

2026-07-14

## 背景

`TASK-002` 的只读预检发现，现有 PRD 和系统设计已经确定产品方向，但尚不足以让实现者在不自行设计的前提下完成配置与领域契约。主要空白包括：频道优先级、重试和超时字段，路径边界，Provider 输入输出结构，评分与分析字段，以及流水线状态和 Job 重试状态之间的职责。

这些契约会被 `TASK-003` 至 `TASK-012` 并行消费。一旦各任务自行补齐，后续整合将产生字段漂移、状态重复和破坏性改名。因此在 `TASK-002` 开工前冻结 V1 契约。

产品负责人在主控对话中明确批准：

```text
批准 C-01 至 C-08 推荐方案，建立 ADR-002 并同步 TASK-002 契约。
```

## 决策

### C-01：频道优先级

- `priority` 为整数，范围 `0..100`，默认 `50`。
- 数值越大，频道越优先；相同优先级必须使用稳定的次级排序，不能依赖容器或数据库的偶然顺序。

### C-02：并发、重试与超时

- V1 的 `worker_concurrency` 固定为 `1`；配置其他值直接校验失败。
- 重试默认最多 `3` 次，指数退避基数 `2` 秒、上限 `60` 秒、抖动比例 `0.2`。
- 通用 HTTP、本地模型和云模型默认超时分别为 `30`、`300`、`120` 秒。
- `Retry-After` 优先于本地计算的退避时间；Provider 只返回建议，应用层决定 Job 调度。

### C-03：本地评分输入限制

- 本地评分默认 `temperature=0.0`、`max_output_tokens=1200`。
- 规范字幕输入上限为 `30000` 字符；该限制不同于云分析的 `30000` 输入 token。
- `TASK-002` 只冻结字段和边界；开头/正文/结尾的具体采样算法仍由 `TASK-007` 实现和验证。

### C-04：路径语义与边界

- `data_dir`、`logs_dir`、`templates_dir` 只接受相对项目根目录的路径。
- `vault_root` 必须是绝对路径；`vault_subdir` 必须是安全相对路径。
- 加载配置时先规范化并检查一次，每次文件写入前还必须对最终目标重新检查边界，防止符号链接或路径拼接绕过。

### C-05：跨模块结构化对象

- 固化 `DiscoveryCursor`、`DiscoveryBatch`、`ScoringInput`、`AnalysisInput`、`NotAvailable`、`NoteRef` 和 `WeeklyReportInput`。
- 跨模块接口不传递自由形状 `dict`；可选诊断也使用具名结构。
- 输入对象与输出对象分离，Provider 不得原地修改调用方对象。

### C-06：评分与分析规范字段

- 评分子维度固定为 `technical`、`business`、`product`、`originality`、`practicality`、`industry_impact`，每项可选且范围 `0..10`。
- 深度分析使用固定 `snake_case` 字段、结构化论点和结构化证据，并对集合基数设上限。
- 事实、推断和建议必须由枚举明确区分，不能只依赖自然语言措辞。

### C-07：三层状态模型

- `PipelineStatus` 只表示视频最近成功的业务进度或业务处置结果。
- `ProcessingStage` 表示一次 Job 当前要执行的阶段。
- `JobStatus` 表示任务尝试生命周期；`RETRY_PENDING` 和 `FAILED_FINAL` 只属于 Job。
- 阶段失败时视频保留最近成功的 `PipelineStatus`，Job 使用 `target_stage` 恢复；人工重跑创建新 Job，不覆盖旧 Job 历史。

### C-08：统一工程命令

`TASK-002` 统一从已锁定环境运行命令；后续 Python 任务的正式开工包也必须沿用同一形式：

```text
uv run python -m pytest ...
uv run mypy src
uv run ruff check .
```

不得在验收证据中混用裸 `python`、`pytest`、`mypy` 或 `ruff`。

## 考虑过的替代方案

### 让每个实现任务自行定义所需字段

- 优点：`TASK-002` 更小。
- 缺点：并行任务会产生不兼容的枚举、字段名和默认值，整合成本高。
- 结论：拒绝；公共契约必须先于并行实现冻结。

### 把重试状态同时放在视频和 Job 上

- 优点：查询单条视频时看起来更直接。
- 缺点：同一视频可以有多次 Job 尝试，两套状态会漂移，也无法可靠表达“最近成功阶段”。
- 结论：拒绝；重试和失败终态由 Job 承担。

### 所有路径都允许绝对路径

- 优点：配置灵活。
- 缺点：项目产物容易写出受控目录，测试也难以证明边界。
- 结论：只允许 Vault 根为绝对路径，项目产物使用项目根相对路径。

## 后果

- `TASK-002` 可以用确定字段和边界实现配置及领域模型，不再需要实现者补做产品设计。
- `TASK-003` 的 SQL Schema 必须分别持久化视频进度和 Job 尝试状态；最终 Schema 仍需单独审批。
- `TASK-007`、`TASK-008`、`TASK-009` 和 `TASK-011` 必须消费这里定义的结构，不能建立平行的自由字典格式。
- 本 ADR 批准契约，不授权安装 `pydantic`、`PyYAML`，不授权修改 `pyproject.toml`/`uv.lock`，也不改变 `TASK-002` 的依赖状态。
- 未来变更公共字段、状态语义或路径边界时，必须新增 ADR 并提供迁移影响，不能静默改名。

## 执行文件

- `docs/decisions/README.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-002-config-domain-contracts.md`
- `tasks/TASK-010-orchestration-recovery.md`
