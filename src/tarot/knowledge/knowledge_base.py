"""Lookup and query utilities for the tarot knowledge base."""

from __future__ import annotations

from collections.abc import Sequence
from typing import overload

from tarot.knowledge.cards import ALL_CARDS
from tarot.knowledge.models import (
    Arcana,
    CardOrientation,
    DrawnCard,
    Element,
    Planet,
    Spread,
    Suit,
    TarotCard,
    Zodiac,
)
from tarot.knowledge.spreads import ALL_SPREADS


class KnowledgeBase:
    """In-memory repository for tarot cards and spreads."""

    def __init__(
        self,
        cards: Sequence[TarotCard] | None = None,
        spreads: Sequence[Spread] | None = None,
    ) -> None:
        cards = list(cards if cards is not None else ALL_CARDS)
        spreads = list(spreads if spreads is not None else ALL_SPREADS)

        self._cards_by_id: dict[str, TarotCard] = {}
        self._cards_by_name: dict[str, TarotCard] = {}
        for card in cards:
            if card.id in self._cards_by_id:
                raise ValueError(f"Duplicate card id: {card.id}")
            self._cards_by_id[card.id] = card
            self._cards_by_name[card.name.lower()] = card

        self._spreads_by_id: dict[str, Spread] = {}
        for spread in spreads:
            if spread.id in self._spreads_by_id:
                raise ValueError(f"Duplicate spread id: {spread.id}")
            self._spreads_by_id[spread.id] = spread

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------
    @property
    def cards(self) -> list[TarotCard]:
        """Return all cards in canonical order."""
        return list(self._cards_by_id.values())

    @property
    def major_arcana(self) -> list[TarotCard]:
        """Return all Major Arcana cards."""
        return [card for card in self.cards if card.arcana == Arcana.MAJOR]

    @property
    def minor_arcana(self) -> list[TarotCard]:
        """Return all Minor Arcana cards."""
        return [card for card in self.cards if card.arcana == Arcana.MINOR]

    def get_card(self, card_id: str) -> TarotCard:
        """Fetch a card by its URL-safe id.

        Raises:
            KeyError: If no card with the given id exists.
        """
        try:
            return self._cards_by_id[card_id]
        except KeyError as exc:
            raise KeyError(f"Card not found: {card_id}") from exc

    def find_card_by_name(self, name: str) -> TarotCard:
        """Fetch a card by display name (case-insensitive).

        Raises:
            KeyError: If no card with the given name exists.
        """
        key = name.lower()
        if key in self._cards_by_name:
            return self._cards_by_name[key]
        raise KeyError(f"Card not found by name: {name}")

    def filter_cards(
        self,
        *,
        arcana: Arcana | None = None,
        suit: Suit | None = None,
        element: Element | None = None,
        planet: Planet | None = None,
        zodiac: Zodiac | None = None,
        keyword: str | None = None,
    ) -> list[TarotCard]:
        """Return cards matching all provided criteria."""
        results = self.cards
        if arcana is not None:
            results = [c for c in results if c.arcana == arcana]
        if suit is not None:
            results = [c for c in results if c.suit == suit]
        if element is not None:
            results = [c for c in results if c.element == element]
        if planet is not None:
            results = [c for c in results if c.planet == planet]
        if zodiac is not None:
            results = [c for c in results if c.zodiac == zodiac]
        if keyword is not None:
            needle = keyword.lower()
            results = [c for c in results if any(needle in kw.lower() for kw in c.keywords)]
        return results

    def search_cards(self, query: str) -> list[TarotCard]:
        """Search cards by name, keywords, or meaning text.

        The query is split on whitespace; every token must match somewhere
        in the card's searchable text.
        """
        tokens = [token.lower() for token in query.split() if token]
        if not tokens:
            return self.cards

        matches: list[TarotCard] = []
        for card in self.cards:
            haystack = " ".join(
                [
                    card.id,
                    card.name,
                    *card.keywords,
                    card.upright_meaning,
                    card.reversed_meaning,
                    card.description,
                    card.advice,
                ]
            ).lower()
            if all(token in haystack for token in tokens):
                matches.append(card)
        return matches

    # ------------------------------------------------------------------
    # Spreads
    # ------------------------------------------------------------------
    @property
    def spreads(self) -> list[Spread]:
        """Return all spreads."""
        return list(self._spreads_by_id.values())

    def get_spread(self, spread_id: str) -> Spread:
        """Fetch a spread by its URL-safe id.

        Raises:
            KeyError: If no spread with the given id exists.
        """
        try:
            return self._spreads_by_id[spread_id]
        except KeyError as exc:
            raise KeyError(f"Spread not found: {spread_id}") from exc

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(
        self,
        card_id: str,
        orientation: CardOrientation = CardOrientation.UPRIGHT,
    ) -> DrawnCard:
        """Create a DrawnCard from a card id and orientation."""
        card = self.get_card(card_id)
        return DrawnCard(card=card, orientation=orientation)


# Singleton-like default instance for convenience.
_default_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    """Return the default knowledge base populated with all cards and spreads."""
    global _default_kb  # noqa: PLW0603
    if _default_kb is None:
        _default_kb = KnowledgeBase()
    return _default_kb


@overload
def get_card(card_id: str) -> TarotCard: ...


@overload
def get_card(card_id: str, default: TarotCard) -> TarotCard: ...


def get_card(card_id: str, default: TarotCard | None = None) -> TarotCard:
    """Convenience lookup for a card by id using the default knowledge base."""
    try:
        return get_knowledge_base().get_card(card_id)
    except KeyError:
        if default is not None:
            return default
        raise
