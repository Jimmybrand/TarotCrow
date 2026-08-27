"""Tests for the tarot knowledge base."""

from __future__ import annotations

import pytest

from tarot.knowledge import (
    ALL_CARDS,
    Arcana,
    CardOrientation,
    Element,
    KnowledgeBase,
    Suit,
    TarotCard,
    get_card,
    get_knowledge_base,
)
from tarot.knowledge.cards import MAJOR_ARCANA, MINOR_ARCANA
from tarot.knowledge.models import Spread, SpreadPosition


class TestCardData:
    """Sanity checks on the bundled card definitions."""

    def test_total_card_count(self) -> None:
        assert len(ALL_CARDS) == 78
        assert len(MAJOR_ARCANA) == 22
        assert len(MINOR_ARCANA) == 56

    def test_unique_card_ids(self) -> None:
        ids = [card.id for card in ALL_CARDS]
        assert len(ids) == len(set(ids))

    def test_major_arcana_have_no_suit(self) -> None:
        for card in MAJOR_ARCANA:
            assert card.suit is None
            assert card.arcana == Arcana.MAJOR

    def test_minor_arcana_have_suit(self) -> None:
        for card in MINOR_ARCANA:
            assert card.suit is not None
            assert card.arcana == Arcana.MINOR

    def test_minor_arcana_counts_per_suit(self) -> None:
        for suit in Suit:
            count = sum(1 for card in MINOR_ARCANA if card.suit == suit)
            assert count == 14, f"Expected 14 cards in {suit.value}"

    def test_meaning_orientation(self) -> None:
        fool = get_card("the-fool")
        assert "leap of faith" in fool.meaning(CardOrientation.UPRIGHT).lower()
        assert "reckless" in fool.meaning(CardOrientation.REVERSED).lower()


class TestKnowledgeBase:
    """Tests for KnowledgeBase lookup and filtering."""

    @pytest.fixture
    def kb(self) -> KnowledgeBase:
        return get_knowledge_base()

    def test_get_card_by_id(self, kb: KnowledgeBase) -> None:
        card = kb.get_card("the-magician")
        assert card.name == "The Magician"

    def test_get_card_missing(self, kb: KnowledgeBase) -> None:
        with pytest.raises(KeyError):
            kb.get_card("not-a-card")

    def test_find_card_by_name_case_insensitive(self, kb: KnowledgeBase) -> None:
        assert kb.find_card_by_name("THE FOOL").id == "the-fool"
        assert kb.find_card_by_name("the fool").id == "the-fool"

    def test_filter_by_arcana(self, kb: KnowledgeBase) -> None:
        majors = kb.filter_cards(arcana=Arcana.MAJOR)
        assert len(majors) == 22
        assert all(card.arcana == Arcana.MAJOR for card in majors)

    def test_filter_by_suit(self, kb: KnowledgeBase) -> None:
        cups = kb.filter_cards(suit=Suit.CUPS)
        assert len(cups) == 14

    def test_filter_by_element(self, kb: KnowledgeBase) -> None:
        fire = kb.filter_cards(element=Element.FIRE)
        assert all(card.element == Element.FIRE for card in fire)

    def test_filter_by_keyword(self, kb: KnowledgeBase) -> None:
        results = kb.filter_cards(keyword="love")
        assert any(card.id == "the-lovers" for card in results)

    def test_filter_combined(self, kb: KnowledgeBase) -> None:
        results = kb.filter_cards(suit=Suit.WANDS, keyword="action")
        assert all(card.suit == Suit.WANDS for card in results)
        assert all(any("action" in kw.lower() for kw in card.keywords) for card in results)

    def test_search_cards(self, kb: KnowledgeBase) -> None:
        results = kb.search_cards("abundance pentacles")
        assert any(card.suit == Suit.PENTACLES for card in results)

    def test_search_empty_query_returns_all(self, kb: KnowledgeBase) -> None:
        assert len(kb.search_cards("")) == len(ALL_CARDS)

    def test_get_spread(self, kb: KnowledgeBase) -> None:
        spread = kb.get_spread("celtic-cross")
        assert spread.name == "Celtic Cross"
        assert len(spread.positions) == 10

    def test_get_spread_missing(self, kb: KnowledgeBase) -> None:
        with pytest.raises(KeyError):
            kb.get_spread("not-a-spread")

    def test_draw(self, kb: KnowledgeBase) -> None:
        drawn = kb.draw("the-star", CardOrientation.REVERSED)
        assert drawn.card.id == "the-star"
        assert drawn.orientation == CardOrientation.REVERSED

    def test_duplicate_card_id_raises(self) -> None:
        card = TarotCard(
            id="the-fool",
            name="Duplicate Fool",
            number=0,
            arcana=Arcana.MAJOR,
            upright_meaning="...",
            reversed_meaning="...",
        )
        with pytest.raises(ValueError, match="Duplicate card id"):
            KnowledgeBase(cards=[card, card])

    def test_duplicate_spread_id_raises(self) -> None:
        spread = Spread(
            id="one-card",
            name="One",
            positions=[SpreadPosition(name="A", description="B", order=0)],
        )
        with pytest.raises(ValueError, match="Duplicate spread id"):
            KnowledgeBase(spreads=[spread, spread])


class TestModels:
    """Tests for model validation."""

    def test_minor_requires_suit(self) -> None:
        with pytest.raises(ValueError):
            TarotCard(
                id="bad-minor",
                name="Bad Minor",
                number=1,
                arcana=Arcana.MINOR,
                upright_meaning="...",
                reversed_meaning="...",
            )

    def test_major_must_not_have_suit(self) -> None:
        with pytest.raises(ValueError):
            TarotCard(
                id="bad-major",
                name="Bad Major",
                number=1,
                arcana=Arcana.MAJOR,
                suit=Suit.CUPS,
                upright_meaning="...",
                reversed_meaning="...",
            )

    def test_spread_positions_must_be_sorted(self) -> None:
        with pytest.raises(ValueError):
            Spread(
                id="bad",
                name="Bad",
                positions=[
                    SpreadPosition(name="Second", description="...", order=1),
                    SpreadPosition(name="First", description="...", order=0),
                ],
            )

    def test_spread_positions_must_be_unique(self) -> None:
        with pytest.raises(ValueError):
            Spread(
                id="bad",
                name="Bad",
                positions=[
                    SpreadPosition(name="A", description="...", order=0),
                    SpreadPosition(name="B", description="...", order=0),
                ],
            )
