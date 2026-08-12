"""Stable command-operation contracts shared by CLI and production runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol


class ExitCode(IntEnum):
    OK = 0
    EXECUTION_FAILED = 1
    USAGE_OR_CONFIGURATION = 2
    LOCAL_RESOURCE = 3


@dataclass(frozen=True, slots=True)
class CommandOutcome:
    """A service result with bounded, user-safe terminal feedback."""

    attempted: int = 0
    failed: int = 0
    prerequisite_failed: bool = False
    local_resource_failed: bool = False
    safe_message: str | None = None

    def __post_init__(self) -> None:
        if self.attempted < 0 or self.failed < 0 or self.failed > self.attempted:
            raise ValueError("command outcome counts are invalid")
        if self.prerequisite_failed and self.local_resource_failed:
            raise ValueError("command outcome has conflicting terminal categories")
        if self.safe_message is not None and (
            not self.safe_message.strip() or len(self.safe_message) > 500
        ):
            raise ValueError("command outcome message is invalid")

    @property
    def exit_code(self) -> ExitCode:
        if self.local_resource_failed:
            return ExitCode.LOCAL_RESOURCE
        if self.prerequisite_failed:
            return ExitCode.USAGE_OR_CONFIGURATION
        if self.failed:
            return ExitCode.EXECUTION_FAILED
        return ExitCode.OK


class Operations(Protocol):
    def check(self, *, channel: str | None, limit: int | None) -> CommandOutcome: ...

    def process(self, *, video: str | None, resume: bool) -> CommandOutcome: ...

    def retry(self, *, video: str | None, failed_only: bool) -> CommandOutcome: ...

    def weekly(self, *, week: str | None) -> CommandOutcome: ...


__all__ = ["CommandOutcome", "ExitCode", "Operations"]
