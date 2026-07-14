# ADR-004：冻结 V1 发现、元数据与 yt-dlp 边界

## 状态

Accepted

## 日期

2026-07-14

## 批准记录

产品负责人在主控对话中明确批准：

```text
批准 ADR-004 D-01 至 D-08，包括 yt-dlp[default,deno]>=2026.7.4,<2026.8、必要传递依赖、网络下载、修改 pyproject.toml/uv.lock 及所列 uv 命令。真实 YouTube 冒烟、Cookie、ffmpeg 仍不授权。
```

## 背景

DEC-01 已批准“频道 RSS 增量发现 + yt-dlp 元数据/字幕清单”，但 `TASK-004` 只读预检发现两个跨任务空白：何时算“发现批次完整保存”，以及字幕轨道明细由 TASK-004 还是 TASK-005 拥有。此外，预检当时尚未批准 yt-dlp 的任务级版本、可选 extras、JavaScript challenge runtime、网络下载和锁文件动作。

2026-07-14 对官方发行资料的核实结果是：当前 stable 为 `2026.7.4`，支持 Python 3.12；裸 `yt-dlp` 包没有强制运行时依赖，但官方 PyPI 安装推荐 `[default]`，完整 YouTube 支持需要 `yt-dlp-ejs` 和受支持的 JavaScript runtime。仅批准裸包会让固定夹具通过，却留下真实 YouTube 链路不完整的风险。

本 ADR 冻结 TASK-004 的最终边界和依赖方案，并构成 D-06 所列依赖与锁文件动作的任务级批准。TASK-004 仍须等待 TASK-002 完成并由主控正式分配后才能安装或写入；真实 YouTube 冒烟、Cookie 和 ffmpeg 明确不在授权范围内。

## 决策

### D-01：发现批次的提交点

- `SourceProvider.discover` 只读取频道 RSS，返回 ADR-002 的 `DiscoveryBatch`，不直接写 SQLite。
- “完整保存发现批次”定义为：批次中去重后的全部候选 `video_id` 已以 `DISCOVERED` 原子 upsert，且 `next_cursor` 在同一 SQLite 事务成功写入。
- 不要求整批元数据获取成功后才推进游标。元数据按候选视频独立执行、独立重试；候选已落库后，即使元数据暂时失败也不会丢失。
- 批次任一候选写入或游标 CAS 失败时，整个事务回滚，游标不得推进。
- 空批次也可以更新 `last_checked_at`，但必须保留既有 `latest_published_at/latest_video_id/provider_cursor`，不得把游标清空。

### D-02：候选顺序、重复和游标规则

- RSS Adapter 按 Provider 响应顺序输出候选；同一批次第一次出现的 `video_id` 保留，后续重复丢弃。
- 状态仓库以 `video_id` 唯一 upsert；重复发现已有视频不产生第二条视频记录，也不让其 Pipeline 倒退。
- `DiscoveryBatch.channel_id`、当前 cursor 和 `next_cursor.channel_id` 必须一致，否则以非法 Provider 响应失败。
- 判断候选是否新于游标时使用 `published_at + video_id` 的稳定组合；同发布时间以 `video_id` 打破比较平局，但 `DiscoveryBatch.video_ids` 仍保持 Provider 原始顺序。
- RSS 中比当前游标旧但数据库尚无记录的条目不自动视为新候选；历史回填不属于 V1 TASK-004，需显式未来任务。

### D-03：元数据失败与 Pipeline/Job 职责

- 每个候选的元数据获取是独立 `METADATA` Job。成功后 upsert 完整 `VideoMetadata`，再由应用层按 ADR-002 转换表推进到 `METADATA_READY` 或 `DEFERRED`。
- 元数据网络超时、限流、解析错误和内容不可用必须映射为不同领域错误；Adapter 不自行重试、不写 Job 状态。
- 若 yt-dlp 返回足够信息，Adapter 必须填充完整 `VideoMetadata`，包括 `description`、`default_language` 和 `available_languages`。
- 若内容不可访问且无法形成完整 `VideoMetadata`，不得用空字符串伪造对象；返回标准化 `CONTENT_UNAVAILABLE` 错误及安全 availability 分类，由状态层记录候选 availability、Job `FAILED_FINAL` 和诊断。
- 一个候选元数据失败不得回滚其他候选，也不得回滚已经提交的发现游标。

