from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.access import allowed_scopes
from app.data import SEED_MEMORY


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def score(query: str, text: str) -> float:
    q = tokenize(query)
    t = tokenize(text)
    if not q or not t:
        return 0.0
    overlap = len(q & t)
    return overlap / math.sqrt(len(q) * len(t))


@dataclass
class MemoryRecord:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorMemory:
    def upsert_memory(self, scope: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        raise NotImplementedError

    def search_memory(self, scope: str, query: str, limit: int = 4) -> list[MemoryRecord]:
        raise NotImplementedError

    def search_allowed_scopes(self, user_id: str, query: str, limit: int = 4) -> tuple[list[MemoryRecord], list[str]]:
        queried = allowed_scopes(user_id)
        records: list[tuple[float, MemoryRecord]] = []
        for scope in queried:
            for record in self.search_memory(scope, query, limit):
                records.append((score(query, record.text), record))
        records.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in records[:limit]], queried

    @property
    def mode(self) -> str:
        return "unknown"


class FallbackVectorMemory(VectorMemory):
    def __init__(self) -> None:
        self.records: dict[str, list[MemoryRecord]] = {}
        for scope, texts in SEED_MEMORY.items():
            for text in texts:
                self.upsert_memory(scope, text, {"seed": True, "scope": scope})

    def upsert_memory(self, scope: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        self.records.setdefault(scope, []).append(MemoryRecord(text, metadata or {"scope": scope}))

    def search_memory(self, scope: str, query: str, limit: int = 4) -> list[MemoryRecord]:
        candidates = self.records.get(scope, [])
        ranked = sorted(candidates, key=lambda record: score(query, record.text), reverse=True)
        return ranked[:limit]

    @property
    def mode(self) -> str:
        return "fallback in-memory vector store"


class ActianVectorMemory(FallbackVectorMemory):
    """Hackathon adapter placeholder.

    The interface is intentionally identical to the fallback store so the app's
    access-control proof cannot accidentally depend on a storage backend.
    """

    @property
    def mode(self) -> str:
        host = os.getenv("VECTORAI_HOST", "unconfigured")
        return f"Actian VectorAI DB adapter ({host})"


def build_memory() -> VectorMemory:
    required = ["VECTORAI_HOST", "VECTORAI_PORT", "VECTORAI_USERNAME", "VECTORAI_PASSWORD", "VECTORAI_DATABASE"]
    if os.getenv("STORAGE_MODE") == "actian" and all(os.getenv(key) for key in required):
        return ActianVectorMemory()
    return FallbackVectorMemory()
