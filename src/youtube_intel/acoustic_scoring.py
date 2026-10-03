"""Deterministic private-stage scoring; never normalizes transcript authority.

NFKC, casefold, punctuation/space removal for CER; Unicode word tokens for WER.
Mixed units are individual Han characters and contiguous non-Han word tokens.
No translation, number rewriting, traditional/simplified conversion or synonyms.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

POLICY = "nfkc-casefold-han-character-latin-word-v1"


def _han(char: str) -> bool:
    return "\u3400" <= char <= "\u9fff" or "\U00020000" <= char <= "\U0003134f"


def text_units(text: str, language: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    if language == "zh":
        return [c for c in normalized if unicodedata.category(c)[0] in {"L", "N"}]
    if language == "mixed":
        normalized = "".join(" " + c + " " if _han(c) else c for c in normalized)
    elif language != "en":
        raise ValueError("unsupported scorer")
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)*", normalized, re.UNICODE)


def _metric(reference: Sequence[str], actual: Sequence[str]) -> dict[str, float | int]:
    if not reference:
        raise ValueError("reference has no scored units")
    row = list(range(len(actual) + 1))
    for i, expected in enumerate(reference, 1):
        next_row = [i]
        for j, observed in enumerate(actual, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1, row[j - 1] + (expected != observed)))
        row = next_row
    return {"errors": row[-1], "reference_units": len(reference), "error_rate": row[-1] / len(reference)}


def score(reference: str, actual: str, language: str) -> dict[str, object]:
    expected, observed = text_units(reference, language), text_units(actual, language)
    result: dict[str, object] = dict(_metric(expected, observed))
    if language == "mixed":
        for name, predicate in (("han", True), ("latin", False)):
            ref = [u for u in expected if (len(u) == 1 and _han(u)) == predicate]
            hyp = [u for u in observed if (len(u) == 1 and _han(u)) == predicate]
            result[name] = _metric(ref, hyp) if ref else {"state": "NOT_EVALUATED", "insertions": len(hyp)}
    return result


def coverage(
    speech_regions: Sequence[tuple[float, float]],
    segments: Sequence[tuple[float, float]],
) -> dict[str, object]:
    """Coverage of known expected speech only; designed silence is never scored.

    Each utterance must have >=80% interval coverage and no internal/boundary
    uncovered run >1.5 seconds. These diagnostics do not assert word precision.
    Segment validity is separately enforced by the Phase 8 transcript contract.
    """
    regions = []
    for start, end in speech_regions:
        if not 0 <= start < end:
            raise ValueError("invalid speech region")
        cursor, covered, largest_gap = start, 0.0, 0.0
        for left, right in sorted(segments):
            left, right = max(start, left), min(end, right)
            if right <= left or right <= cursor:
                continue
            largest_gap = max(largest_gap, left - cursor)
            covered += right - max(left, cursor)
            cursor = right
        largest_gap = max(largest_gap, end - cursor)
        fraction = covered / (end - start)
        regions.append({"start": start, "end": end, "coverage": fraction, "uncovered_seconds": end - start - covered, "largest_gap_seconds": largest_gap, "passed": fraction >= 0.8 and largest_gap <= 1.5})
    return {"passed": bool(regions) and all(r["passed"] for r in regions), "regions": regions}
