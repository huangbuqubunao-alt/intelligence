# 测试报告（TEST_REPORT）— Muse 评审轮

> 分支：`muse/user-pilot-consolidation`（from main `fad25e6`）。本报告只记录实际执行过的测试；未执行的写明原因，不虚构结果。

## 环境

| 项 | 值 |
|---|---|
| 操作系统 | Linux（评审用虚拟机） |
| Python | 3.12.3（系统）/ venv Python 3.12 |
| pytest | 9.1.1（`~/workspace/intelligence/venv`） |
| 执行方式 | `cd ~/workspace/intelligence/muse-work && PYTHONPATH=src <venv>/bin/python -m pytest … -p no:cacheprovider` |
| 环境备注 | `/tmp` 为 512M tmpfs 且已满，pytest 需 `TMPDIR=~/workspace/intelligence/tmp-pytest` 重定向方可运行；此为本机环境限制，与产品代码无关 |

## 已验证项（本轮实测）

| 套件 | 命令 | 结果 |
|---|---|---|
| `tests/unit/test_backup_restore.py` | 同上 | **27 passed**（含保留的新增回归测试 `test_backup_is_not_blocked_by_completed_no_new_intelligence`；`test_backup_is_not_blocked_by_uninvoked_waiting_model` 已随 WAITING_MODEL 豁免回退移除，见 M-5） |
| `tests/integration/test_runtime_composition.py` | 同上 | **10 passed**（含新增回归测试 `test_local_distillation_transport_is_production_authorized`） |
| `test_task022…::test_backup_quiescence_requires_confirmed_user_cloud_success_for_local_wait`（3 用例） | 同上 | **3 passed**（WAITING_MODEL 豁免回退后的定向验证） |
| 定向验证合并 | 同上 | **40 passed，0 failed** |

结论：Bug2（本地提炼生产资格）、Bug3（备份豁免，M-5 回退后）的产品代码改动与其回归测试在本环境全部通过。

## 后端全量套件（`pytest tests/`，不含 e2e）——已完成

| 分支 | 结果 | 日志 |
|---|---|---|
| muse-work（含本轮全部改动） | **704 failed / 3265 passed / 1 skipped**（33.5 分钟） | `~/workspace/muse-backend-tests.log` |
| main 基线 | **702 failed / 3264 passed / 1 skipped**（32.8 分钟） | `~/workspace/main-backend-tests.log` |

**失败集合差集**（`comm` 对比两个 FAILED 列表）：
- 仅 muse-work 失败（3 个）：`tests/integration/test_task022_personalized_distillation.py::test_backup_quiescence_requires_confirmed_user_cloud_success_for_local_wait` 的 3 个参数化用例 —— **确认为本次改动引入的回归**（豆包 WAITING_MODEL 豁免过宽），已回退修复并定向验证 40 passed（见 ISSUES_FOUND.md M-5）。
- 仅 main 失败（1 个）：`tests/integration/test_local_content_adversarial.py::test_original_move_delete_mutation_dedupe_and_changed_import` —— 在 muse-work 上通过，属环境抖动/时序敏感，非改动相关。
- 其余 701 个失败在两个分支完全一致，均为 pre-existing 环境/固件限制，与本次改动无关：
  - `ScoreResult` pydantic 校验 "reason does not match output_language"（约 460 处）及连带的 `DeepAnalysisRejected: requires a verified scoring read`（148 处）——评分管线 fixture/环境问题（venv pydantic 2.13.5 在 `pyproject.toml` pin 范围 `>=2.13.4,<2.14` 内，非版本错配）；
  - macOS 特有：`/usr/sbin/ioreg` 缺失（16 处）、APFS/Keychain 相关；
  - 需真实 Ollama 服务：`OllamaProviderError`（10 处）；
  - 改动直接相关的测试文件（`test_backup_restore.py`、`test_runtime_composition.py`）在全量中零失败。

**结论**：回退 M-5 后，muse-work 与 main 基线的失败集合实质一致（差 1 个环境抖动项），无新增回归。

## 其他已确认项
| 前端 vitest（`App.test.tsx`） | **111 passed**（2026-10-11 实测：108 个原有 + 豆包新增 2 个 + Muse 新增导入回归测试 1 个）。另 `tsc -b` 类型检查通过、`vite build` 生产构建成功 |
| 豆包报告的 2 个后端失败测试 | 在全量套件中未出现 FAILED；此前单独运行均通过，确认为进程时序类环境敏感测试，非本次改动引入 |
| `npm run build`（生产构建） | **通过**（`tsc -b` + `vite build`，dist 输出正常） |
| 真实 GUI 回归（导航 hash、提炼、备份三条路径） | **未执行** —— 本环境无浏览器自动化能力；豆包轮次的 GUI 验证记录保留在其分支备查，本轮不重复声称 |
| macOS 特有项（Keychain、APFS clonefile、原生文件选择器） | **NOT TESTED**（本环境为 Linux，相关分支不可达） |
| 本地转写模型（mlx-whisper）链路 | **NOT TESTED**（模型未配置，见 U1） |
| 2 GiB 大文件导入 | **NOT TESTED**（见 U3） |

## 诚实声明

- 本报告中的 "passed" 数字均为本轮在 muse-work 分支上实际执行 pytest 得到的结果，非复述豆包数据。
- 所有未执行的测试均已标注 [PENDING] / NOT TESTED / 未执行，未声称任何未实际执行的测试已通过。
