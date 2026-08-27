"""Reading domain models, factory, in-memory store, and lifecycle state machine."""

from __future__ import annotations

import random
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional, Sequence, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tarot.canon.deck import RWS_DECK
from tarot.canon.models import TarotCard as CanonTarotCard
from tarot.knowledge.models import (
    CardOrientation,
    Spread,
    SpreadPosition,
)
from tarot.knowledge.models import (
    TarotCard as KnowledgeTarotCard,
)


class DomainType(str, Enum):
    """Life area or reading domain classification."""

    GENERAL = "general"
    CAREER = "career"
    LOVE = "love"
    RELATIONSHIPS = "relationships"
    FINANCE = "finance"
    HEALTH = "health"
    SPIRITUAL = "spiritual"
    PERSONAL_GROWTH = "personal_growth"
    DECISION = "decision"
    PETS = "pets"


class ReadingStatus(str, Enum):
    """Lifecycle states of a tarot reading."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    INTERPRETATION_PENDING = "INTERPRETATION_PENDING"
    INTERPRETATION_READY = "INTERPRETATION_READY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Valid state transitions
_VALID_TRANSITIONS: dict[ReadingStatus, set[ReadingStatus]] = {
    ReadingStatus.PENDING: {
        ReadingStatus.IN_PROGRESS,
        ReadingStatus.FAILED,
    },
    ReadingStatus.IN_PROGRESS: {
        ReadingStatus.INTERPRETATION_PENDING,
        ReadingStatus.INTERPRETATION_READY,
        ReadingStatus.FAILED,
    },
    ReadingStatus.INTERPRETATION_PENDING: {
        ReadingStatus.INTERPRETATION_READY,
        ReadingStatus.FAILED,
    },
    ReadingStatus.INTERPRETATION_READY: {
        ReadingStatus.COMPLETED,
        ReadingStatus.INTERPRETATION_PENDING,
        ReadingStatus.FAILED,
    },
    ReadingStatus.COMPLETED: set(),  # Terminal state
    ReadingStatus.FAILED: {
        ReadingStatus.INTERPRETATION_PENDING,
        ReadingStatus.IN_PROGRESS,
    },  # Allow retry on failure
}


class InvalidStateTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""


class DrawnCard(BaseModel):
    """A card drawn in a reading."""

    model_config = ConfigDict(frozen=True)

    card_id: str = Field(
        ...,
        description="Unique card identifier, e.g., 'the_fool' or 'the-fool'",
    )
    orientation: CardOrientation = Field(
        default=CardOrientation.UPRIGHT,
        description="Card orientation (upright or reversed)",
    )
    position: Optional[SpreadPosition] = Field(
        default=None,
        description="Spread position if applicable",
    )
    draw_order: int = Field(
        ...,
        ge=0,
        description="Zero-based draw order sequence in the reading",
    )


class Reading(BaseModel):
    """Immutable Tarot Reading data model representing the full reading session."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique reading identifier",
    )
    user_id: str = Field(..., description="ID of the user who owns this reading")
    session_id: str = Field(
        ...,
        description="Session identifier for grouping interactions",
    )
    question: str = Field(..., description="Raw question asked by the user")
    normalized_question: str = Field(
        default="",
        description="Normalized or cleaned question text",
    )
    domain: DomainType = Field(
        default=DomainType.GENERAL,
        description="Domain or life area of the question",
    )
    spread: Spread = Field(..., description="Spread layout used for the reading")
    cards: tuple[DrawnCard, ...] = Field(
        default_factory=tuple,
        description="Immutable sequence of drawn cards",
    )
    random_seed: Optional[int] = Field(
        default=None,
        description="Random seed used for deterministic card draw and auditing",
    )
    audit_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Audit information, engine details, timestamps, etc.",
    )
    knowledge_context: Optional[Union[str, dict[str, Any]]] = Field(
        default=None,
        description="Domain/memory/knowledge context retrieved for the reading",
    )
    interpretation: Optional[str] = Field(
        default=None,
        description="AI or reader interpretation text; None initially",
    )
    status: ReadingStatus = Field(
        default=ReadingStatus.PENDING,
        description="Current reading lifecycle status",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    related_readings: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="IDs of related prior or subsequent readings",
    )

    @field_validator("cards", mode="before")
    @classmethod
    def _coerce_cards(cls, v: Any) -> tuple[DrawnCard, ...]:
        if isinstance(v, (list, tuple, set)):
            return tuple(v)
        return v

    @field_validator("related_readings", mode="before")
    @classmethod
    def _coerce_related_readings(cls, v: Any) -> tuple[UUID, ...]:
        if isinstance(v, (list, tuple, set)):
            return tuple(v)
        return v

    def transition_to(
        self,
        new_status: ReadingStatus,
        *,
        interpretation: Optional[str] = None,
        audit_metadata_update: Optional[dict[str, Any]] = None,
    ) -> Reading:
        """Create a new Reading instance with a transitioned state.

        Enforces:
        - State transition legality
        - Immutability of cards / orientations (cards cannot be changed during transition)
        - Handling of interpretation updates
        """
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed and new_status != self.status:
            raise InvalidStateTransitionError(
                f"Cannot transition from {self.status.value} to {new_status.value}"
            )

        new_audit = dict(self.audit_metadata)
        if audit_metadata_update:
            new_audit.update(audit_metadata_update)

        new_interpretation = self.interpretation if interpretation is None else interpretation

        return self.model_copy(
            update={
                "status": new_status,
                "interpretation": new_interpretation,
                "audit_metadata": new_audit,
            }
        )

    def with_interpretation(self, interpretation: str) -> Reading:
        """Update interpretation and transition status if appropriate."""
        return self.transition_to(
            ReadingStatus.INTERPRETATION_READY,
            interpretation=interpretation,
        )

    def mark_failed(self, error_message: str = "") -> Reading:
        """Mark the reading as failed (e.g. AI generation error) without modifying cards."""
        update_audit = {"last_error": error_message} if error_message else {}
        return self.transition_to(
            ReadingStatus.FAILED,
            audit_metadata_update=update_audit,
        )

    def retry_interpretation(self) -> Reading:
        """Transition from FAILED, READY, or IN_PROGRESS to INTERPRETATION_PENDING.

        Cards remain untouched.
        """
        valid_sources = (
            ReadingStatus.FAILED,
            ReadingStatus.INTERPRETATION_READY,
            ReadingStatus.IN_PROGRESS,
        )
        if self.status not in valid_sources:
            raise InvalidStateTransitionError(
                f"Cannot retry interpretation from status {self.status.value}"
            )
        return self.transition_to(ReadingStatus.INTERPRETATION_PENDING)


