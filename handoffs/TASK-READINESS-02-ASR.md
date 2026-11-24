# TASK-READINESS-02-ASR 交接报告

## 元数据

- Task: READINESS-02-ASR；Implementer `/root/readiness_asr`。
- Base: `7302f244e6326616c2b1ec72d0ad5f026d21cecb`。
- Worktree: `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness-asr`。
- Branch: `codex/task-readiness-asr`。
- Head: scoped commit SHA 由实际 Git 结果返回 root；任务建议 `IN_REVIEW`，不得自行设 DONE/合并。
- 具体模型实验范围已有用户批准，正式采用仍需 root 独立验收和授权。

## 目标与实际范围

修复原 Whisper profile 的静音幻觉、中长停顿覆盖与混合语音时轴失败；实际仅新增 acoustic helper、修改 worker/profile/完整资格 tuple 与负控制要求、相应测试及隔离验收脚本/材料。无 Schema、依赖/锁文件、SDK、权重、正式配置/owner 数据、Cloud、Vault、launchd、Distillation/UI/runtime composition 改动。

详细设计、复用来源、许可证和误拒绝限制见 `docs/validation/readiness-asr/IMPLEMENTATION.md`。DIRECT 既有 mlx-whisper 0.4.3 / MLX 0.32.0 / 同一固定模型、PCM 工具、validator/scorer、机器 seal、Jobs/BackupRestore；ADAPT 原始 PCM 分段及 native 时间映射。未复制 SDK 代码，不依赖新的组件。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| 全原始、独立、弱音与负控制冻结 | PASS | 原12正向+2弱音+3负控制；输入、预期、policy、实现 SHA 在各轮 FREEZE 与 product-freeze |
| 原 profile 纯静音失败真实复现 | PASS | `.var/readiness-asr/old-worker-silence-baseline.json`，3.5s 输出 Thank you./29.98s |
| run01/run02 失败保留 | PASS | 16/17 与11/17，完整失败 docs/raw 保留；未改门槛/样例 |
| run03 统一政策研究矩阵 | PASS | 17/17，`run03/RESULTS.json`；research 未颁产品资格 |
| 实际 Local Jobs 全矩阵 | PASS | `PRODUCT_RESULTS.json`；14 trusted 正向全通过，3负控FAILED/零调用/无 authority |
| 字幕、摘要、Evidence 完整 | PASS | 实际 repository timed cues/Summary 与 Evidence resolve；native原输出独立保存 |
| 重启普通 factory 与 seal | PASS | `PRODUCT_VERIFICATION.json`；新 Python 进程 current tuple 相同、普通 factory PASSED；缺失/改变 tuple STALE |
| 模型路径移除后历史 authority | PASS | 14条精确字幕/Evidence/摘要保持，production eligibility关闭 |
| 实际 Backup/Restore | PASS | 14条精确字幕/时间/文本/摘要恢复，3负控无 authority，恢复端模型/receipt不继承 |
| SQLite integrity/FK | PASS | 原库/恢复库 integrity/quick ok、FK空 |
| 正式采用与 GUI | root pending | 当前只隔离根 PASSED，正式门禁未变；root负责 GUI/普通设置/独立审查与整合 |

## 实际检查

- 红测试保留：缺少 helper、原长停顿边界、word-grid、旧8样本/缺负控制无法资格 PASS 均先失败再实现。
- 原聚焦121 tests PASS，独立 review P1 修复后的126 focused tests PASS（包括新增5项），日志 `.var/readiness-asr/review-p1-focused.txt`。
- Strict mypy 102源文件 PASS，`product-final-mypy.txt`；全src Ruff、相关脚本/新测试 Ruff PASS，py_compile/diffcheck PASS。
- 独立树完整 backend `PYTHONPATH=src .venv/bin/python -m pytest -q`：4033 passed、1 existing skip、2既有fixture warnings，992.12s；日志 `.var/readiness-asr/backend-full.txt`。该次 collection 在 review 新增5tests之前，新增全由126 focused覆盖；root整合后仍应执行候选完整集合。skip为既有 canonical o200k asset 未显式provision，未下载/弱化。
- 前端与真实 macOS GUI 由 root 在整合候选进行；此树不改前端。

## 可复核执行

- `PYTHONPATH=src .venv/bin/python scripts/qualify_readiness_asr_product.py .var/readiness-asr/product-01` 已真实完成。该根拒绝覆盖；不要重新运行同根。
- `PYTHONPATH=src:. .venv/bin/python scripts/verify_readiness_asr_product.py .var/readiness-asr/product-01` 已真实完成。恢复根拒绝覆盖；不重跑同根。
- 原 report、每项raw/native chunks、状态和 private资格 receipt 在 `.var/readiness-asr/product-01`；公开概要及 SHA在对应 PRODUCT*.json，无seal密钥进入Git。
- ROOT整合后可使用同一隔离 product根做 GUI，先确认 current tuple hash相同。tuple不绑定 providers/subtitles.py/transcripts.py；绑定 local_content.py/source_authority.py/worker/helper/scorer/qualification 与严格 executor/validator。
- 普通首次新任务的完整 GUI链路、生产激活、全部来源与 Intelligence资格由 root验收；本交接不据有限合成语音声称自然语音总体准确率。

## Diff 与剩余风险

- 仅任务scope，无删除测试/断言、弱化门槛、Expected/样例调整、非有限值修补、模型文本剪裁/去重、伪造成功/Receipt或Cloud执行。
- NO_SIGNAL/NOISE_ONLY是前置信号拒绝，不是语义真值；弱于固定−45dBFS或呈均匀噪声的真实语音可能误拒绝，任意录音不保证准确。固定25s硬窗口可能影响连续语音边缘词，必须承受原门槛。
- 声学receipt旧profile自然STALE；旧FAILED记录保留。当前新PASSED只写在隔离机器根，备份不迁移。
- 单机GPU时段已释放，无Whisper推理/验收进程残留。
- `DECISION NEEDED`: None for this approved isolation scope；正式采用由root按既有授权与验收处理。

## Reviewer / 主控

首轮独立 reviewer 判定 REJECT：P1为 harness 未把Summary/Evidence条件传入seal前qualification；P2为run02文档计数。现最小修复并新增5测试，等待root bounded re-review；未自行合入main。

## 独立审查整改补充

产品完整条件（真实READY、trusted字幕、Summary、Evidence resolve、全部entry.passed门槛）现在绑定completed；report/evaluate不一致时在任何seal写入前拒绝。负控制也绑定实际FAILED及完整passed状态。新增缺摘要/证据/字幕、stale pass flag、PENDING和before-seal无writer调用回归。原product-freeze与全部raw/report/receipt不变，新harnessfreeze为`product-freeze-review-p1.json`，`REVIEW_P1_REPLAY.json`证明已保存17项完整evidence canonical逐字节一致并认证旧receipt，无新推理或历史重写。后续新的显式engineeringrun默认读review后冻结；`--freeze`仅可显式引用匹配实现的材料，原冻实现hash不会被静默复用。
