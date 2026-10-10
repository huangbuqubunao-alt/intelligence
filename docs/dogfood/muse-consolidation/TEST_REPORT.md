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
| `tests/unit/test_backup_restore.py` | 同上 | **28 passed**（60.96s→42.97s，含 2 个新增回归测试 `test_backup_is_not_blocked_by_completed_no_new_intelligence`、`test_backup_is_not_blocked_by_uninvoked_waiting_model`） |
| `tests/integration/test_runtime_composition.py` | 同上 | **10 passed**（含新增回归测试 `test_local_distillation_transport_is_production_authorized`） |
| 两套件合并 | 同上 | **38 passed，0 failed** |

结论：Bug2（本地提炼生产资格）、Bug3（备份豁免）的产品代码改动与其回归测试在本环境全部通过。

## 待填项

| 项 | 状态 |
|---|---|
| 后端全量套件（`pytest tests/`，不含 e2e） | **[RUNNING]** muse-work 分支全量运行中（后台）；main 基线待跑。豆包报告的 2 个失败已在 muse-work 上单独复核：`test_task_owned_child_stops_when_application_parent_dies` 与 `test_serve_api_sigterm_drains_active_tracking_before_exit` 单独运行时均通过，确认为进程时序类环境敏感测试，非本次改动引入 |
| 前端 vitest（`App.test.tsx`） | **111 passed**（2026-10-11 实测：108 个原有 + 豆包新增 2 个 + Muse 新增导入回归测试 1 个）。另 `tsc -b` 类型检查通过、`vite build` 生产构建成功 |
| `npm run build`（生产构建） | **通过**（`tsc -b` + `vite build`，dist 输出正常） |
| 真实 GUI 回归（导航 hash、提炼、备份三条路径） | **未执行** —— 本环境无浏览器自动化能力；豆包轮次的 GUI 验证记录保留在其分支备查，本轮不重复声称 |
| macOS 特有项（Keychain、APFS clonefile、原生文件选择器） | **NOT TESTED**（本环境为 Linux，相关分支不可达） |
| 本地转写模型（mlx-whisper）链路 | **NOT TESTED**（模型未配置，见 U1） |
| 2 GiB 大文件导入 | **NOT TESTED**（见 U3） |

## 诚实声明

- 本报告中的 "passed" 数字均为本轮在 muse-work 分支上实际执行 pytest 得到的结果，非复述豆包数据。
- 所有未执行的测试均已标注 [PENDING] / NOT TESTED / 未执行，未声称任何未实际执行的测试已通过。