# Type aliases for custom engine functions
DrawEngine = Callable[[Sequence[Any], int, random.Random], list[Any]]
OrientationEngine = Callable[[int, random.Random], list[CardOrientation]]


def default_draw_engine(
    deck: Sequence[Any],
    count: int,
    rng: random.Random,
) -> list[Any]:
    """Default draw engine: sample without replacement."""
    if count > len(deck):
        raise ValueError(f"Cannot draw {count} cards from a deck of size {len(deck)}")
    return rng.sample(list(deck), count)


def default_orientation_engine(
    count: int,
    rng: random.Random,
) -> list[CardOrientation]:
    """Default orientation engine: independent 50/50 upright/reversed."""
    return [
        CardOrientation.REVERSED if rng.random() < 0.5 else CardOrientation.UPRIGHT
        for _ in range(count)
    ]


class ReadingFactory:
    """Factory for creating Reading instances with non-replacement card draws."""

    @staticmethod
    def create_reading(
        question: str,
        spread: Spread,
        *,
        user_id: str = "anonymous",
        session_id: Optional[str] = None,
        domain: DomainType = DomainType.GENERAL,
        deck: Optional[Sequence[Union[CanonTarotCard, KnowledgeTarotCard, str]]] = None,
        draw_engine: Optional[DrawEngine] = None,
        orientation_engine: Optional[OrientationEngine] = None,
        random_seed: Optional[int] = None,
        knowledge_context: Optional[Union[str, dict[str, Any]]] = None,
        related_readings: Optional[Sequence[UUID]] = None,
        normalized_question: Optional[str] = None,
        initial_status: ReadingStatus = ReadingStatus.IN_PROGRESS,
    ) -> Reading:
        """Create an immutable Reading with drawn cards.

        Args:
            question: User's question.
            spread: Tarot spread layout defining position count.
            user_id: User identifier.
            session_id: Session identifier (auto-generated if None).
            domain: DomainType category.
            deck: Sequence of cards or card IDs. Defaults to canonical 78 RWS cards.
            draw_engine: Function (deck, count, rng) -> drawn_items.
            orientation_engine: Function (count, rng) -> orientations.
            random_seed: Seed for reproducibility and audit.
            knowledge_context: Associated context/memories.
            related_readings: Associated prior reading UUIDs.
            normalized_question: Pre-processed question string.
            initial_status: Initial ReadingStatus (defaults to IN_PROGRESS after draw).

        Returns:
            Immutable Reading instance.
        """
        rng = random.Random(random_seed)
        num_cards = len(spread.positions)

        # Standardise deck to card ids
        source_deck: Sequence[Any] = deck if deck is not None else RWS_DECK
        if len(source_deck) < num_cards:
            raise ValueError(
                f"Deck size ({len(source_deck)}) is smaller than required "
                f"spread positions ({num_cards})"
            )

        draw_fn = draw_engine or default_draw_engine
        drawn_cards_raw = draw_fn(source_deck, num_cards, rng)

        # Ensure no duplicates (draw without replacement)
        drawn_card_ids: list[str] = []
        for c in drawn_cards_raw:
            if hasattr(c, "id"):
                cid = c.id
            elif isinstance(c, str):
                cid = c
            else:
                cid = str(c)
            drawn_card_ids.append(cid)

        if len(set(drawn_card_ids)) != len(drawn_card_ids):
            raise ValueError("Draw engine produced duplicate cards (must be without replacement)")

        orient_fn = orientation_engine or default_orientation_engine
        orientations = orient_fn(num_cards, rng)

        drawn_card_models: list[DrawnCard] = []
        for i, (cid, orient) in enumerate(zip(drawn_card_ids, orientations)):
            pos = spread.positions[i] if i < len(spread.positions) else None
            drawn_card_models.append(
                DrawnCard(
                    card_id=cid,
                    orientation=orient,
                    position=pos,
                    draw_order=i,
                )
            )

        audit = {
            "draw_engine": getattr(draw_fn, "__name__", str(draw_fn)),
            "orientation_engine": getattr(orient_fn, "__name__", str(orient_fn)),
            "card_count": num_cards,
        }

        return Reading(
            id=uuid4(),
            user_id=user_id,
            session_id=session_id or str(uuid4()),
            question=question,
            normalized_question=normalized_question or question.strip(),
            domain=domain,
            spread=spread,
            cards=tuple(drawn_card_models),
            random_seed=random_seed,
            audit_metadata=audit,
            knowledge_context=knowledge_context,
            interpretation=None,
            status=initial_status,
            created_at=datetime.now(timezone.utc),
            related_readings=tuple(related_readings or ()),
        )


