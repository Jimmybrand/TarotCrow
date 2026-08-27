"""Tests for the Tarot memory / history system."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tarot.memory.models import MemoryEntry, MemoryStore, MemoryType, ReadingMemory
from tarot.memory.retriever import retrieve_relevant
from tarot.memory.store import JsonMemoryStore


class TestMemoryEntry:
    """Unit tests for the MemoryEntry model."""

    def test_create_user_stated_fact(self) -> None:
        entry = MemoryEntry(
            user_id="user-1",
            type=MemoryType.USER_STATED_FACT,
            content="User prefers career readings in the morning.",
        )
        assert entry.user_id == "user-1"
        assert entry.type == MemoryType.USER_STATED_FACT
        assert entry.confidence == 1.0
        assert entry.expires_at is None
        assert not entry.is_expired()

    def test_expiry_validation(self) -> None:
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError):
            MemoryEntry(
                user_id="user-1",
                type=MemoryType.READING_CONTEXT,
                content="context",
                created_at=now,
                expires_at=now - timedelta(hours=1),
            )

    def test_is_expired(self) -> None:
        now = datetime.now(timezone.utc)
        entry = MemoryEntry(
            user_id="user-1",
            type=MemoryType.HYPOTHESIS,
            content="guess",
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        assert entry.is_expired(now)


class TestReadingMemory:
    """Unit tests for the ReadingMemory model."""

    def test_create_reading_summary(self) -> None:
        reading = ReadingMemory(
            user_id="user-1",
            question_summary="Should I change jobs?",
            domain="career",
            tags=["career", "decision"],
            entities=["current employer", "new offer"],
            thread_id="thread-abc",
        )
        assert reading.user_id == "user-1"
        assert reading.domain == "career"
        assert reading.thread_id == "thread-abc"


class TestMemoryStore:
    """Unit tests for the in-memory MemoryStore model."""

    @pytest.fixture
    def store(self) -> MemoryStore:
        return MemoryStore()

    def test_add_and_get_entry(self, store: MemoryStore) -> None:
        entry = MemoryEntry(user_id="u1", type=MemoryType.USER_STATED_FACT, content="fact")
        store.add_entry(entry)
        assert store.get_entry(entry.id) == entry

    def test_update_entry(self, store: MemoryStore) -> None:
        entry = MemoryEntry(user_id="u1", type=MemoryType.USER_STATED_FACT, content="old")
        store.add_entry(entry)
        entry.content = "new"
        store.update_entry(entry)
        assert store.get_entry(entry.id).content == "new"

    def test_update_missing_entry_raises(self, store: MemoryStore) -> None:
        entry = MemoryEntry(user_id="u1", type=MemoryType.USER_STATED_FACT, content="x")
        with pytest.raises(KeyError):
            store.update_entry(entry)

    def test_delete_entry(self, store: MemoryStore) -> None:
        entry = MemoryEntry(user_id="u1", type=MemoryType.USER_STATED_FACT, content="fact")
        store.add_entry(entry)
        assert store.delete_entry(entry.id) is True
        assert store.get_entry(entry.id) is None

    def test_query_by_user(self, store: MemoryStore) -> None:
        e1 = MemoryEntry(user_id="u1", type=MemoryType.USER_STATED_FACT, content="a")
        e2 = MemoryEntry(user_id="u2", type=MemoryType.USER_STATED_FACT, content="b")
        e3 = MemoryEntry(user_id="u1", type=MemoryType.READING_CONTEXT, content="c")
        store.add_entry(e1)
        store.add_entry(e2)
        store.add_entry(e3)
        results = store.query_by_user("u1")
        assert len(results) == 2
        assert all(r.user_id == "u1" for r in results)

    def test_query_by_entity(self, store: MemoryStore) -> None:
        e1 = MemoryEntry(user_id="u1", type=MemoryType.USER_STATED_FACT, content="Luna is a cat")
        e2 = MemoryEntry(user_id="u1", type=MemoryType.USER_STATED_FACT, content="No mention")
        store.add_entry(e1)
        store.add_entry(e2)
        results = store.query_by_entity("luna")
        assert len(results) == 1
        assert results[0].id == e1.id

    def test_query_by_thread(self, store: MemoryStore) -> None:
        r1 = ReadingMemory(user_id="u1", thread_id="t1")
        r2 = ReadingMemory(user_id="u1", thread_id="t2")
        r3 = ReadingMemory(user_id="u1", thread_id="t1")
        store.add_reading(r1)
        store.add_reading(r2)
        store.add_reading(r3)
        results = store.query_by_thread("t1")
        assert len(results) == 2

    def test_remove_expired(self, store: MemoryStore) -> None:
        now = datetime.now(timezone.utc)
        e1 = MemoryEntry(
            user_id="u1",
            type=MemoryType.USER_STATED_FACT,
            content="fresh",
            created_at=now,
            expires_at=now + timedelta(days=1),
        )
        e2 = MemoryEntry(
            user_id="u1",
            type=MemoryType.USER_STATED_FACT,
            content="stale",
            created_at=now - timedelta(days=2),
            expires_at=now - timedelta(days=1),
        )
        store.add_entry(e1)
        store.add_entry(e2)
        removed = store.remove_expired(now)
        assert removed == [e2.id]
        assert store.get_entry(e2.id) is None
        assert store.get_entry(e1.id) is not None


class TestJsonMemoryStore:
    """Integration tests for the JSON-backed memory store."""

    @pytest.fixture
    def tmp_path(self) -> Path:
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    @pytest.fixture
    def json_store(self, tmp_path: Path) -> JsonMemoryStore:
        return JsonMemoryStore(tmp_path / "memory.json")

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "memory.json"
        store = JsonMemoryStore(path)
        entry = store.create_entry(
            user_id="u1",
            type=MemoryType.USER_STATED_FACT,
            content="persisted",
        )
        store.create_reading(user_id="u1", question_summary="q", domain="career")

        # Re-open the store and verify data is reloaded.
        store2 = JsonMemoryStore(path)
        assert store2.get_entry(entry.id) is not None
        assert len(store2.list_all_entries()) == 1
        assert len(store2.query_by_thread(None)) == 1

    def test_create_entry_with_ttl(self, json_store: JsonMemoryStore) -> None:
        entry = json_store.create_entry(
            user_id="u1",
            type=MemoryType.READING_CONTEXT,
            content="context",
            ttl_seconds=3600,
        )
        assert entry.expires_at is not None
        assert entry.expires_at > datetime.now(timezone.utc)

    def test_get_entry_expires(self, json_store: JsonMemoryStore) -> None:
        now = datetime.now(timezone.utc)
        entry = MemoryEntry(
            user_id="u1",
            type=MemoryType.HYPOTHESIS,
            content="old guess",
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        json_store._store.add_entry(entry)  # type: ignore[attr-defined]
        json_store._save()  # type: ignore[attr-defined]
        assert json_store.get_entry(entry.id) is None

    def test_memory_safety_blocks_upgrade(self, json_store: JsonMemoryStore) -> None:
        entry = json_store.create_entry(
            user_id="u1",
            type=MemoryType.HYPOTHESIS,
            content="maybe",
        )
        entry.type = MemoryType.USER_STATED_FACT
        with pytest.raises(ValueError, match="Cannot auto-upgrade"):
            json_store.update_entry(entry)

    def test_memory_safety_allows_same_type_update(self, json_store: JsonMemoryStore) -> None:
        entry = json_store.create_entry(
            user_id="u1",
            type=MemoryType.HYPOTHESIS,
            content="maybe",
        )
        entry.content = "refined maybe"
        updated = json_store.update_entry(entry)
        assert updated.content == "refined maybe"

    def test_cleanup_expired(self, json_store: JsonMemoryStore) -> None:
        now = datetime.now(timezone.utc)
        json_store.create_entry(
            user_id="u1",
            type=MemoryType.USER_STATED_FACT,
            content="fresh",
            created_at=now,
            expires_at=now + timedelta(days=1),
        )
        json_store.create_entry(
            user_id="u1",
            type=MemoryType.USER_STATED_FACT,
            content="stale",
            created_at=now - timedelta(days=2),
            expires_at=now - timedelta(days=1),
        )
        removed = json_store.cleanup_expired()
        assert removed == 1
        assert len(json_store.list_all_entries()) == 1

    def test_query_by_user_removes_expired(self, json_store: JsonMemoryStore) -> None:
        now = datetime.now(timezone.utc)
        json_store.create_entry(
            user_id="u1",
            type=MemoryType.USER_STATED_FACT,
            content="stale",
            created_at=now - timedelta(days=2),
            expires_at=now - timedelta(days=1),
        )
        results = json_store.query_by_user("u1")
        assert results == []


class TestRetriever:
    """Tests for the memory retriever."""

    @pytest.fixture
    def populated_store(self, tmp_path: Path) -> JsonMemoryStore:
        store = JsonMemoryStore(tmp_path / "memory.json")
        store.create_entry(
            user_id="u1",
            type=MemoryType.USER_STATED_FACT,
            content="User works in software engineering",
        )
        store.create_entry(
            user_id="u1",
            type=MemoryType.READING_CONTEXT,
            content="Previous career reading mentioned a promotion",
        )
        store.create_entry(
            user_id="u1",
            type=MemoryType.MODEL_INTERPRETATION,
            content="The Tower suggests sudden change in love life",
        )
        store.create_entry(
            user_id="u1",
            type=MemoryType.HYPOTHESIS,
            content="User may be interested in remote work",
            confidence=0.4,
        )
        store.create_entry(
            user_id="u2",
            type=MemoryType.USER_STATED_FACT,
            content="Other user's fact about career",
        )
        return store

    def test_retrieve_relevant_filters_by_user(self, populated_store: JsonMemoryStore) -> None:
        results = retrieve_relevant(
            populated_store,
            user_id="u1",
            question="What about my career?",
            domain="career",
        )
        assert all(r.user_id == "u1" for r in results)

    def test_retrieve_relevant_ranks_matching_facts(
        self, populated_store: JsonMemoryStore
    ) -> None:
        results = retrieve_relevant(
            populated_store,
            user_id="u1",
            question="Tell me about my career path",
            domain="career",
            limit=3,
        )
        assert len(results) <= 3
        # The user-stated fact about software engineering should rank highest.
        assert results[0].type == MemoryType.USER_STATED_FACT
        assert "software" in results[0].content.lower()

    def test_retrieve_relevant_drops_unrelated_memories(
        self, populated_store: JsonMemoryStore
    ) -> None:
        results = retrieve_relevant(
            populated_store,
            user_id="u1",
            question="What do the cards say about my pet?",
            domain="pets",
            limit=5,
        )
        # None of the seeded memories mention pets, so nothing should return.
        assert results == []

    def test_retrieve_relevant_respects_limit(self, populated_store: JsonMemoryStore) -> None:
        results = retrieve_relevant(
            populated_store,
            user_id="u1",
            question="career software engineering promotion",
            domain="career",
            limit=2,
        )
        assert len(results) == 2

    def test_retrieve_relevant_prefers_user_stated_facts(
        self, populated_store: JsonMemoryStore
    ) -> None:
        results = retrieve_relevant(
            populated_store,
            user_id="u1",
            question="career",
            domain="career",
            limit=1,
        )
        assert results[0].type == MemoryType.USER_STATED_FACT
