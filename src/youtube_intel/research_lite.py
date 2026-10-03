"""Bounded deterministic library research. No provider, ingestion or promotion."""

from __future__ import annotations

import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from typing import Callable, Literal

from pydantic import ValidationError

from youtube_intel.domain import Availability
from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
)
from youtube_intel.research_contract import (
    CANDIDATE_LIMIT,
    CONTRACT,
    MAX_EVIDENCE,
    MAX_INTELLIGENCE,
    ResearchContent,
    ResearchEvidence,
    ResearchIntelligence,
    ResearchPacket,
    ResearchRequest,
    ResearchUnresolved,
    canonical,
    digest,
    semantic_identity,
)
from youtube_intel.research_diff import ResearchDiff, project_diff
from youtube_intel.state import (
    SQLiteStateRepository,
    VerifiedEvidenceText,
    build_evidence_id,
)

RESEARCH_AUTHORITY_TABLES = frozenset({"research_items", "research_results"})
_STOP_WORDS = frozenset("a an the is are was were to of in on for and or what how why can do does i my this that with from".split())


class ResearchRejected(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _timestamp(value: str) -> datetime:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("Research requires aware timestamps")
    return instant.astimezone(UTC)


def _terms(question: str) -> tuple[str, ...]:
    # Bounded lexical retrieval, not semantic relevance or a truth classifier.
    terms: list[str] = []
    for word in re.findall(r"[\u3400-\u9fff]+|[^\W_]+", question.casefold()):
        if word in _STOP_WORDS:
            continue
        if re.fullmatch(r"[\u3400-\u9fff]+", word) and len(word) > 2:
            terms.extend(word[i:i + 2] for i in range(len(word) - 1))
        else:
            terms.append(word)
    return tuple(dict.fromkeys(terms))[:32]


@dataclass(frozen=True)
class ResearchRead:
    result_identity: str
    packet: ResearchPacket
    is_current: bool | None = None

    def as_dict(self) -> dict[str, object]:
        return {"result_identity": self.result_identity, "provenance_status": "VERIFIED",
                "packet": self.packet.model_dump(mode="json")}


class ResearchLiteService:
    def __init__(self, repository: SQLiteStateRepository, *, now: Callable[[], datetime] | None = None) -> None:
        self._repository = repository
        self._now = now or (lambda: datetime.now(UTC))
        self._intelligence_reader = AuthoritativeIntelligenceReader(repository)

    def _scope(self, connection: sqlite3.Connection, ids: list[str]) -> list[ResearchContent]:
        marks = ",".join("?" for _ in ids)
        rows = connection.execute(
            f"SELECT video_id, title, availability FROM videos WHERE video_id IN ({marks}) ORDER BY video_id",
            ids,
        ).fetchall()
        if len(rows) != len(ids):
            raise ResearchRejected("RESEARCH_SCOPE_NOT_FOUND")
        if any(row["availability"] != Availability.PUBLIC.value for row in rows):
            raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE")
        return [ResearchContent(content_id=row["video_id"], title=None if row["title"] is None else row["title"][:240]) for row in rows]

    def _evidence_record(self, row: sqlite3.Row | None, verified: VerifiedEvidenceText | None, evidence_id: str, ids: list[str]) -> ResearchEvidence:
        if row is None or verified is None or row["video_id"] not in ids:
            raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE")
        evidence = self._repository._evidence_from_row(row)
        expected_id = build_evidence_id(
            video_id=evidence.video_id, artifact_id=evidence.artifact_id,
            start_ms=evidence.start_ms, end_ms=evidence.end_ms,
            lineage_kind=evidence.lineage_kind, role=evidence.role,
        )
        if expected_id != evidence_id or evidence.lineage_kind.value not in {"ORIGINAL_TRANSCRIPT", "EXTRACTION"}:
            raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE")
        return ResearchEvidence(
            evidence_id=evidence_id, content_id=evidence.video_id,
            artifact_id=evidence.artifact_id, excerpt=verified.excerpt,
            excerpt_hash=verified.excerpt_hash, timed_transcript_hash=verified.timed_transcript_hash,
            start_ms=verified.start_ms, end_ms=verified.end_ms,
            source_language=evidence.language, lineage_kind="ORIGINAL_TRANSCRIPT" if evidence.lineage_kind.value == "ORIGINAL_TRANSCRIPT" else "EXTRACTION",
            role=evidence.role.value, created_at=evidence.created_at.isoformat(),
        )

    def _evidence_many(self, connection: sqlite3.Connection, evidence_ids: list[str], ids: list[str]) -> list[ResearchEvidence]:
        if not evidence_ids:
            return []
        try:
            verified = self._repository.resolve_verified_evidence_text_batch_in_transaction(connection, tuple(evidence_ids))
            marks = ",".join("?" for _ in evidence_ids)
            rows = {r["evidence_id"]: r for r in connection.execute(f"SELECT * FROM evidence WHERE evidence_id IN ({marks})", evidence_ids)}
            return [self._evidence_record(rows.get(eid), verified.get(eid), eid, ids) for eid in evidence_ids]
        except (ValueError, TypeError) as error:
            raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE") from error

    def assemble(self, request: ResearchRequest, *, output_language: Literal["zh-CN", "en"]) -> ResearchRead:
        research_id = semantic_identity(request, output_language)
        now = self._now()
        if now.tzinfo is None:
            raise ResearchRejected("RESEARCH_EXECUTION_FAILED")
        assembled_at = now.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
        terms = _terms(request.question)
        connection = self._repository._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            scope = self._scope(connection, request.content_ids)
            connection.create_function("research_score", 1, lambda text: sum(term in str(text).casefold() for term in terms), deterministic=True)
            marks = ",".join("?" for _ in request.content_ids)
            sql = f"FROM evidence e JOIN evidence_text_bindings b USING(evidence_id) WHERE e.video_id IN ({marks}) AND research_score(b.excerpt)>0"
            count = int(connection.execute("SELECT count(*) " + sql, request.content_ids).fetchone()[0])
            rows = connection.execute(
                "SELECT e.evidence_id, length(b.excerpt) AS excerpt_length " + sql +
                " ORDER BY research_score(b.excerpt) DESC, e.video_id, e.start_ms, e.end_ms, e.evidence_id LIMIT ?",
                [*request.content_ids, CANDIDATE_LIMIT],
            ).fetchall()
            evidence_ids = []
            for row in rows:
                if row["excerpt_length"] <= 4000:
                    evidence_ids.append(row["evidence_id"])
                if len(evidence_ids) == MAX_EVIDENCE:
                    break
            matching_evidence_count = len(evidence_ids)
            intelligence_sql = (
                f"FROM distillation_cards c JOIN intelligences i ON i.current_revision_id=c.revision_id "
                f"WHERE c.video_id IN ({marks}) AND (research_score(c.core_conclusion)>0 OR EXISTS ("
                "SELECT 1 FROM intelligence_revision_evidence re JOIN evidence_text_bindings b USING(evidence_id) "
                "WHERE re.revision_id=c.revision_id AND research_score(b.excerpt)>0))"
            )
            intelligence_count = int(connection.execute("SELECT count(*) " + intelligence_sql, request.content_ids).fetchone()[0])
            intelligence_rows = connection.execute(
                "SELECT i.intelligence_id " + intelligence_sql +
                " ORDER BY research_score(c.core_conclusion) DESC, c.video_id, i.intelligence_id LIMIT ?",
                [*request.content_ids, MAX_INTELLIGENCE],
            ).fetchall()
            findings = []
            for row in intelligence_rows:
                finding = self._intelligence(row["intelligence_id"], request.content_ids, assembled_at=assembled_at)
                additional = [eid for eid in finding.evidence_ids if eid not in evidence_ids]
                if len(evidence_ids) + len(additional) > MAX_EVIDENCE:
                    continue  # Omit the whole interpretation; never amputate its provenance.
                evidence_ids.extend(additional)
                findings.append(finding)
            evidence = self._evidence_many(connection, evidence_ids, request.content_ids)
            truncated = count > matching_evidence_count or intelligence_count > len(findings)
            unresolved: list[ResearchUnresolved] = ["NO_SYNTHESIS", "LEXICAL_RETRIEVAL"]
            if truncated:
                unresolved.append("BOUNDED_PACKET")
            if not evidence:
                unresolved.append("NO_MATCHING_EVIDENCE")
            packet = ResearchPacket(
                research_id=research_id, execution_id=uuid.uuid4().hex,
                execution_number=1 + int(connection.execute("SELECT coalesce(max(execution_number),0) FROM research_results WHERE research_id=?", (research_id,)).fetchone()[0]),
                question=request.question, output_language=output_language, assembled_at=assembled_at,
                scope=scope, material_status="EVIDENCE_AVAILABLE" if evidence else "INSUFFICIENT_MATERIAL",
                evidence=evidence, intelligence=findings, evidence_candidates=count, intelligence_candidates=intelligence_count,
                retrieval_truncated=truncated,
                unresolved=unresolved,
            )
            result = self._persist(connection, request, packet)
            connection.execute("COMMIT")
            return result
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def _intelligence(self, intelligence_id: str, ids: list[str], revision_id: str | None = None, *, assembled_at: str) -> ResearchIntelligence:
        try:
            card = (self._intelligence_reader.read_current_card(intelligence_id) if revision_id is None
                    else self._intelligence_reader.read_recorded_card(intelligence_id, revision_id))
            if card.video_id not in ids:
                raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE")
            revision = self._repository.get_intelligence_revision(card.verified.revision_id)
            if revision is None or revision.created_at > _timestamp(assembled_at):
                raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE")
            relations = self._repository.list_intelligence_revision_evidence_relations(card.verified.revision_id)
            return ResearchIntelligence(
                intelligence_id=intelligence_id, revision_id=card.verified.revision_id,
                content_id=card.video_id, source_id=card.source_id, conclusion=card.core_conclusion,
                claim_kind=card.verified.claim_kind.value, state=card.verified.state.value,
                evidence_ids=list(card.verified.evidence_ids),
                stances=[None if r.stance is None else r.stance.value for r in relations],
            )
        except (IntelligenceReadRejected, ValueError) as error:
            raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE") from error

    def _persist(self, connection: sqlite3.Connection, request: ResearchRequest, packet: ResearchPacket) -> ResearchRead:
        payload = packet.model_dump(mode="json")
        payload_hash = digest(payload)
        result_identity = digest({"contract": CONTRACT, "research_id": packet.research_id,
                                  "execution_id": packet.execution_id, "payload_hash": payload_hash})
        connection.execute(
            "INSERT INTO research_items VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(research_id) DO NOTHING",
            (packet.research_id, packet.question, canonical(request.content_ids), packet.output_language,
             CONTRACT, result_identity, packet.assembled_at),
        )
        connection.execute(
            "INSERT INTO research_results VALUES (?, ?, ?, ?, ?, ?, ?)",
            (result_identity, packet.research_id, packet.execution_id, canonical(payload), payload_hash, packet.assembled_at, packet.execution_number),
        )
        connection.execute("UPDATE research_items SET current_result_identity=? WHERE research_id=?", (result_identity, packet.research_id))
        row = connection.execute("SELECT * FROM research_results WHERE result_identity=?", (result_identity,)).fetchone()
        assert row is not None
        return self.verify_row(connection, row)

    def verify_row(self, connection: sqlite3.Connection, row: sqlite3.Row, *,
                   evidence_cache: dict[str, ResearchEvidence] | None = None) -> ResearchRead:
        """Shared restart/backup validator. Hash shape alone never grants trust."""
        try:
            packet = ResearchPacket.model_validate_json(row["payload_json"])
            payload = packet.model_dump(mode="json")
            request = ResearchRequest(question=packet.question, content_ids=[c.content_id for c in packet.scope])
            item = connection.execute("SELECT * FROM research_items WHERE research_id=?", (packet.research_id,)).fetchone()
            payload_hash = digest(payload)
            expected_identity = digest({"contract": CONTRACT, "research_id": packet.research_id,
                                        "execution_id": packet.execution_id, "payload_hash": payload_hash})
            if (
                item is None or semantic_identity(request, packet.output_language) != packet.research_id
                or row["research_id"] != packet.research_id or row["execution_id"] != packet.execution_id
                or row["result_identity"] != expected_identity or row["payload_hash"] != payload_hash
                or row["execution_number"] != packet.execution_number
                or row["payload_json"] != canonical(payload) or row["assembled_at"] != packet.assembled_at
                or item["question"] != request.question or item["scope_json"] != canonical(request.content_ids)
                or item["output_language"] != packet.output_language or item["contract"] != CONTRACT
                or _timestamp(item["created_at"]) > _timestamp(packet.assembled_at)
                or re.fullmatch(r"[a-f0-9]{32}", packet.execution_id) is None
                or [c.content_id for c in packet.scope] != request.content_ids
                or len({e.evidence_id for e in packet.evidence}) != len(packet.evidence)
                or len({f.intelligence_id for f in packet.intelligence}) != len(packet.intelligence)
                or packet.intelligence_candidates < len(packet.intelligence)
                or packet.material_status != ("EVIDENCE_AVAILABLE" if packet.evidence else "INSUFFICIENT_MATERIAL")
            ):
                raise ValueError("Research identity or structure mismatch")
            expected_unresolved = ["NO_SYNTHESIS", "LEXICAL_RETRIEVAL", *(["BOUNDED_PACKET"] if packet.retrieval_truncated else []), *([] if packet.evidence else ["NO_MATCHING_EVIDENCE"])]
            if packet.unresolved != expected_unresolved:
                raise ValueError("Research status mismatch")
        except (ValueError, TypeError, KeyError) as error:
            raise ResearchRejected("RESEARCH_CORRUPTED_RESULT") from error
        # Resolve authority again. Never remove a bad citation and retain VERIFIED.
        scope = self._scope(connection, request.content_ids)
        # Titles are immutable execution context, not claims. A later metadata
        # refresh must not destroy a correctly bound Research artifact.
        if [c.content_id for c in scope] != request.content_ids:
            raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE")
        if evidence_cache is None:
            actual_evidence = self._evidence_many(connection, [e.evidence_id for e in packet.evidence], request.content_ids)
        else:
            actual_evidence = [evidence_cache[e.evidence_id] for e in packet.evidence]
        for reference, actual in zip(packet.evidence, actual_evidence, strict=True):
            if actual.content_id not in request.content_ids or actual != reference or _timestamp(actual.created_at) > _timestamp(packet.assembled_at):
                raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE")
        evidence_by_id = {e.evidence_id: e for e in packet.evidence}
        for finding in packet.intelligence:
            actual_finding = self._intelligence(finding.intelligence_id, request.content_ids, finding.revision_id, assembled_at=packet.assembled_at)
            if actual_finding != finding or any(
                eid not in evidence_by_id or evidence_by_id[eid].content_id != finding.content_id
                for eid in finding.evidence_ids
            ):
                raise ResearchRejected("RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE")
        return ResearchRead(result_identity=expected_identity, packet=packet)

    def read(self, research_id: str) -> ResearchRead:
        connection = self._repository._connect(read_only=True)
        try:
            connection.execute("BEGIN")
            row = connection.execute(
                "SELECT r.* FROM research_items i LEFT JOIN research_results r ON r.result_identity=i.current_result_identity AND r.research_id=i.research_id WHERE i.research_id=?",
                (research_id,),
            ).fetchone()
            if row is None:
                raise ResearchRejected("RESEARCH_NOT_FOUND")
            if row["result_identity"] is None:
                raise ResearchRejected("RESEARCH_CORRUPTED_RESULT")
            latest = connection.execute("SELECT max(execution_number) FROM research_results WHERE research_id=?", (research_id,)).fetchone()[0]
            if row["execution_number"] != latest:
                raise ResearchRejected("RESEARCH_CORRUPTED_RESULT")
            return self.verify_row(connection, row)
        except ResearchRejected:
            raise
        except (ValueError, sqlite3.Error) as error:
            raise ResearchRejected("RESEARCH_CORRUPTED_RESULT") from error
        finally:
            connection.close()

    def read_revision(self, research_id: str, revision_id: str) -> ResearchRead:
        """A revision id is the existing immutable result identity, never current."""
        connection = self._repository._connect(read_only=True)
        try:
            connection.execute("BEGIN")
            row = connection.execute(
                "SELECT * FROM research_results WHERE research_id=? AND result_identity=?",
                (research_id, revision_id),
            ).fetchone()
            if row is None:
                raise ResearchRejected("RESEARCH_REVISION_NOT_FOUND")
            result = self.verify_row(connection, row)
            is_current = bool(connection.execute(
                "SELECT current_result_identity=? AND NOT EXISTS (SELECT 1 FROM research_results "
                "WHERE research_id=? AND execution_number>?) FROM research_items WHERE research_id=?",
                (revision_id, research_id, row["execution_number"], research_id),
            ).fetchone()[0])
            return ResearchRead(result.result_identity, result.packet, is_current=is_current)
        except ResearchRejected:
            raise
        except (ValueError, sqlite3.Error) as error:
            raise ResearchRejected("RESEARCH_CORRUPTED_RESULT") from error
        finally:
            connection.close()

    def diff(self, research_id: str, base_revision: str, target_revision: str) -> ResearchDiff:
        """Read two trusted authorities in one snapshot; never consult current."""
        if any(re.fullmatch(r"[a-f0-9]{64}", value) is None for value in (research_id, base_revision, target_revision)):
            raise ResearchRejected("RESEARCH_DIFF_INVALID_REQUEST")
        connection = self._repository._connect(read_only=True)
        try:
            connection.execute("BEGIN")
            if connection.execute("SELECT 1 FROM research_items WHERE research_id=?", (research_id,)).fetchone() is None:
                raise ResearchRejected("RESEARCH_NOT_FOUND")
            trusted: dict[str, ResearchRead] = {}
            for side, revision_id in (("BASE", base_revision), ("TARGET", target_revision)):
                if revision_id in trusted:
                    continue
                row = connection.execute("SELECT * FROM research_results WHERE result_identity=?", (revision_id,)).fetchone()
                if row is None:
                    raise ResearchRejected(f"RESEARCH_DIFF_{side}_NOT_FOUND")
                if row["research_id"] != research_id:
                    raise ResearchRejected("RESEARCH_DIFF_WRONG_RESEARCH")
                try:
                    ResearchPacket.model_validate_json(row["payload_json"])
                except ValidationError as error:
                    if any(e["loc"] == ("contract",) and e["type"] == "literal_error" for e in error.errors()):
                        raise ResearchRejected("RESEARCH_DIFF_INCOMPATIBLE_CONTRACT") from None
                    raise ResearchRejected("RESEARCH_DIFF_UNTRUSTED_REVISION") from None
                try:
                    trusted[revision_id] = self.verify_row(connection, row)
                except ResearchRejected:
                    raise ResearchRejected("RESEARCH_DIFF_UNTRUSTED_REVISION") from None
            return project_diff(base_revision, trusted[base_revision].packet, target_revision, trusted[target_revision].packet)
        except ResearchRejected:
            raise
        except (ValueError, TypeError, KeyError, sqlite3.Error):
            raise ResearchRejected("RESEARCH_DIFF_UNTRUSTED_REVISION") from None
        finally:
            connection.close()

    def history(self, research_id: str, *, cursor: str | None = None, limit: int = 25) -> dict[str, object]:
        """Bounded trusted previous revisions, ordered by immutable execution sequence.

        Cursor pins the initial current sequence so concurrent reruns do not shift
        pages. Unavailable counts describe this page only, never a trusted total.
        """
        if not 1 <= limit <= 25:
            raise ResearchRejected("RESEARCH_INVALID_CURSOR")
        connection = self._repository._connect(read_only=True)
        try:
            connection.execute("BEGIN")
            item = connection.execute("SELECT * FROM research_items WHERE research_id=?", (research_id,)).fetchone()
            if item is None:
                raise ResearchRejected("RESEARCH_NOT_FOUND")
            latest = connection.execute(
                "SELECT max(execution_number) FROM research_results WHERE research_id=?", (research_id,)
            ).fetchone()[0]
            current = connection.execute(
                "SELECT * FROM research_results WHERE research_id=? AND result_identity=?",
                (research_id, item["current_result_identity"]),
            ).fetchone()
            current_id = None
            if current is not None and current["execution_number"] == latest:
                try:
                    current_id = self.verify_row(connection, current).result_identity
                except ResearchRejected:
                    pass  # A broken current result does not conceal valid older authority.
            anchor = int(latest or 0)
            before = anchor + 1
            if cursor is not None:
                if len(cursor) > 120 or re.fullmatch(r"[a-f0-9]{64}:[0-9]{1,12}:[0-9]{1,12}", cursor) is None:
                    raise ResearchRejected("RESEARCH_INVALID_CURSOR")
                owner, raw_anchor, raw_before = cursor.split(":")
                anchor, before = int(raw_anchor), int(raw_before)
                if owner != research_id or not 0 < before <= anchor <= int(latest or 0):
                    raise ResearchRejected("RESEARCH_INVALID_CURSOR")
            rows = connection.execute(
                "SELECT * FROM research_results WHERE research_id=? AND execution_number<=? "
                "AND execution_number<? AND result_identity!=? ORDER BY execution_number DESC LIMIT ?",
                (research_id, anchor, before, current_id or "", limit + 1),
            ).fetchall()
            has_more = len(rows) > limit
            rows = rows[:limit]
            # Resolve shared Evidence across the bounded page once. Packet parsing
            # here grants no trust; every row still passes the complete validator.
            evidence_cache = None
            try:
                packets = []
                for row in rows:
                    try:
                        packets.append(ResearchPacket.model_validate_json(row["payload_json"]))
                    except ValueError:
                        pass
                evidence_ids = sorted({e.evidence_id for p in packets for e in p.evidence})
                scope_ids = sorted({c.content_id for p in packets for c in p.scope})
                evidence_cache = {e.evidence_id: e for e in self._evidence_many(connection, evidence_ids, scope_ids)}
            except ResearchRejected:
                pass  # Isolate unavailable references via individual verification.
            revisions = []
            unavailable = 0
            for row in rows:
                try:
                    result = self.verify_row(connection, row, evidence_cache=evidence_cache)
                    packet = result.packet
                    revisions.append({
                        "revision_id": result.result_identity, "assembled_at": packet.assembled_at,
                        "question": packet.question, "output_language": packet.output_language,
                        "scope_count": len(packet.scope), "evidence_count": len(packet.evidence),
                        "intelligence_count": len(packet.intelligence), "status": packet.material_status,
                    })
                except (ResearchRejected, KeyError):
                    unavailable += 1
            return {
                "revisions": revisions, "current_revision_id": current_id,
                "current_available": current_id is not None, "unavailable_count": unavailable,
                "has_more": has_more, "limit": limit,
                "next_cursor": f"{research_id}:{anchor}:{rows[-1]['execution_number']}" if has_more else None,
            }
        except ResearchRejected:
            raise
        except (ValueError, sqlite3.Error) as error:
            raise ResearchRejected("RESEARCH_CORRUPTED_RESULT") from error
        finally:
            connection.close()

    def list_current(self, *, offset: int = 0, limit: int = 25) -> dict[str, object]:
        connection = self._repository._connect(read_only=True)
        try:
            total = int(connection.execute("SELECT count(*) FROM research_items").fetchone()[0])
            ids = [r[0] for r in connection.execute(
                "SELECT research_id FROM research_items ORDER BY created_at DESC, research_id LIMIT ? OFFSET ?", (limit, offset)
            )]
        finally:
            connection.close()
        items = []
        for identity in ids:
            try:
                result = self.read(identity)
                packet = result.packet
                items.append({"research_id": identity, "question": packet.question,
                              "scope_count": len(packet.scope), "assembled_at": packet.assembled_at,
                              "output_language": packet.output_language, "status": packet.material_status})
            except ResearchRejected as error:
                items.append({"research_id": identity, "status": error.code})
        return {"research": items, "total": total, "offset": offset, "limit": limit}

    def scope_options(self, *, query: str = "", offset: int = 0, limit: int = 50) -> dict[str, object]:
        connection = self._repository._connect(read_only=True)
        try:
            connection.execute("BEGIN")
            where = "WHERE availability=? AND (instr(lower(coalesce(title,'')),lower(?))>0 OR instr(lower(channel_name),lower(?))>0)"
            parameters = [Availability.PUBLIC.value, query, query]
            total = int(connection.execute("SELECT count(*) FROM videos " + where, parameters).fetchone()[0])
            rows = connection.execute(
                "SELECT video_id,title,coalesce(channel_name,'') AS channel_name FROM videos " + where +
                " ORDER BY published_at DESC,video_id LIMIT ? OFFSET ?", [*parameters, limit, offset],
            ).fetchall()
            return {"content": [{"content_id": r["video_id"], "title": None if r["title"] is None else r["title"][:240], "channel_name": r["channel_name"][:240]} for r in rows],
                    "total": total, "offset": offset, "limit": limit}
        finally:
            connection.close()

    @staticmethod
    def verify_schema(connection: sqlite3.Connection) -> None:
        """Match table, index, FK/check and trigger definitions to packaged 031."""
        sql = resources.files("youtube_intel").joinpath("migrations", "031_add_research_lite.sql").read_text()
        expected = sqlite3.connect(":memory:")
        try:
            expected.executescript(sql)
            query = "SELECT name,sql FROM sqlite_master WHERE (name LIKE 'research_%' OR name LIKE 'idx_research_%') AND sql IS NOT NULL ORDER BY name"
            def normalized(db: sqlite3.Connection) -> list[tuple[str, str]]:
                return [(r[0], " ".join(r[1].split()).rstrip(";")) for r in db.execute(query)]
            if normalized(expected) != normalized(connection):
                raise ResearchRejected("RESEARCH_CORRUPTED_RESULT")
        finally:
            expected.close()

    def verify_database(self, connection: sqlite3.Connection) -> None:
        self.verify_schema(connection)
        for item in connection.execute("SELECT * FROM research_items"):
            bounds = connection.execute("SELECT count(*),min(execution_number),max(execution_number) FROM research_results WHERE research_id=?", (item["research_id"],)).fetchone()
            current = connection.execute("SELECT research_id,execution_number FROM research_results WHERE result_identity=?", (item["current_result_identity"],)).fetchone()
            if (not bounds[0] or bounds[1] != 1 or bounds[0] != bounds[2] or current is None
                    or current["research_id"] != item["research_id"] or current["execution_number"] != bounds[2]):
                raise ResearchRejected("RESEARCH_CORRUPTED_RESULT")
        for row in connection.execute("SELECT * FROM research_results"):
            self.verify_row(connection, row)