class ReadingStore:
    """Thread-safe In-memory Reading store with lookup, persistence, and querying."""

    def __init__(self) -> None:
        self._readings: dict[UUID, Reading] = {}
        self._lock = threading.RLock()

    def save_reading(self, reading: Reading) -> Reading:
        """Save or overwrite a reading in the store."""
        with self._lock:
            self._readings[reading.id] = reading
            return reading

    def get_reading(self, reading_id: Union[UUID, str]) -> Optional[Reading]:
        """Retrieve a reading by its UUID or UUID string."""
        uid = UUID(str(reading_id)) if not isinstance(reading_id, UUID) else reading_id
        with self._lock:
            return self._readings.get(uid)

    def delete_reading(self, reading_id: Union[UUID, str]) -> bool:
        """Delete a reading by ID. Returns True if deleted."""
        uid = UUID(str(reading_id)) if not isinstance(reading_id, UUID) else reading_id
        with self._lock:
            return self._readings.pop(uid, None) is not None

    def list_user_readings(
        self,
        user_id: str,
        limit: Optional[int] = None,
    ) -> list[Reading]:
        """List readings belonging to a user, sorted newest first."""
        with self._lock:
            user_readings = [
                r for r in self._readings.values() if r.user_id == user_id
            ]
            user_readings.sort(key=lambda r: r.created_at, reverse=True)
            if limit is not None:
                return user_readings[:limit]
            return user_readings

    def update_interpretation(
        self,
        reading_id: Union[UUID, str],
        interpretation: str,
        new_status: ReadingStatus = ReadingStatus.INTERPRETATION_READY,
    ) -> Reading:
        """Update reading interpretation and transition state.

        Raises KeyError if reading is not found.
        Raises InvalidStateTransitionError if transition is invalid.
        """
        uid = UUID(str(reading_id)) if not isinstance(reading_id, UUID) else reading_id
        with self._lock:
            existing = self._readings.get(uid)
            if existing is None:
                raise KeyError(f"Reading {uid} not found")

            updated = existing.transition_to(
                new_status=new_status,
                interpretation=interpretation,
            )
            self._readings[uid] = updated
            return updated

    def update_status(
        self,
        reading_id: Union[UUID, str],
        new_status: ReadingStatus,
        *,
        error_message: Optional[str] = None,
    ) -> Reading:
        """Update status of a reading in store."""
        uid = UUID(str(reading_id)) if not isinstance(reading_id, UUID) else reading_id
        with self._lock:
            existing = self._readings.get(uid)
            if existing is None:
                raise KeyError(f"Reading {uid} not found")

            audit_update = {"last_error": error_message} if error_message else None
            updated = existing.transition_to(
                new_status=new_status,
                audit_metadata_update=audit_update,
            )
            self._readings[uid] = updated
            return updated

    def clear(self) -> None:
        """Clear all readings from store."""
        with self._lock:
            self._readings.clear()

    def count(self) -> int:
        """Count total readings in store."""
        with self._lock:
            return len(self._readings)


__all__ = [
    "DomainType",
    "ReadingStatus",
    "InvalidStateTransitionError",
    "DrawnCard",
    "Reading",
    "ReadingFactory",
    "ReadingStore",
    "DrawEngine",
    "OrientationEngine",
    "default_draw_engine",
    "default_orientation_engine",
]
