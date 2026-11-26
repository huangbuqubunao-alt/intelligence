# TASK-016A Correction 1 独立 Reviewer 2

你是全新独立 Reviewer 2，只审查固定 Correction 和完整 TASK-016A，不依赖此前 Reviewer
或 Implementer 自报，不修改业务代码。唯一 source 写入是追加 `handoffs/TASK-016A.md`。

固定对象：

```text
Worktree: /Users/developer/Documents/yia-worktrees/task-016a-intelligence-contract-foundation
Branch: codex/task-016a-intelligence-contract-foundation
Correction HEAD: 26a74cd508b28c9fd89e86af741414c8653f2721
Correction sole parent / Review 1 evidence: 6a564b18a3c91e4366c1b744733910dc5584854b
Review 1 evidence sole parent / implementation: 210dd203e722eabf3453808f490f4afe52139183
Implementation sole parent / base: 36969c5c5f7af75a2cf2255b63f742c12cf4fb0c
Correction range: 6a564b18a3c91e4366c1b744733910dc5584854b...26a74cd508b28c9fd89e86af741414c8653f2721
Complete range: 36969c5c5f7af75a2cf2255b63f742c12cf4fb0c...26a74cd508b28c9fd89e86af741414c8653f2721
Correction paths: src/youtube_intel/domain.py; tests/unit/test_contracts.py; handoffs/TASK-016A.md
Complete allowed paths: config/settings.example.yaml; src/youtube_intel/config.py; src/youtube_intel/domain.py; tests/unit/test_contracts.py; handoffs/TASK-016A.md
```

先核验 dynamic main 授权、source 分支/HEAD/父链/洁净度、Review 1 handoff-only、Correction
三路径和完整五路径、禁止路径与 `git diff --check`。静态复核完整 TASK-016A 五轴，重点独立
对抗：对象构造与 JSON 的 `NaN/+Inf/-Inf/1e999` 必须拒绝；合法 timed-subtitle 时间必须
JSON round-trip 等值；不得回归 timestamp basis、Evidence 引用、mode/fallback/digest、旧配置
安全迁移、Weekly V2 和 update-bypass。

无 P0/P1 后独立运行 lock check、locked offline sync、contracts、mypy、Ruff 全仓、full
pytest、offline build、YAML safe-load 和两组 diff check。禁止网络、模型、Key、真实 Vault、
用户数据、merge/push 和 TASK-016B–H。发现 P0/P1 立即停止后续门禁。

以 P0/P1/P2/P3 和 `APPROVE/REJECT` 追加 handoff，创建一个 handoff-only commit，其唯一父
必须为 `26a74cd508b28c9fd89e86af741414c8653f2721`。不得修改任务状态或其他文件。
