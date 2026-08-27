"""Tarot core module — re-exports the domain card view and adapter.

The canonical card catalogue model lives in `src/tarot/canon/models.py`.
This module keeps the historical `CardView` API surface available by
re-exporting the domain view layer and installing the bidirectional
adapter between `TarotCard` and `Card` / `PipCard` / `TrumpCard`.
"""

from __future__ import annotations

# Import the domain view layer so consumers can continue to use
# `from src.tarot.core import Card, PipCard, TrumpCard`.
from .domain.card_view import (
    Arcana,
    ArcanaType,
    Suit,
    Rank,
    Element,
    SUIT_ELEMENTS,
    RANK_NUMBERS,
    AstrologyCorrespondence,
    OrientedStrings,
    OrientedText,
    CardKeywords,
    CardMeaning,
    CardMeanings,
    ImageryNotes,
    CardMetadata,
    Card,
    PipCard,
    TrumpCard,
    AnyCard,
)

# Importing the adapter installs `.to_card_view()` on TarotCard and
# `.to_tarot_card()` on Card. Keep this import at the bottom to avoid
# shadowing the re-exports above.
from .domain import adapter  # noqa: F401


__all__ = [
    "Arcana",
    "ArcanaType",
    "Suit",
    "Rank",
    "Element",
    "SUIT_ELEMENTS",
    "RANK_NUMBERS",
    "AstrologyCorrespondence",
    "OrientedStrings",
    "OrientedText",
    "CardKeywords",
    "CardMeaning",
    "CardMeanings",
    "ImageryNotes",
    "CardMetadata",
    "Card",
    "PipCard",
    "TrumpCard",
    "AnyCard",
]
