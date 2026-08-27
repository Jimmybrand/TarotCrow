"""JSON-backed persistence layer for the Tarot memory system.

The store is intentionally simple: a single JSON file that mirrors the
`MemoryStore` model.  Replacing it with a real database later should only
require swapping out this module.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import MemoryEntry, MemoryStore, MemoryType, ReadingMemory


class JsonMemoryStore:
    """Thread-safe, JSON-file backed memory store.

    All public methods acquire an internal lock, so the store is safe to use
    from multiple threads in the same process.  Writes are flushed to disk
    immediately after every mutating operation.

    Args:
        path: Path to the JSON file used for persistence.  If the file does
            not exist, an empty store is created on first access.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._store = MemoryStore()
        self._load()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        """Load state from disk, or start empty if the file is missing."""
        if not self._path.exists():
            self._store = MemoryStore()
            return

        with self._path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        self._store = MemoryStore.model_validate(data)
        self._store.remove_expired()

    def _save(self) -> None:
        """Persist the current state to disk atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(
                self._store.model_dump(mode="json"),
                fh,
                indent=2,
                ensure_ascii=False,
                default=_json_default,
            )
        tmp.replace(self._path)

    # ------------------------------------------------------------------ #
    # Memory entry CRUD
    # ------------------------------------------------------------------ #

    def create_entry(
        self,
        user_id: str,
        type: MemoryType,  # noqa: A002
        content: str,
        *,
        provenance: str = "",
        confidence: float = 1.0,
        created_at: datetime | None = None,
        expires_at: datetime | None = None,
        ttl_seconds: int | None = None,
    ) -> MemoryEntry:
        """Create and persist a new memory entry.

        Args:
            user_id: Owner of the memory.
            type: Classification of the memory.
            content: The memory content.
            provenance: Origin of the memory.
            confidence: Confidence score in [0.0, 1.0].
            created_at: Optional creation timestamp.  Defaults to now.
            expires_at: Explicit expiry timestamp.  Takes precedence over
                `ttl_seconds`.
            ttl_seconds: Time-to-live in seconds from creation.

        Returns:
            The created `MemoryEntry`.
        """
        if expires_at is None and ttl_seconds is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        entry = MemoryEntry(
            user_id=user_id,
            type=type,
            content=content,
            provenance=provenance,
            confidence=confidence,
            created_at=created_at or datetime.now(timezone.utc),
            expires_at=expires_at,
        )

        with self._lock:
            # Store a copy so callers cannot accidentally mutate internal state.
            self._store.add_entry(entry.model_copy())
            self._save()
        return entry

    def get_entry(self, entry_id: str) -> MemoryEntry | None:
        """Fetch a memory entry by id."""
        with self._lock:
            entry = self._store.get_entry(entry_id)
            if entry is not None and entry.is_expired():
                self._store.delete_entry(entry_id)
                self._save()
                return None
            return entry

    def update_entry(self, entry: MemoryEntry) -> MemoryEntry:
        """Update an existing memory entry.

        This method enforces the memory-safety rule: entries of type
        `HYPOTHESIS` or `MODEL_INTERPRETATION` cannot be automatically
        upgraded to `USER_STATED_FACT`.  Such an upgrade must be performed
        by creating a new, explicitly verified entry.

        Raises:
            KeyError: if the entry does not exist.
            ValueError: if the update violates memory-safety rules.
        """
        with self._lock:
            existing = self._store.get_entry(entry.id)
            if existing is None:
                raise KeyError(f"Memory entry {entry.id!r} not found")

            if entry.type == MemoryType.USER_STATED_FACT and existing.type in {
                MemoryType.HYPOTHESIS,
                MemoryType.MODEL_INTERPRETATION,
            }:
                raise ValueError(
                    "Cannot auto-upgrade HYPOTHESIS or MODEL_INTERPRETATION "
                    "to USER_STATED_FACT"
                )

            self._store.update_entry(entry)
            self._save()
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a memory entry by id.  Returns True if it existed."""
        with self._lock:
            removed = self._store.delete_entry(entry_id)
            if removed:
                self._save()
            return removed

    # ------------------------------------------------------------------ #
    # Reading summary CRUD
    # ------------------------------------------------------------------ #

    def create_reading(
        self,
        user_id: str,
        *,
        question_summary: str = "",
        domain: str = "",
        tags: list[str] | None = None,
        entities: list[str] | None = None,
        entities_context: dict[str, Any] | None = None,
        thread_id: str | None = None,
    ) -> ReadingMemory:
        """Create and persist a reading summary."""
        reading = ReadingMemory(
            user_id=user_id,
            question_summary=question_summary,
            domain=domain,
            tags=list(tags or []),
            entities=list(entities or []),
            entities_context=dict(entities_context or {}),
            thread_id=thread_id,
        )
        with self._lock:
            self._store.add_reading(reading)
            self._save()
        return reading

    def get_reading(self, reading_id: str) -> ReadingMemory | None:
        """Fetch a reading summary by id."""
        with self._lock:
            return self._store.get_reading(reading_id)

    def delete_reading(self, reading_id: str) -> bool:
        """Delete a reading summary by id.  Returns True if it existed."""
        with self._lock:
            removed = self._store.delete_reading(reading_id)
            if removed:
                self._save()
            return removed

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def query_by_user(self, user_id: str) -> list[MemoryEntry]:
        """Return all non-expired memory entries for a user."""
        with self._lock:
            self._store.remove_expired()
            return self._store.query_by_user(user_id)

    def query_by_entity(self, entity: str) -> list[MemoryEntry]:
        """Return all non-expired memory entries mentioning an entity."""
        with self._lock:
            self._store.remove_expired()
            return self._store.query_by_entity(entity)

    def query_by_thread(self, thread_id: str) -> list[ReadingMemory]:
        """Return reading summaries linked to a thread."""
        with self._lock:
            return self._store.query_by_thread(thread_id)

    def list_all_entries(self) -> list[MemoryEntry]:
        """Return all non-expired memory entries.  Useful for admin/debug."""
        with self._lock:
            self._store.remove_expired()
            return list(self._store.entries.values())

    def cleanup_expired(self) -> int:
        """Remove expired entries and return the number deleted."""
        with self._lock:
            removed = self._store.remove_expired()
            if removed:
                self._save()
            return len(removed)

    # ------------------------------------------------------------------ #
    # Testing / migration helpers
    # ------------------------------------------------------------------ #

    def clear(self) -> None:
        """Remove all entries and readings.  Useful in tests."""
        with self._lock:
            self._store = MemoryStore()
            self._save()


def _json_default(obj: Any) -> Any:
    """Fallback JSON encoder for non-serialisable values."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
