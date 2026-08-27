"""RWS Deck aggregation, registry, lookup, and query interface."""

from typing import Dict, List, Optional
from .models import ArcanaType, Element, Suit, TarotCard
from .cards_major import MAJOR_ARCANA
from .cards_wands import WANDS
from .cards_cups import CUPS
from .cards_swords import SWORDS
from .cards_pentacles import PENTACLES

# Complete canonical 78 cards
RWS_DECK: List[TarotCard] = [
    *MAJOR_ARCANA,
    *WANDS,
    *CUPS,
    *SWORDS,
    *PENTACLES,
]

# Quick index by card ID
_CARD_BY_ID: Dict[str, TarotCard] = {card.id: card for card in RWS_DECK}
_CARD_BY_NAME: Dict[str, TarotCard] = {card.name.lower(): card for card in RWS_DECK}
_CARD_BY_ZH_NAME: Dict[str, TarotCard] = {card.name_zh: card for card in RWS_DECK}


def get_all_cards() -> List[TarotCard]:
    """Return a copy of the complete 78 RWS tarot card list."""
    return list(RWS_DECK)


def get_card_by_id(card_id: str) -> Optional[TarotCard]:
    """Retrieve a card by unique ID (e.g. 'the_fool', 'three_of_cups')."""
    return _CARD_BY_ID.get(card_id.strip().lower())


def get_card_by_name(name: str) -> Optional[TarotCard]:
    """Retrieve a card by English or Chinese name."""
    clean_name = name.strip()
    if clean_name in _CARD_BY_ZH_NAME:
        return _CARD_BY_ZH_NAME[clean_name]
    return _CARD_BY_NAME.get(clean_name.lower())


def filter_cards(
    arcana: Optional[ArcanaType] = None,
    suit: Optional[Suit] = None,
    element: Optional[Element] = None,
) -> List[TarotCard]:
    """Filter cards by Arcana type, Suit, or Element."""
    results = RWS_DECK
    if arcana is not None:
        results = [c for c in results if c.arcana == arcana]
    if suit is not None:
        results = [c for c in results if c.suit == suit]
    if element is not None:
        results = [c for c in results if c.element == element]
    return results
