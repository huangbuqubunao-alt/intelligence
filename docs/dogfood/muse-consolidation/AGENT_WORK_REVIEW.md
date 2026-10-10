# 豆包产品代码改动审查 — Muse 独立评审

> 评审对象：豆包在 `opencode/user-pilot` 分支（本目录对应 `~/workspace/intelligence/pilot/` 快照）中对 Intelligence 产品代码的 6 处改动（3 处产品修复 + 3 个测试文件新增）。
> 评审方法：`diff` 对比 main 基线（`~/workspace/intelligence/main`）与 muse-work 分支（`~/workspace/intelligence/muse-work`，含 Muse 修正版）；阅读改动点上下游代码语义；核查安全影响（云门禁、凭据、付费调用路径）；独立重跑后端回归测试。
> 结论总览：**Bug1 = MODIFY（方向正确，实现有 `#` 缺陷，已由 Muse 版修正）**；**Bug2 = ACCEPT**；**Bug3 = ACCEPT**；**4 组测试 = ACCEPT**。
> 本文档全部为中文。验证环境：Linux，Python 3.12，pytest 9.1.1；前端未做真实 GUI 点击（无浏览器自动化能力，见 INDEPENDENT_UX_REPORT.md）。

---

## 改动 1：前端路由 hashchange 修复（Bug1）—— MODIFY

**文件**：`frontend/src/workspace/App.tsx`（+ Muse 修正），`frontend/src/workspace/App.test.tsx`（新增 2 个测试）

### 豆包的改动内容

- 背景问题（属实）：`App.tsx` 的 `hashchange` 监听器只处理 `#Content/<videoId>` 深链接；普通视图 hash（`#Topics`、`#Settings` 等）变化被忽略。导致浏览器前进/后退、地址栏编辑 hash 时视图不跟随；侧边栏点击正常是因为 `navigate()` 显式 `setPage`。
- 豆包修复：在 `App` 组件内新增 `programmaticHash` ref 记录程序导航产生的 hash；扩展 `hashchange` 处理器——若事件 hash 与记录值一致则判定为程序导航并跳过，否则按用户导航处理（深链接打开内容详情，普通 hash 按 `initialPage()` 切换视图并 `setImported(false)` 等重置）。

### 审查发现：豆包实现存在真实的 `#` 缺陷

独立核验豆包原始代码（`~/workspace/intelligence/pilot/frontend/src/workspace/App.tsx`）：

```ts
// 豆包版（3 处赋值均不带 #）
programmaticHash.current = next;                    // 如 "Settings"
programmaticHash.current = "Content";
programmaticHash.current = destinations[target.kind];
```

而处理器比较的是 `location.hash`，浏览器返回的值**永远带前导 `#`**（如 `"#Settings"`）。因此：

- `programmaticHash.current === location.hash` **永不为真**，去重逻辑完全失效；
- 每次程序导航（如导入成功后 `navigate()`）触发的 hashchange 事件都会被误判为"用户导航"，进入用户分支，执行 **`setImported(false)`** —— 导入成功提示被立即清除（这正是 de-dup 机制要保护的东西）。

豆包代码中的注释（"A stale value is harmless: it is cleared on the next user hashchange because it will not match."）说明作者注意到了不匹配，但误判了后果：不是"无害"，而是**每一次程序导航都会被误分类**。

### Muse 版修正（muse-work 分支，已验证）

```ts
programmaticHash.current = "#" + next;
programmaticHash.current = "#Content";
programmaticHash.current = "#" + destinations[target.kind];
```

并配有注释说明为何必须带 `#`（`location.hash` 永远包含前导 `#`；存裸页面名则永不命中、每次程序导航都会被误判为用户导航从而清除导入提示）。三处赋值点与三处 `location.hash = …` 赋值一一对应（`location.hash = next` → 浏览器规范化为 `"#" + next`），经代码审查确认一致。

### 审查依据

- **语义正确性**：方向正确——hash 路由必须区分程序导航与用户导航，否则要么后退失效（原 Bug），要么程序导航被二次处理（豆包缺陷）。修正后两类导航各走正确分支。
- **副作用检查**：用户分支调用 `setImported(false)`、`setResearchReturn(null)`、`setContentTarget(null)`、`setDeltaTarget(null)` 后 `setPage(next)`；`initialPage()` 对未知 hash 有兜底（返回当前/默认页，见 App.tsx `initialPage`），不会因异常 hash 崩溃。深链接分支（`initialContentTarget()`）保留导入提示，与修复目标一致。
- **安全影响**：纯前端路由状态机，不涉及凭据、网络请求、付费调用。无安全降级。

### 决定：MODIFY（采用方向，修正实现）

---

## 改动 2：本地提炼 transport 授予生产资格（Bug2）—— ACCEPT

**文件**：`src/youtube_intel/runtime_composition.py`

### 豆包的改动内容

```python
transport = OllamaLocalDistillationTransport(
    settings=config.settings.local_scoring,
    # 注释：本地生产授权绑定精确安装模型 digest，每次 dispatch 校验；
    # M12 云生产门禁是独立机制（云提供商另需独立评审资格 + 逐次授权）；
    # 本地提炼（手动/自动）必须可用，否则所有本地提炼永远 WAITING_MODEL。
    production_qualified=True,
)
```

原为 `production_qualified=False`（M12 提交引入），且代码库中没有任何路径能把本地 transport 的该标志置为 True → 手动/自动本地提炼在 dispatch 前被 `is_authorized_for_normal_production` 拒绝 → 永远 `WAITING_MODEL`。

### 审查依据

