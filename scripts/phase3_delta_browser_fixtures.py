"""Build browser cases from real SQLite authority, without models or real data.

Run from this worktree: PYTHONPATH=src python scripts/phase3_delta_browser_fixtures.py
The browser runner consumes /tmp/phase3-delta-fixtures.json by default.
"""

from __future__ import annotations

import argparse
import json
import runpy
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from youtube_intel import knowledge_delta
from youtube_intel.knowledge_delta import KnowledgeDeltaService
from youtube_intel.state import (
    IntelligenceState,
    SQLiteStateRepository,
    TopicAssociationKind,
)
from youtube_intel.topic import TopicApplicationService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("/tmp/phase3-delta-fixtures.json")
    )
    output = parser.parse_args().output
    root = Path(__file__).resolve().parents[1]
    fixture = runpy.run_path(
        str(root / "tests/integration/test_v1x_knowledge_delta.py")
    )
    now, start = fixture["NOW"], fixture["START"]
    cases: dict[str, object] = {}
    with TemporaryDirectory(prefix="phase3-browser-authority-") as temp:
        for name in (
            "empty",
            "one",
            "many",
            "mixed",
            "revision_heavy",
            "source_failures",
            "recovery",
            "boundary",
            "partial",
            "unavailable",
        ):
            repository = SQLiteStateRepository(Path(temp) / f"{name}.sqlite3")
            repository.initialize(now=now)
            if name in {"one", "mixed", "revision_heavy"}:
                fixture["content"](repository, "content:fixture", now)
            if name == "many":
                connection = repository._connect()
                try:
                    connection.executemany(
                        "INSERT INTO videos (video_id, channel_id, title, pipeline_status, pipeline_version, discovered_at, updated_at, completed_at) "
                        "VALUES (?, 'channel', ?, 'COMPLETE', 'fixture', ?, ?, ?)",
                        [
                            (
                                f"many-{i:04}",
                                "很长的原始来源标题 " * 40,
                                start.isoformat(),
                                now.isoformat(),
                                now.isoformat(),
                            )
                            for i in range(1000)
                        ],
                    )
                finally:
                    connection.close()
            if name in {"mixed", "revision_heavy"}:
                support = (fixture["evidence"](repository, "content:fixture"),)
                fixture["revision"](
                    repository, "intelligence:fixture", 1, start, support
                )
                for number in range(2, 13 if name == "revision_heavy" else 3):
                    fixture["revision"](
                        repository,
                        "intelligence:fixture",
                        number,
                        now,
                        support,
                        IntelligenceState.CONFIRMED
                        if number == 2
                        else IntelligenceState.UPDATED,
                    )
                fixture["revision"](
                    repository,
                    "intelligence:older",
                    1,
                    start - timedelta(microseconds=1),
                    support,
                )
                fixture["revision"](
                    repository,
                    "intelligence:older",
                    2,
                    now,
                    support,
                    IntelligenceState.DISPUTED,
                )
                topic_service = TopicApplicationService(repository, now=lambda: now)
                topic = topic_service.create_topic(
                    command_id="fixture", name="真实关联主题 / Linked Topic"
                )
                topic_service.associate_intelligence(
                    topic_id=topic.topic_id,
                    intelligence_id="intelligence:fixture",
                    kind=TopicAssociationKind.NEW_INFORMATION,
                )
            if name in {"mixed", "source_failures", "recovery"}:
                fixture["source"](repository)
                fixture["source_run"](repository, "failed-first", start)
                fixture["source_run"](
                    repository, "failed-second", start + timedelta(hours=1)
                )
                if name == "recovery":
                    fixture["source_run"](
                        repository, "recovered", now - timedelta(hours=1), success=True
                    )
                    fixture["source_run"](
                        repository, "normal-success", now, success=True
                    )
            if name == "boundary":
                for identity, at in [
                    ("before", start - timedelta(microseconds=1)),
                    ("at-start", start),
                    ("at-end", now),
                    ("future", now + timedelta(microseconds=1)),
                ]:
                    fixture["content"](repository, identity, at)
            if name == "partial":
                with patch.object(
                    knowledge_delta, "_TOPICS", "SELECT missing FROM no_table"
                ):
                    cases[name] = (
                        KnowledgeDeltaService(repository, now=lambda: now)
                        .read()
                        .as_dict()
                    )
            elif name == "unavailable":
                with patch.object(
                    repository,
                    "_connect",
                    side_effect=knowledge_delta.StateStoreError("fixture unavailable"),
                ):
                    cases[name] = (
                        KnowledgeDeltaService(repository, now=lambda: now)
                        .read()
                        .as_dict()
                    )
            else:
                cases[name] = (
                    KnowledgeDeltaService(repository, now=lambda: now).read().as_dict()
                )
    output.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(cases)} real-SQLite browser fixtures -> {output}")


if __name__ == "__main__":
    main()
