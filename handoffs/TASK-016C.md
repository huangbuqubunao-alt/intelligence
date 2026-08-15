# TASK-016C Handoff

## Phase E Authority Amendment Round 3

状态：**DESIGN READY / IMPLEMENTATION NOT AUTHORIZED**。

本轮仅更新设计控制面，未修改 `src/`、测试、依赖、数据库、Artifact、cache 或任何 Phase E 实现。

- Phase D accepted baseline：`2c11faf41e17c3b823a39bfd1018c5c876b236c5`。
- `QualityProvenanceAuthority` / `QualityPassAttestation` 保持 Phase D 的 Judge provenance 职责，
  不混入 scoring context。
- 后续 Phase E 必须使用 RuntimeOperations 私有铸造的 opaque `TrustedScoringContext`，并让
  Finalizer 重算 canonical scoring request identity；context 不携带调用方声明的 request hash。
- 可信输出改为 Finalizer-only opaque `TrustedScoreResult` wrapper；裸 `ScoreResult` 不能跨入
  Phase F–I trusted pipeline。
- `scoring.py` 的 canonical identity extraction 是必要且最小的未来授权项；它必须保持现有 hash
  完全兼容且无 I/O。

权威细节见
[Phase E Authority Amendment Round 3](../docs/TASK-016C-PHASE-E-AUTHORITY-AMENDMENT-ROUND-3.md)。
在独立设计审查和明确 implementation authorization 前，禁止启动 Phase E。
