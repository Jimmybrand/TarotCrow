"""Bidirectional adapter between canonical `TarotCard` and domain `CardView`.

The canonical model (`src/tarot/canon.models.TarotCard`) is the single source
of truth for the RWS catalogue. The domain view (`src/tarot.domain.card_view`)
provides a richer, hierarchical representation. This module converts between
the two without modifying either schema.

Conversion notes
----------------
* `TarotCard.name`      → `Card.canonical_name`
* `TarotCard.name_zh`   → `Card.localized_names["zh"]`
* `TarotCard.keywords`  → `Card.keywords`
* `TarotCard.upright_interpretation`  → `Card.meanings.general.upright`
* `TarotCard.reversed_interpretation` → `Card.meanings.general.reversed`
* `TarotCard.astrology` (str) → `AstrologyCorrespondence(notes=...)`
* `TarotCard.suit` is optional; when present the card becomes a `PipCard`.
* `TarotCard.arcana` discriminates Major (`TrumpCard`) vs Minor (`PipCard`).
"""

from __future__ import annotations

from typing import Optional, Union

from ..canon.models import (
    ArcanaType,
    CardMeaning,
    Element,
    Suit,
    TarotCard,
)
from .card_view import (
    Arcana,
    AstrologyCorrespondence,
    Card,
    CardKeywords,
    CardMeanings,
    OrientedText,
    PipCard,
    Rank,
    TrumpCard,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rank_from_number(number: int) -> Rank:
    """Map a Minor Arcana number (1-14) to its Rank enum."""
    for rank, value in {
        Rank.ACE: 1,
        Rank.TWO: 2,
        Rank.THREE: 3,
        Rank.FOUR: 4,
        Rank.FIVE: 5,
        Rank.SIX: 6,
        Rank.SEVEN: 7,
        Rank.EIGHT: 8,
        Rank.NINE: 9,
        Rank.TEN: 10,
        Rank.PAGE: 11,
        Rank.KNIGHT: 12,
        Rank.QUEEN: 13,
        Rank.KING: 14,
    }.items():
        if value == number:
            return rank
    raise ValueError(f"No Rank for Minor Arcana number {number}")


def _number_from_rank(rank: Rank) -> int:
    """Map a Rank enum to its Minor Arcana number (1-14)."""
    from .card_view import RANK_NUMBERS

    return RANK_NUMBERS[rank]


def _canon_arcana_to_domain(arcana: ArcanaType) -> Arcana:
    """Convert canon ArcanaType enum to domain Arcana enum."""
    return Arcana(arcana.value)


def _domain_arcana_to_canon(arcana: Arcana) -> ArcanaType:
    """Convert domain Arcana enum to canon ArcanaType enum."""
    return ArcanaType(arcana.value)


def _canon_element_to_domain(element: Optional[Element]) -> Optional[Element]:
    """Canon and domain share the same Element enum; just pass through."""
    return element


def _canon_suit_to_domain(suit: Optional[Suit]) -> Optional[Suit]:
    """Canon and domain share the same Suit enum; just pass through."""
    return suit


def _canon_card_meaning_to_keywords(meaning: CardMeaning) -> CardKeywords:
    """Convert canon CardMeaning to domain CardKeywords."""
    return CardKeywords(
        upright=list(meaning.upright),
        reversed=list(meaning.reversed),
    )


def _domain_keywords_to_card_meaning(keywords: CardKeywords) -> CardMeaning:
    """Convert domain CardKeywords to canon CardMeaning."""
    return CardMeaning(
        upright=list(keywords.upright),
        reversed=list(keywords.reversed),
    )


def _astrology_to_canon_string(astrology: Optional[AstrologyCorrespondence]) -> Optional[str]:
    """Flatten domain astrology block back to a canon string."""
    if astrology is None:
        return None
    return astrology.as_canon_string()


# ---------------------------------------------------------------------------
# TarotCard → CardView
# ---------------------------------------------------------------------------


def tarot_card_to_card_view(card: TarotCard) -> Union[PipCard, TrumpCard]:
    """Convert a canonical `TarotCard` into a domain `PipCard` or `TrumpCard`."""
    arcana = _canon_arcana_to_domain(card.arcana)
    localized_names: dict[str, str] = {}
    if card.name_zh:
        localized_names["zh"] = card.name_zh

    common_kwargs = {
        "id": card.id,
        "arcana": arcana,
        "number": card.number,
        "canonical_name": card.name,
        "localized_names": localized_names,
        "element": _canon_element_to_domain(card.element),
        "astrology": AstrologyCorrespondence(notes=card.astrology) if card.astrology else None,
        "archetype": card.archetype,
        "keywords": _canon_card_meaning_to_keywords(card.keywords),
        "meanings": CardMeanings(
            general=OrientedText(
                upright=card.upright_interpretation,
                reversed=card.reversed_interpretation,
            )
        ),
        "description": card.description,
    }

    if arcana is Arcana.MINOR:
        if card.suit is None:
            raise ValueError("Minor Arcana TarotCard must have a suit")
        return PipCard(
            **common_kwargs,
            suit=card.suit,
            rank=_rank_from_number(card.number),
        )

    return TrumpCard(**common_kwargs)


# ---------------------------------------------------------------------------
# CardView → TarotCard
# ---------------------------------------------------------------------------


def card_view_to_tarot_card(card: Card) -> TarotCard:
    """Convert a domain `Card` (PipCard or TrumpCard) into a canonical `TarotCard`."""
    name_zh = card.localized_names.get("zh")

    suit: Optional[Suit] = None
    if isinstance(card, PipCard):
        suit = card.suit
    elif isinstance(card, TrumpCard):
        suit = None

    return TarotCard(
        id=card.id,
        name=card.canonical_name,
        name_zh=name_zh or "",
        arcana=_domain_arcana_to_canon(card.arcana),
        number=card.number,
        suit=suit,
        element=_canon_element_to_domain(card.element),
        astrology=_astrology_to_canon_string(card.astrology),
        keywords=_domain_keywords_to_card_meaning(card.keywords),
        archetype=card.archetype,
        description=card.description,
        upright_interpretation=card.meanings.general.upright,
        reversed_interpretation=card.meanings.general.reversed,
    )


# ---------------------------------------------------------------------------
# Convenience methods attached to the models
# ---------------------------------------------------------------------------


def _install_adapters() -> None:
    """Wire adapter methods onto the canonical and domain models.

    This keeps the conversion API discoverable while avoiding circular
    imports inside the model modules themselves.
    """
    TarotCard.to_card_view = tarot_card_to_card_view  # type: ignore[attr-defined]
    Card.to_tarot_card = card_view_to_tarot_card  # type: ignore[attr-defined]


_install_adapters()
