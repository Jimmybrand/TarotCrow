"""Domain view layer for tarot cards.

This package provides a richer, hierarchical view of a tarot card
(`Card`, `PipCard`, `TrumpCard`) that is kept separate from the
canonical flat catalogue model in `src/tarot/canon/models.py`.

Adapters in `src/tarot/domain/adapter.py` convert between the two
representations without modifying either schema.
"""

from .card_view import (
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
