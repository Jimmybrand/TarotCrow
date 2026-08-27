"""Unit tests for Tarot Reading state machine, data model, factory, and store."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from tarot.knowledge.models import CardOrientation, Spread, SpreadPosition
from tarot.knowledge.spreads import (
    CELTIC_CROSS_SPREAD,
    ONE_CARD_SPREAD,
    THREE_CARD_SPREAD,
)
from tarot.reading import (
    DomainType,
    DrawnCard,
    InvalidStateTransitionError,
    Reading,
    ReadingFactory,
    ReadingStatus,
    ReadingStore,
)


class TestReadingModel:
    """Test Reading and DrawnCard immutable data models."""

    def test_drawn_card_immutability(self) -> None:
        pos = SpreadPosition(name="Present", description="Now", order=0)
        card = DrawnCard(
            card_id="the_fool",
            orientation=CardOrientation.UPRIGHT,
            position=pos,
            draw_order=0,
        )

        with pytest.raises(ValidationError):
            card.card_id = "the_magician"  # type: ignore[misc]

        with pytest.raises(ValidationError):
            card.orientation = CardOrientation.REVERSED  # type: ignore[misc]

    def test_reading_creation_and_defaults(self) -> None:
        r_id = uuid4()
        pos = SpreadPosition(name="Single", description="Card", order=0)
        spread = Spread(id="single", name="Single", positions=[pos])
        card = DrawnCard(
            card_id="the_fool",
            orientation=CardOrientation.UPRIGHT,
            position=pos,
            draw_order=0,
        )

        reading = Reading(
            id=r_id,
            user_id="user_123",
            session_id="session_456",
            question="What is coming?",
            domain=DomainType.CAREER,
            spread=spread,
            cards=(card,),
        )

        assert reading.id == r_id
        assert reading.user_id == "user_123"
        assert reading.session_id == "session_456"
        assert reading.domain == DomainType.CAREER
        assert reading.status == ReadingStatus.PENDING
        assert reading.interpretation is None
        assert len(reading.cards) == 1
        assert reading.cards[0].card_id == "the_fool"
        assert reading.created_at is not None

    def test_reading_immutability(self) -> None:
        reading = ReadingFactory.create_reading(
            question="Should I change jobs?",
            spread=ONE_CARD_SPREAD,
            user_id="user_test",
        )

        # Cannot directly mutate fields
        with pytest.raises(ValidationError):
            reading.status = ReadingStatus.COMPLETED  # type: ignore[misc]

        with pytest.raises(ValidationError):
            reading.cards = ()  # type: ignore[misc]

        with pytest.raises(ValidationError):
            reading.interpretation = "New interpretation"  # type: ignore[misc]

    def test_cards_and_related_readings_tuple_coercion(self) -> None:
        pos = SpreadPosition(name="Single", description="Card", order=0)
        spread = Spread(id="single", name="Single", positions=[pos])
        card = DrawnCard(
            card_id="the_fool",
            orientation=CardOrientation.UPRIGHT,
            position=pos,
            draw_order=0,
        )
        rel_id = uuid4()

        reading = Reading(
            user_id="u1",
            session_id="s1",
            question="Q?",
            spread=spread,
            cards=[card],  # pass list, should coerce to tuple
            related_readings=[rel_id],  # pass list, should coerce to tuple
        )
        assert isinstance(reading.cards, tuple)
        assert isinstance(reading.related_readings, tuple)
        assert reading.related_readings[0] == rel_id


class TestReadingFactory:
    """Test ReadingFactory draw mechanics and non-replacement."""

    def test_create_reading_three_card_spread(self) -> None:
        reading = ReadingFactory.create_reading(
            question="How is my relationship?",
            domain=DomainType.LOVE,
            spread=THREE_CARD_SPREAD,
            user_id="user_alice",
            session_id="sess_alice",
            random_seed=42,
        )

        assert reading.user_id == "user_alice"
        assert reading.session_id == "sess_alice"
        assert reading.domain == DomainType.LOVE
        assert reading.spread.id == "three-card"
        assert len(reading.cards) == 3

        # Positions and orders must match spread positions
        for i, card in enumerate(reading.cards):
            assert card.draw_order == i
            assert card.position is not None
            assert card.position.name == THREE_CARD_SPREAD.positions[i].name
            assert card.orientation in (CardOrientation.UPRIGHT, CardOrientation.REVERSED)

        # Non-replacement check
        card_ids = [c.card_id for c in reading.cards]
        assert len(card_ids) == len(set(card_ids))

    def test_draw_without_replacement_all_celtic_cross(self) -> None:
        reading = ReadingFactory.create_reading(
            question="Complete life review",
            spread=CELTIC_CROSS_SPREAD,
            random_seed=12345,
        )
        assert len(reading.cards) == 10
        card_ids = [c.card_id for c in reading.cards]
        assert len(card_ids) == 10
        assert len(set(card_ids)) == 10

    def test_custom_deck_and_engines(self) -> None:
        custom_deck = ["custom_card_1", "custom_card_2", "custom_card_3"]

        def mock_draw(deck, count, rng):
            return deck[:count]

        def mock_orient(count, rng):
            return [CardOrientation.REVERSED] * count

        reading = ReadingFactory.create_reading(
            question="Testing custom engine",
            spread=THREE_CARD_SPREAD,
            deck=custom_deck,
            draw_engine=mock_draw,
            orientation_engine=mock_orient,
        )

        expected_ids = ["custom_card_1", "custom_card_2", "custom_card_3"]
        assert [c.card_id for c in reading.cards] == expected_ids
        assert all(c.orientation == CardOrientation.REVERSED for c in reading.cards)

    def test_factory_seed_reproducibility(self) -> None:
        r1 = ReadingFactory.create_reading(
            question="Seed test",
            spread=THREE_CARD_SPREAD,
            random_seed=999,
        )
        r2 = ReadingFactory.create_reading(
            question="Seed test",
            spread=THREE_CARD_SPREAD,
            random_seed=999,
        )

        assert [c.card_id for c in r1.cards] == [c.card_id for c in r2.cards]
        assert [c.orientation for c in r1.cards] == [c.orientation for c in r2.cards]

    def test_factory_deck_too_small_raises(self) -> None:
        with pytest.raises(ValueError, match="smaller than required spread positions"):
            ReadingFactory.create_reading(
                question="Too small",
                spread=THREE_CARD_SPREAD,
                deck=["card_1"],
            )

    def test_factory_duplicate_draw_raises(self) -> None:
        def bad_draw(deck, count, rng):
            return [deck[0]] * count  # duplicates

        with pytest.raises(ValueError, match="must be without replacement"):
            ReadingFactory.create_reading(
                question="Duplicate draw test",
                spread=THREE_CARD_SPREAD,
                draw_engine=bad_draw,
            )


class TestReadingStateMachine:
    """Test Reading lifecycle state machine transitions and safety rules."""

    def test_valid_lifecycle_progression(self) -> None:
        # PENDING -> IN_PROGRESS -> INTERPRETATION_PENDING -> INTERPRETATION_READY -> COMPLETED
        pos = SpreadPosition(name="Single", description="Card", order=0)
        spread = Spread(id="single", name="Single", positions=[pos])
        card = DrawnCard(
            card_id="the_fool",
            orientation=CardOrientation.UPRIGHT,
            position=pos,
            draw_order=0,
        )

        r0 = Reading(
            user_id="u",
            session_id="s",
            question="Q",
            spread=spread,
            cards=(card,),
            status=ReadingStatus.PENDING,
        )
        assert r0.status == ReadingStatus.PENDING

        r1 = r0.transition_to(ReadingStatus.IN_PROGRESS)
        assert r1.status == ReadingStatus.IN_PROGRESS
        assert r1.cards == r0.cards

        r2 = r1.transition_to(ReadingStatus.INTERPRETATION_PENDING)
        assert r2.status == ReadingStatus.INTERPRETATION_PENDING
        assert r2.cards == r0.cards

        r3 = r2.with_interpretation("You are about to embark on a fresh journey.")
        assert r3.status == ReadingStatus.INTERPRETATION_READY
        assert r3.interpretation == "You are about to embark on a fresh journey."
        assert r3.cards == r0.cards

        r4 = r3.transition_to(ReadingStatus.COMPLETED)
        assert r4.status == ReadingStatus.COMPLETED
        assert r4.cards == r0.cards

    def test_cards_and_orientation_cannot_be_changed_after_draw(self) -> None:
        reading = ReadingFactory.create_reading(
            question="State test",
            spread=THREE_CARD_SPREAD,
            random_seed=123,
        )
        original_cards = reading.cards

        # Transitioning state must preserve the exact drawn cards
        in_progress = reading.transition_to(ReadingStatus.INTERPRETATION_PENDING)
        assert in_progress.cards == original_cards

        ready = in_progress.with_interpretation("Interpreted text")
        assert ready.cards == original_cards
        assert ready.cards[0].orientation == original_cards[0].orientation

    def test_ai_failure_does_not_retrigger_draw_and_allows_retry(self) -> None:
        reading = ReadingFactory.create_reading(
            question="AI fail test",
            spread=THREE_CARD_SPREAD,
            random_seed=456,
        )
        original_cards = reading.cards

        # Transition to INTERPRETATION_PENDING
        pending_interp = reading.transition_to(ReadingStatus.INTERPRETATION_PENDING)

        # AI fails
        failed_reading = pending_interp.mark_failed(error_message="RateLimitError from LLM")
        assert failed_reading.status == ReadingStatus.FAILED
        assert failed_reading.audit_metadata.get("last_error") == "RateLimitError from LLM"
        assert failed_reading.cards == original_cards  # Cards remain immutable!

        # Retry interpretation
        retried_reading = failed_reading.retry_interpretation()
        assert retried_reading.status == ReadingStatus.INTERPRETATION_PENDING
        assert retried_reading.cards == original_cards  # Cards STILL identical!

        # Now succeed
        success_reading = retried_reading.with_interpretation(
            "AI successfully generated interpretation."
        )
        assert success_reading.status == ReadingStatus.INTERPRETATION_READY
        assert success_reading.interpretation == "AI successfully generated interpretation."
        assert success_reading.cards == original_cards

    def test_invalid_state_transitions(self) -> None:
        reading = ReadingFactory.create_reading(
            question="Invalid transition test",
            spread=ONE_CARD_SPREAD,
            initial_status=ReadingStatus.PENDING,
        )

        # PENDING cannot go directly to COMPLETED or INTERPRETATION_READY
        with pytest.raises(InvalidStateTransitionError):
            reading.transition_to(ReadingStatus.COMPLETED)

        with pytest.raises(InvalidStateTransitionError):
            reading.transition_to(ReadingStatus.INTERPRETATION_READY)

        # COMPLETED cannot transition to anything
        completed = reading.transition_to(ReadingStatus.IN_PROGRESS).transition_to(
            ReadingStatus.INTERPRETATION_READY, interpretation="Done"
        ).transition_to(ReadingStatus.COMPLETED)

        with pytest.raises(InvalidStateTransitionError):
            completed.transition_to(ReadingStatus.PENDING)

        with pytest.raises(InvalidStateTransitionError):
            completed.transition_to(ReadingStatus.INTERPRETATION_PENDING)


class TestReadingStore:
    """Test in-memory ReadingStore CRUD operations and queries."""

    @pytest.fixture
    def store(self) -> ReadingStore:
        return ReadingStore()

    def test_save_and_get_reading(self, store: ReadingStore) -> None:
        reading = ReadingFactory.create_reading(
            question="Will I pass the test?",
            domain=DomainType.GENERAL,
            spread=ONE_CARD_SPREAD,
            user_id="user_1",
        )
        saved = store.save_reading(reading)
        assert saved.id == reading.id

        fetched = store.get_reading(reading.id)
        assert fetched is not None
        assert fetched.id == reading.id
        assert fetched.question == "Will I pass the test?"

        # Lookup with string UUID
        fetched_str = store.get_reading(str(reading.id))
        assert fetched_str is not None
        assert fetched_str.id == reading.id

    def test_delete_reading(self, store: ReadingStore) -> None:
        reading = ReadingFactory.create_reading(
            question="To be deleted",
            spread=ONE_CARD_SPREAD,
            user_id="user_1",
        )
        store.save_reading(reading)
        assert store.count() == 1

        assert store.delete_reading(reading.id) is True
        assert store.get_reading(reading.id) is None
        assert store.count() == 0
        assert store.delete_reading(reading.id) is False

    def test_list_user_readings_sorted_and_limited(self, store: ReadingStore) -> None:
        r1 = ReadingFactory.create_reading(
            question="Q1",
            spread=ONE_CARD_SPREAD,
            user_id="user_a",
        )
        r2 = ReadingFactory.create_reading(
            question="Q2",
            spread=ONE_CARD_SPREAD,
            user_id="user_a",
        )
        r3 = ReadingFactory.create_reading(
            question="Q3",
            spread=ONE_CARD_SPREAD,
            user_id="user_b",
        )

        store.save_reading(r1)
        store.save_reading(r2)
        store.save_reading(r3)

        user_a_readings = store.list_user_readings("user_a")
        assert len(user_a_readings) == 2
        assert {r.id for r in user_a_readings} == {r1.id, r2.id}

        # Test limit
        limited = store.list_user_readings("user_a", limit=1)
        assert len(limited) == 1

        # Other user
        user_b_readings = store.list_user_readings("user_b")
        assert len(user_b_readings) == 1
        assert user_b_readings[0].id == r3.id

    def test_update_interpretation_in_store(self, store: ReadingStore) -> None:
        reading = ReadingFactory.create_reading(
            question="Store interpretation update",
            spread=ONE_CARD_SPREAD,
            user_id="user_x",
            initial_status=ReadingStatus.INTERPRETATION_PENDING,
        )
        store.save_reading(reading)

        updated = store.update_interpretation(
            reading.id,
            interpretation="Insightful interpretation for user_x.",
        )
        assert updated.status == ReadingStatus.INTERPRETATION_READY
        assert updated.interpretation == "Insightful interpretation for user_x."

        # Fetch from store again to ensure stored copy is updated
        fetched = store.get_reading(reading.id)
        assert fetched is not None
        assert fetched.interpretation == "Insightful interpretation for user_x."
        assert fetched.status == ReadingStatus.INTERPRETATION_READY

    def test_update_missing_reading_raises(self, store: ReadingStore) -> None:
        missing_id = uuid4()
        with pytest.raises(KeyError):
            store.update_interpretation(missing_id, "test")

        with pytest.raises(KeyError):
            store.update_status(missing_id, ReadingStatus.FAILED)
