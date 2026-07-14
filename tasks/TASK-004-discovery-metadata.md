# TASK-004：频道发现与元数据

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-002

## 目标

交付第一条垂直切片：从配置频道发现候选视频，获取标准化元数据，并通过接口交给状态仓库；实现必须支持固定离线夹具和可替换 Source Provider。

## 范围

- 按 `DEC-01` 实现频道发现和元数据 Adapter。
- 标准化公开视频、Shorts、已结束直播、直播中/预约和不可用内容的状态。
- 只有完整保存发现批次后才推进频道游标；重复发现同一视频不产生重复事件。

## 范围外

- 不下载字幕或音频。
- 不评分、不写 Obsidian。
- 不自动读取用户 YouTube 订阅或要求账号登录。

## 验收标准

- [ ] 固定夹具能发现新视频、忽略已见视频，并正确分类直播中、已结束和不可用内容。
- [ ] 重复运行同一发现批次得到相同视频集合，不产生重复持久化记录或错误推进游标。
- [ ] 网络超时、解析失败和内容不可用映射为不同领域错误，且响应正文不会原样写日志。

## 验证

- [ ] `python -m pytest tests/unit/test_discovery.py`
- [ ] `python -m pytest tests/integration/test_discovery_adapter.py`
- [ ] `mypy src && ruff check .`
- [ ] 可选受控冒烟：对一个已批准频道设置 `--limit 2`，只检查输出和数据库，不进入下载阶段。

## 预计触达文件

- `src/youtube_intel/discovery.py`
- `src/youtube_intel/providers/youtube.py`
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `tests/fixtures/youtube/` 下一个最小夹具文件

## 交付证据

- 离线测试结果。
- 如运行真实冒烟，记录命令、时间、频道和脱敏结果；未运行则明确说明。
- Provider 页面/响应变更风险说明。