- **根因属实**：`OllamaLocalDistillationTransport.is_authorized_for_normal_production` 定义为 `self._production_qualified and self.is_authorized_for(value)`（`distillation.py:2143`）；`_production_qualified` 在整个代码库中**仅**被这一处使用（grep 确认：定义、赋值、使用各一处），云模型走独立的 transport 类与 M12 门禁，改动不触及云路径。
- **安全等级未降低**：授予资格后，`is_authorized_for(value)` 仍强制执行全部逐次校验：`settings.model/expected_model_digest` 必须与编译期常量 `_MODEL/_DIGEST` 精确一致；`available` 属性每次 dispatch 前请求 Ollama `/api/tags` 核对**已安装模型的 digest**；`selected_provider == "ollama"`、`selected_model` 匹配、输出语言 ∈ {zh-CN, en}、证据非空。恢复的是 M12 之前的本地行为，未放宽任何一项。
- **注释准确**：新增注释对"本地 digest 绑定"与"M12 云门禁独立"的区分，与代码实际语义一致。

### 决定：ACCEPT（直接采用）

---

## 改动 3：备份就绪检查豁免两类终态 checkpoint（Bug3）—— ACCEPT

**文件**：`src/youtube_intel/backup_restore.py`

### 豆包的改动内容

备份 `readiness()` 的 distillation 检查与 `_is_settled_attention_source_run` 同步增加两类豁免：

1. `PENDING` + `distillation_no_new_intelligence_results` 已有该 `execution_id` 的结果行 → 视为已完结（"无新洞察"结果已持久记录；SUCCEEDED 终态要求存在 Intelligence 行，schema CHECK 约束使其无法置 SUCCEEDED，checkpoint 只能停在 PENDING，且 `continue` 入口只接受 PENDING→ 推进，实为死状态）；
2. `WAITING_MODEL` + `invocation_count = 0` → 从未被 claim/dispatch（模型在 reserve 时不可用），无运行中工作，且 `continue` 入口不接受 WAITING_MODEL，无法自行推进。

### 审查依据

- **根因属实**：`record_distillation_no_new_intelligence`（`state.py:10149`）只写结果表，不改 checkpoint 状态；SUCCEEDED 要求 Intelligence 行的约束与豆包描述一致；原检查把任何 PENDING/WAITING_MODEL 都视为 `DISTILLATION_ACTIVE`，一次提炼后备份被永久阻止——逻辑链完整。
- **豁免条件精确**：`_is_completed_no_new_intelligence` 要求 `JOIN distillation_no_new_intelligence_results ... AND c.invocation_count = 1`——结果行存在即证明该执行确实跑完（invocation_count ∈ {0,1}，有结果行则必为 1，条件等价但显式写出更严谨）；`_is_uninvoked_waiting_model` 要求 `status='WAITING_MODEL' AND invocation_count=0`——从未调度，无运行中工作。两个豁免都不会放过真正活动（RUNNING / WAITING_BUDGET / invocation_count=1 的 WAITING_MODEL / 无结果的 PENDING）的任务。
- **一致性**：主检查循环与 `_is_settled_attention_source_run` 的 SQL 豁免条件一致（后者用 `EXISTS` 子查询表达同一语义），两处不会出现"备份放行但 attention 判定阻塞"的不一致。
- **安全影响**：备份一致性保证未被削弱——豁免的都是"已持久记录且不可再推进"的终态，不存在备份时丢失未落盘工作的风险。

### 决定：ACCEPT（直接采用）

---

## 改动 4–6：新增回归测试 —— ACCEPT

| 测试文件 | 新增测试 | 审查结论 |
|---|---|---|
| `frontend/src/workspace/App.test.tsx` | ① 用户 hash 导航（地址栏/前进后退）切换 Settings/Topics/Content/Following/空 hash 回首页；② hashchange 深链接仍打开内容详情 | 测试覆盖了 Bug1 的两条核心路径；用 `HashChangeEvent` 模拟浏览器行为，断言视图标题切换与 hash 保持。语义正确。注意：前端测试尚未在本环境执行（无 node_modules，见 TEST_REPORT.md），结论基于代码审查。 |
| `tests/integration/test_runtime_composition.py` | `test_local_distillation_transport_is_production_authorized`：构造本地 runtime，断言 transport 为 ollama、模型匹配配置，并走完一次本地提炼授权 | 回归锚点准确（M12 门禁导致 WAITING_MODEL）。**已独立实测通过**（见下）。 |
| `tests/unit/test_backup_restore.py` | ① `test_backup_is_not_blocked_by_completed_no_new_intelligence`；② `test_backup_is_not_blocked_by_uninvoked_waiting_model` | 两个测试分别构造两类死 checkpoint 并断言 `readiness()["ready"] is True` 且无 `DISTILLATION_ACTIVE`。用例与豁免条件一一对应。**已独立实测通过**（见下）。 |

**独立实测**（muse-work 分支，Linux，Python 3.12，pytest 9.1.1，`PYTHONPATH=src`）：

- `tests/unit/test_backup_restore.py` → **28 passed**
- `tests/integration/test_runtime_composition.py` → **10 passed**
- 合计 38 passed，0 failed。含全部 3 个新增后端回归测试。

### 决定：ACCEPT（测试用例语义正确，命名与回归锚点清晰；后端已实测通过，前端待 npm 环境执行）

---

## 审查方法与边界声明

- 本评审未做真实 GUI 点击（本环境无浏览器自动化能力）；前端结论基于代码阅读与静态分析，已如实标注。
- 后端结论基于代码阅读 + 独立重跑相关测试套件（非复述豆包数据）。
- 未修改 muse-work 下除 `docs/dogfood/muse-consolidation/` 之外的任何文件；未做 git 操作。
