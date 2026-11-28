# Wave 8 检查点（Checkpoint — Codex PR #59 第四轮终审整改完成）

- **分支**：`antigravity/autonomous-product-evolution-wave8-20261127`（[PR #59](https://github.com/huangbuqubunao-alt/intelligence/pull/59)，Draft）
- **仓库 `main` 基线**：`f7b97134a9fafd3e8e447851a4237bdc66f7e60e`（未触碰）
- **第 44 项整提交回退提交**：`f4da98e4`（已从当前分支清晰移除 `f3cd5563`）
- **VERIFIED_CODE_SHA_R2**：`81c16adb1be072cb3353d4b7194a4b6fae947e80`（交付头 `edf86fc6a2759a8c36ec0dd4dbfdc9593de9d7d8`）
- **VERIFIED_CODE_SHA_R3**：`2b0c4d6b40856a89fed7d4c21c2f1b837db1f574`（交付头 `8618ae53d6f46fdbbfc5bd69bd6683f346331c30`）
- **VERIFIED_CODE_SHA_R4**：`a31b0bdcbce9b8af52fe2f31ea0944b5520c2184`
- **第四轮收口范围**（针对 Codex Round 3 `B / HOLD` 仅剩 `P1-02` 2 项边界反例 + 3 项非阻断 P2/P3）：
  - **P1-02 边界 1（单条精确 `10 MiB` v1 笔记无损分段与复原）**：安全拆分 UTF-16 代理对并在导出前校验单卷 ≤ `10 MiB` 且 100% 覆盖原记录；实机使用 Codex 复现输入 `single-max-v1.json`（`10,485,760` B）导入→导出两卷（`10,485,712` B 与 `587` B）→空库全选复原，SHA-256 与原正文逐字节一致。
  - **P1-02 边界 2（多条超限常用视图逐项装卷与分段复原）**：改写常用视图为逐项装卷（必要时对超长 `searchQuery` 分段）绝不整组丢弃；实机使用 Codex 复现输入 `saved-view-a/b.json` 导入→导出两卷（`5,400,403` B 含 1 笔记 1 视图、`5,400,331` B 含 0 笔记 1 视图）→空库恢复 `1/1` 笔记与 `2/2` 视图。
  - **P2/P3 非阻断收敛**：多卷导入缺失卷显式警告、损坏文件原子整批中止不写入残片、`#Research` 剪贴板写入拒绝改报 `alert` 不误显「已复制」、纯启发式 `HEURISTIC_ONLY` 会话不再误标「已裁剪」。
- **本地全量验证（均运行于 `a31b0bdc`）**：Vitest **102/102（1376/1376）通过**（`67.30s`）、Vite 构建 `965ms`、`ruff`/`mypy` 0 错误、`test_public_beta_demo_showcase.py` + `test_research_lite.py` **16 passed**（`57.28s`）、真机 Chrome 对 Codex 原版证据输入实测 **0 控制台/页面/HTTP 错误**。
- **交付报告**：[01_CODEX_REVIEW_REMEDIATION_REPORT.md](../2026-11-28-pr59-remediation/01_CODEX_REVIEW_REMEDIATION_REPORT.md)