### D-04：字幕清单归属

- TASK-004 只公开 `VideoMetadata.available_languages`：合并 yt-dlp 的人工字幕与自动字幕目录，规范化、去重并保持“人工首次出现顺序，随后自动字幕新增语言”的稳定顺序。
- TASK-004 不新增公共 `SubtitleTrack`、URL、格式或 manual/auto 类型字段，不修改 TASK-002 的 `domain.py`。
- TASK-005 在真正选择和下载字幕时重新查询轨道明细，并按“人工字幕 > 自动字幕 > Whisper”的规则选择。这一小段重复网络查询换取公共契约稳定和 URL 过期风险隔离。
- `available_languages` 是能力摘要，不得被 TASK-005 当作可直接下载的轨道缓存。

### D-05：RSS 与 yt-dlp Adapter 边界

- RSS 使用 Python 标准库 `urllib.request`、`xml.etree.ElementTree` 和 `datetime`；不为 RSS 引入 `httpx` 或 XML 第三方包。
- RSS 请求必须使用配置的 HTTP timeout、有限响应读取、明确 User-Agent，并把超时、HTTP 错误、非法 XML 分别映射为安全领域错误；不得把原始响应正文写入日志或异常。
- yt-dlp 使用 Python API，不启动 shell 子进程；对单视频设置等价于 `skip_download=True`、`noplaylist=True`、安静且禁用媒体/字幕/缩略图写入的选项。
- TASK-004 不传 `cookiefile`、`cookiesfrombrowser`、用户名、密码、`.netrc` 或浏览器会话，不读取登录态。
- TASK-004 不下载字幕、音频或视频，不调用 ffmpeg，不启用 `--remote-components` 运行时下载。
- 外部 yt-dlp 输出先映射为批准的具名领域对象；核心逻辑不得依赖原始自由 `dict`。

### D-06：yt-dlp 依赖与安装授权

推荐直接依赖：

```text
yt-dlp[default,deno]>=2026.7.4,<2026.8
```

理由与边界：

- `uv.lock` 固定实际解析版本；窄到 2026 年 7 月 stable 系列，跨月升级必须重新审查外部站点兼容性。
- `[default]` 按官方建议引入 `yt-dlp-ejs` 和默认网络/媒体元数据依赖；`[deno]` 引入 Python 分发的 Deno runtime，使 Apple Silicon 环境无需 Homebrew 或手工系统安装即可提供官方推荐的 JS runtime。
- 批准范围包含 uv 为这两个 extras 解析的必要传递依赖、包下载和 lock 更新；不授权任意新增直接依赖。
- 不引入 `httpx`、ffmpeg Python 包或系统 ffmpeg。ffmpeg 是后续媒体下载/转写任务的独立门禁，不属于 TASK-004。
- 不允许依赖自己在运行时远程下载 EJS 组件；使用锁定的 `yt-dlp-ejs` 包。
- 包网络下载授权不等于真实 YouTube 冒烟授权。TASK-004 默认检查必须完全离线；真实频道 `--limit 2` 冒烟仍需单独批准。

批准的唯一依赖写入命令为：

```bash
uv add 'yt-dlp[default,deno]>=2026.7.4,<2026.8'
uv lock --check
uv sync --locked
```

### D-07：测试矩阵与真实网络门禁

默认离线测试至少覆盖：

- RSS 正常顺序、批内重复、已见/新视频、同发布时间稳定排序、空批次、异常 XML、超时和有限响应。
- `DiscoveryBatch` 不直接推进持久化游标；Fake Repository 证明只有候选全部保存后才提交 `next_cursor`。
- 元数据固定夹具映射 `VideoMetadata` 全部字段，以及标题更新、Shorts、直播中、预约、已结束直播、公开视频、私有、删除和地区限制。
- 人工/自动字幕目录只形成有序去重 `available_languages`，不暴露临时轨道 URL。
- 捕获 yt-dlp 选项，证明 `skip_download`、无 Cookie/登录态、无字幕/音频/视频写入和无 remote components。
- 网络、限流、解析和不可用错误分类；安全消息不包含响应正文、Cookie 或本机路径。
- 相同夹具和 cursor 得到稳定结果；重复批次不产生重复持久化事件。

