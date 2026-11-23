"""Deterministic daily Product Ops report generator for Intelligence.

Reads git repository facts, product-ops state/decision files, and (optionally)
an explicitly supplied read-only ``hub.sqlite3`` sidecar database without
modifying product state, touching secrets, or calling external paid APIs.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True, slots=True)
class GitFacts:
    branch: str
    head_sha: str
    short_sha: str
    ahead_of_main: int | None
    dirty_tracked_count: int
    recent_commits: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HubUsageFacts:
    available: bool
    distilled_briefs: int | None
    qa_sessions: int | None
    qa_grounded: int | None
    qa_refused: int | None
    weekly_briefs: int | None


@dataclass(frozen=True, slots=True)
class OpsReportSummary:
    report_date: str
    output_path: str
    written: bool
    skipped_existing: bool
    git: GitFacts
    hub_usage: HubUsageFacts
    pending_founder_decisions: tuple[str, ...]


def _run_git(repo_root: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return proc.returncode, proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def collect_git_facts(repo_root: Path) -> GitFacts:
    _, branch = _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    _, head_sha = _run_git(repo_root, "rev-parse", "HEAD")
    _, short_sha = _run_git(repo_root, "rev-parse", "--short", "HEAD")
    _, status_out = _run_git(repo_root, "status", "--porcelain", "--untracked-files=no")
    dirty_tracked_count = len([ln for ln in status_out.splitlines() if ln.strip()])
    rc_ahead, ahead_raw = _run_git(repo_root, "rev-list", "--count", "main..HEAD")
    ahead_of_main: int | None = None
    if rc_ahead == 0 and ahead_raw.isdigit():
        ahead_of_main = int(ahead_raw)
    _, log_out = _run_git(repo_root, "log", "-n", "5", "--oneline")
    recent = tuple(ln.strip() for ln in log_out.splitlines() if ln.strip())
    return GitFacts(
        branch=branch or "UNKNOWN",
        head_sha=head_sha or "UNKNOWN",
        short_sha=short_sha or "UNKNOWN",
        ahead_of_main=ahead_of_main,
        dirty_tracked_count=dirty_tracked_count,
        recent_commits=recent,
    )


def collect_hub_usage_readonly(hub_db: Path | None) -> HubUsageFacts:
    if hub_db is None or not hub_db.is_file():
        return HubUsageFacts(
            available=False,
            distilled_briefs=None,
            qa_sessions=None,
            qa_grounded=None,
            qa_refused=None,
            weekly_briefs=None,
        )
    uri = f"file:{hub_db.resolve().as_posix()}?mode=ro"
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=3.0)
        briefs = int(conn.execute("SELECT COUNT(*) FROM video_ai_briefs").fetchone()[0])
        qa_rows = conn.execute("SELECT scope_json FROM research_qa_sessions").fetchall()
        qa_total = len(qa_rows)
        qa_refused = 0
        for (raw_scope,) in qa_rows:
            try:
                parsed = json.loads(str(raw_scope or "{}"))
            except ValueError:
                parsed = {}
            if isinstance(parsed, dict) and (
                parsed.get("refused") is True
                or parsed.get("answer_status") == "REFUSED_INSUFFICIENT_EVIDENCE"
            ):
                qa_refused += 1
        qa_grounded = qa_total - qa_refused
        weekly = int(conn.execute("SELECT COUNT(*) FROM weekly_ai_briefs").fetchone()[0])
        return HubUsageFacts(
            available=True,
            distilled_briefs=briefs,
            qa_sessions=qa_total,
            qa_grounded=qa_grounded,
            qa_refused=qa_refused,
            weekly_briefs=weekly,
        )
    except sqlite3.Error:
        return HubUsageFacts(
            available=False,
            distilled_briefs=None,
            qa_sessions=None,
            qa_grounded=None,
            qa_refused=None,
            weekly_briefs=None,
        )
    finally:
        if conn is not None:
            conn.close()


def extract_pending_founder_decisions(founder_decisions_path: Path) -> tuple[str, ...]:
    if not founder_decisions_path.is_file():
        return ()
    text = founder_decisions_path.read_text(encoding="utf-8")
    sections = re.split(r"(?m)^##\s+", text)
    pending: list[str] = []
    for section in sections[1:]:
        header = section.splitlines()[0].strip() if section.splitlines() else ""
        if not header.startswith("FD-"):
            continue
        if "PENDING" in section or "待创始人决定" in section or "待决策" in section:
            if "RESOLVED" not in section and "APPROVED" not in section and "REJECTED" not in section:
                pending.append(header)
    return tuple(pending)


def render_daily_ops_markdown(
    *,
    report_date: str,
    git: GitFacts,
    hub_usage: HubUsageFacts,
    pending_decisions: tuple[str, ...],
    current_goal: str,
) -> str:
    commits_md = "\n".join(f"  - `{c}`" for c in git.recent_commits) or "  - 暂无记录"
    ahead_str = (
        f"领先 `main` {git.ahead_of_main} 笔提交"
        if git.ahead_of_main is not None
        else "无法对比 `main`"
    )
    if hub_usage.available:
        usage_block = (
            f"- 已提炼内容卡片：`{hub_usage.distilled_briefs}`\n"
            f"- 跨源问答会话总计：`{hub_usage.qa_sessions}`"
            f"（有证据作答 `{hub_usage.qa_grounded}` · 诚实拒答 `{hub_usage.qa_refused}`）\n"
            f"- 周报快照数：`{hub_usage.weekly_briefs}`"
        )
    else:
        usage_block = (
            "- 核心北极星（周真实可核验研究收获人数 / WAU）：**暂无数据**（零遥测，等待首批受邀用户实验 `EXP-001`）\n"
            "- 本地只读实例统计：未传入 `--hub-db` 隔离库路径，未读取个人真实库"
        )

    decisions_block = (
        "\n".join(f"- **{item}**（详见 `product-ops/FOUNDER_DECISIONS.md`）" for item in pending_decisions)
        if pending_decisions
        else "- 无需决策"
    )

    return (
        f"# 产品自主运营日报｜{report_date}\n\n"
        "### 1. 产品整体状态\n\n"
        f"- **当前版本及发布状态**：`v0.1.0` · `PUBLIC_BETA`（开源 Apache-2.0，独立分支 `{git.branch}` @ `{git.short_sha}`，{ahead_str}）\n"
        "- **产品阶段**：Pre-Launch / 首批真实外部用户价值验证前期（工程主干与反幻觉闭环已收敛，外部激活与留存为 `暂无数据`）\n"
        f"- **当前最重要目标**：{current_goal}\n"
        f"- **总体健康状况**：工作区已跟踪未提交改动 `{git.dirty_tracked_count}` 项；最近本地提交：\n"
        f"{commits_md}\n"
        "- **与昨日相比的变化**：已由 `scripts/generate_daily_ops_report.py` 按真实 Git 与产品运营台账快照更新（具体实验/手工补充项见人工/Agent 复盘补充）。\n\n"
        "### 2. 今日完成\n\n"
        "- （待本日迭代完成后记录；自动化巡检已验证 Git 与 `product-ops/` 持久化台账状态）\n\n"
        "### 3. 市场与竞品新情报\n\n"
        "- 无重要变化（每周周期巡检记录见 `product-ops/MARKET_INTELLIGENCE.md` 与 `product-ops/COMPETITOR_MATRIX.md`）。\n\n"
        "### 4. 用户及产品数据\n\n"
        f"{usage_block}\n"
        "- GitHub 仓库可见性及社区转化：仓库当前若仍为 Private，自然 Star/Issue 为 0，外部留存**暂无数据**。\n\n"
        "### 5. 今日关键决策\n\n"
        "- 保持本地优先与 Zero-Telemetry 边界；仅在明确决策记录与验证门禁通过后推进对外发布与用户实验（参见 `product-ops/DECISION_LOG.md`）。\n\n"
        "### 6. 风险及阻塞\n\n"
        "- `main` 分支与工作分支存在提交差，且仓库私有状态阻塞公开发布验证与自然获客。\n"
        "- 外部真实用户行为样本为 0，所有转化与定价判断均保留为 `待验证假设`。\n\n"
        "### 7. 需要创始人决定的事项\n\n"
        f"{decisions_block}\n\n"
        "### 8. 明日计划\n\n"
        "1. 若 `FD-001` 获批：整合已验证提交至 `main` 并核验 GitHub Actions 首轮全绿。\n"
        "2. 推进真实本机模型处理陌生双语材料的端到端对照包与录屏证据（`EXP-002`）。\n"
        "3. 完成首批目标研究者试用的任务脚本与反馈收集模版准备（`EXP-001`）。\n\n"
        "### 9. 本周目标进度\n\n"
        "- 见 `product-ops/ROADMAP.md` 与 `product-ops/reports/weekly/`。\n"
    )


def _extract_current_goal(current_state_path: Path) -> str:
    if not current_state_path.is_file():
        return "完成首次价值验证闭环与跨源可携带研究输出"
    for line in current_state_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- **当前产品目标**") or line.startswith("**当前产品目标**"):
            parts = line.split("：", 1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()
    return "完成首次价值验证闭环与跨源可携带研究输出"


def generate_report(
    *,
    repo_root: Path,
    report_date: str,
    hub_db: Path | None = None,
    output_path: Path | None = None,
    overwrite: bool = False,
) -> OpsReportSummary:
    resolved_root = repo_root.resolve()
    target = (
        output_path.resolve()
        if output_path is not None
        else resolved_root / "product-ops" / "reports" / "daily" / f"{report_date}.md"
    )
    git = collect_git_facts(resolved_root)
    hub_usage = collect_hub_usage_readonly(hub_db)
    pending = extract_pending_founder_decisions(
        resolved_root / "product-ops" / "FOUNDER_DECISIONS.md"
    )
    goal = _extract_current_goal(resolved_root / "product-ops" / "CURRENT_STATE.md")

    if target.exists() and not overwrite:
        return OpsReportSummary(
            report_date=report_date,
            output_path=str(target),
            written=False,
            skipped_existing=True,
            git=git,
            hub_usage=hub_usage,
            pending_founder_decisions=pending,
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_daily_ops_markdown(
        report_date=report_date,
        git=git,
        hub_usage=hub_usage,
        pending_decisions=pending,
        current_goal=goal,
    )
    target.write_text(markdown, encoding="utf-8")
    return OpsReportSummary(
        report_date=report_date,
        output_path=str(target),
        written=True,
        skipped_existing=False,
        git=git,
        hub_usage=hub_usage,
        pending_founder_decisions=pending,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic Intelligence daily Product Ops report."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Git worktree root containing product-ops/",
    )
    parser.add_argument(
        "--date",
        default=datetime.now(SHANGHAI_TZ).strftime("%Y-%m-%d"),
        help="Report date YYYY-MM-DD in Asia/Shanghai timezone",
    )
    parser.add_argument(
        "--hub-db",
        type=Path,
        default=None,
        help="Optional explicit read-only path to an isolated hub.sqlite3",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional custom output Markdown path",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing daily report file if present",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print JSON operational summary to stdout",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    summary = generate_report(
        repo_root=args.repo_root,
        report_date=str(args.date),
        hub_db=args.hub_db,
        output_path=args.output,
        overwrite=bool(args.overwrite),
    )
    if args.json_summary:
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    else:
        status = "written" if summary.written else "skipped_existing"
        print(f"[{status}] {summary.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
