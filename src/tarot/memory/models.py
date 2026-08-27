"""Data models for the Tarot memory / history system.

Memory captures durable facts about users and readings so that future
readings can be personalised without re-asking the same questions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Self
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class MemoryType(str, Enum):
    """Classification of a memory entry.

    The type determines how much trust the system places in the entry and
    whether it may be surfaced as a hard fact to the user.
    """

    USER_STATED_FACT = "user_stated_fact"
    READING_CONTEXT = "reading_context"
    MODEL_INTERPRETATION = "model_interpretation"
    HYPOTHESIS = "hypothesis"


class MemoryEntry(BaseModel):
    """A single durable memory atom.

    A memory entry is intentionally fine-grained: one fact or one piece of
    context per entry.  This makes retrieval, expiry and provenance tracking
    easier than storing large blobs.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this memory entry.",
    )
    user_id: str = Field(..., description="Owner of the memory.")
    type: MemoryType = Field(
        ...,
        description="Kind of memory; controls trust and surfacing rules.",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="The actual memory content.",
    )
    provenance: str = Field(
        default="",
        description="Where this memory came from, e.g. 'user:profile' or 'model:reading'.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the entry was created.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="UTC expiry timestamp; None means never expires.",
    )

    @model_validator(mode="after")
    def _validate_expiry(self) -> Self:
        if self.expires_at is not None and self.expires_at < self.created_at:
            raise ValueError("expires_at must not be earlier than created_at")
        return self

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return True if the memory has passed its expiry time."""
        if self.expires_at is None:
            return False
        if now is None:
            now = datetime.now(timezone.utc)
        return self.expires_at <= now

    def is_user_stated_fact(self) -> bool:
        """Return True if this entry is a user-stated fact."""
        return self.type == MemoryType.USER_STATED_FACT


class ReadingMemory(BaseModel):
    """Summary metadata for a single tarot reading.

    This is a lightweight, queryable index of a reading.  The full reading
    record (cards, interpretations, etc.) is expected to live elsewhere;
    this model only stores the facets needed for memory retrieval.
    """

    reading_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the reading.",
    )
    user_id: str = Field(..., description="User who requested the reading.")
    question_summary: str = Field(
        default="",
        description="Short normalised summary of the user's question.",
    )
    domain: str = Field(
        default="",
        description="Domain or life area, e.g. 'career' or 'relationships'.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form tags attached to the reading.",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Named entities extracted from the question/context.",
    )
    entities_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured context about entities.",
    )
    thread_id: str | None = Field(
        default=None,
        description="Conversation thread this reading belongs to, if any.",
    )


class MemoryStore(BaseModel):
    """In-memory container of memory entries and reading summaries.

    This model is used by the JSON-backed store to persist its entire state
    to disk.  It is not intended to be used directly by callers; use
    `JsonMemoryStore` instead.
    """

    entries: dict[str, MemoryEntry] = Field(default_factory=dict)
    readings: dict[str, ReadingMemory] = Field(default_factory=dict)

    def add_entry(self, entry: MemoryEntry) -> MemoryEntry:
        """Add a memory entry, returning the stored instance."""
        self.entries[entry.id] = entry
        return entry

    def get_entry(self, entry_id: str) -> MemoryEntry | None:
        """Fetch a memory entry by id, or None if missing."""
        return self.entries.get(entry_id)

    def update_entry(self, entry: MemoryEntry) -> MemoryEntry:
        """Update an existing memory entry in place.

        Raises:
            KeyError: if the entry id does not already exist.
        """
        if entry.id not in self.entries:
            raise KeyError(f"Memory entry {entry.id!r} not found")
        self.entries[entry.id] = entry
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a memory entry by id.  Returns True if it existed."""
        return self.entries.pop(entry_id, None) is not None

    def add_reading(self, reading: ReadingMemory) -> ReadingMemory:
        """Add a reading summary, returning the stored instance."""
        self.readings[reading.reading_id] = reading
        return reading

    def get_reading(self, reading_id: str) -> ReadingMemory | None:
        """Fetch a reading summary by id, or None if missing."""
        return self.readings.get(reading_id)

    def delete_reading(self, reading_id: str) -> bool:
        """Delete a reading summary by id.  Returns True if it existed."""
        return self.readings.pop(reading_id, None) is not None

    def query_by_user(self, user_id: str) -> list[MemoryEntry]:
        """Return all memory entries belonging to the given user."""
        return [e for e in self.entries.values() if e.user_id == user_id]

    def query_by_entity(self, entity: str) -> list[MemoryEntry]:
        """Return memory entries whose content mentions the entity.

        Matching is case-insensitive and based on simple substring search.
        """
        needle = entity.lower()
        return [e for e in self.entries.values() if needle in e.content.lower()]

    def query_by_thread(self, thread_id: str) -> list[ReadingMemory]:
        """Return reading summaries linked to the given thread."""
        return [r for r in self.readings.values() if r.thread_id == thread_id]

    def remove_expired(self, now: datetime | None = None) -> list[str]:
        """Remove expired entries and return the ids that were deleted."""
        if now is None:
            now = datetime.now(timezone.utc)
        expired = [eid for eid, e in self.entries.items() if e.is_expired(now)]
        for eid in expired:
            del self.entries[eid]
        return expired


__all__ = [
    "MemoryType",
    "MemoryEntry",
    "ReadingMemory",
    "MemoryStore",
]