真实网络测试单独标记，默认不运行。只有主控给出频道、limit、时间窗口和网络授权后才可执行；不因真实站点波动修改离线断言。

### D-08：并行文件所有权与 Repository 接口

TASK-003 与 TASK-004 只有在 TASK-002 `DONE` 且 ADR-003/ADR-004 `Accepted` 后，才能从同一个最新 main 基线并行启动。

TASK-004 独占：

- `src/youtube_intel/discovery.py`
- `src/youtube_intel/providers/youtube.py`
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `tests/fixtures/youtube/**`
- `pyproject.toml`
- `uv.lock`
- `handoffs/TASK-004.md`

TASK-004 不得修改 `domain.py` 或 `state.py`。它通过窄 consumer Protocol/Fake 使用以下已冻结语义：读取当前 `DiscoveryCursor`、以 expected cursor 原子保存 `DiscoveryBatch`、upsert `VideoMetadata`、标记不可用候选。TASK-003 的具体 SQLite 类不得被 TASK-004 导入；两项整合后再运行组合契约测试。

TASK-003 的 SQL 位于 uv module root 下，必须由 TASK-003 的 `uv build` 证明已打包；它不得与 TASK-004 竞争 `pyproject.toml/uv.lock`。

TASK-004 工程门禁统一为：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run mypy src
uv run ruff check .
git diff --check
```

## 考虑过的替代方案

### 元数据全部成功后才推进 RSS 游标

看似更完整，但一个私有或长期失败视频会阻塞整个频道并反复产生同一批候选。候选先原子落库、元数据按视频重试更符合“单视频失败不阻断其他视频”。

### TASK-004 新增完整 `SubtitleTrack`

可减少 TASK-005 一次查询，但会在 TASK-002 实现进行中修改公共契约，并长期缓存易过期轨道 URL。拒绝；TASK-004 只提供语言能力摘要。

### 只安装裸 `yt-dlp`

依赖最少，固定夹具也能通过，但官方说明完整 YouTube 支持需要 EJS 和 JavaScript runtime。拒绝作为推荐生产方案。

### 依赖本机已有 Node/Deno

减少 Python lock 内容，但环境不可复现。推荐使用 yt-dlp 的 `deno` extra；若用户不接受该依赖体积，可明确选择“依赖外部 runtime”的替代方案并补充 doctor 门禁。

### 在 TASK-004 安装 ffmpeg

TASK-004 不下载或后处理媒体，ffmpeg 没有必要。拒绝并留给后续音频任务单独审批。

## 后果

- RSS 游标不会被单个元数据错误卡死，且不会因提前推进而丢候选。
- TASK-004 与 TASK-003 可在文件范围隔离的前提下真正并行。
- TASK-005 明确承担字幕轨道细节和选择，避免公共领域对象临时扩张。
- 推荐依赖比裸 yt-dlp 大，但换取官方支持的 EJS + Deno 可复现链路；升级节奏需要显式维护。
- 本 ADR 不授权真实 YouTube、Cookie、账号、ffmpeg、媒体下载或任何实现写入。

## 执行门禁

- D-01 至 D-08 和 D-06 的依赖动作已批准；不得由实现者扩展 extras 或直接依赖。
- TASK-004 当前只因 TASK-002 尚未完成而保持 `BLOCKED`。
- 真实 YouTube 冒烟、Cookie、账号登录、远程 EJS components 和 ffmpeg 仍未授权。
- 主控将在 TASK-002 `DONE` 后，从同一最新 main 基线并行分配 TASK-003 与 TASK-004。

## 研究依据

- [yt-dlp 2026.7.4 PyPI](https://pypi.org/project/yt-dlp/2026.7.4/)
- [yt-dlp 2026.07.04 官方发行](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.07.04)
- [yt-dlp 官方安装 Wiki：pip 推荐 default extra](https://github.com/yt-dlp/yt-dlp/wiki/Installation#with-pip)
- [yt-dlp 官方 EJS 指南：完整 YouTube 支持与 JS runtime](https://github.com/yt-dlp/yt-dlp/wiki/EJS)
- [Deno Python redistribution（含 macOS arm64 wheel）](https://pypi.org/project/deno/)
