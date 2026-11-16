"""Provider registry: discovery candidates are never automatically trusted."""
from dataclasses import dataclass
from enum import Enum

class SourceStatus(str, Enum):
    CANDIDATE = "candidate"
    QUARANTINED = "quarantined"
    APPROVED = "approved"
    DISABLED = "disabled"

@dataclass(frozen=True)
class SourceCandidate:
    name: str
    domain: str
    category: str
    status: SourceStatus = SourceStatus.CANDIDATE

class SourceRegistry:
    def __init__(self):
        self._sources: dict[str, SourceCandidate] = {}

    def register(self, source: SourceCandidate) -> None:
        if not source.domain or source.domain in self._sources:
            raise ValueError("source domain missing or already registered")
        self._sources[source.domain] = source

    def approved(self, category: str) -> list[SourceCandidate]:
        return [s for s in self._sources.values()
                if s.category == category and s.status == SourceStatus.APPROVED]
