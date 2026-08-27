"""Unit tests for the 78 RWS Tarot Card Canon."""

import pytest
from src.tarot.canon import (
    RWS_DECK,
    MAJOR_ARCANA,
    WANDS,
    CUPS,
    SWORDS,
    PENTACLES,
    ArcanaType,
    Suit,
    Element,
    get_all_cards,
    get_card_by_id,
    get_card_by_name,
    filter_cards,
)


def test_deck_total_count():
    assert len(RWS_DECK) == 78
    assert len(get_all_cards()) == 78


def test_arcana_distribution():
    assert len(MAJOR_ARCANA) == 22
    assert len(WANDS) == 14
    assert len(CUPS) == 14
    assert len(SWORDS) == 14
    assert len(PENTACLES) == 14

    majors = [c for c in RWS_DECK if c.arcana == ArcanaType.MAJOR]
    minors = [c for c in RWS_DECK if c.arcana == ArcanaType.MINOR]
    assert len(majors) == 22
    assert len(minors) == 56


def test_unique_ids_and_names():
    ids = [c.id for c in RWS_DECK]
    names = [c.name for c in RWS_DECK]
    names_zh = [c.name_zh for c in RWS_DECK]

    assert len(ids) == len(set(ids)), "Card IDs must be unique"
    assert len(names) == len(set(names)), "Card names must be unique"
    assert len(names_zh) == len(set(names_zh)), "Chinese card names must be unique"


def test_card_completeness():
    for card in RWS_DECK:
        assert card.id
        assert card.name
        assert card.name_zh
        assert card.description
        assert card.upright_interpretation
        assert card.reversed_interpretation
        assert len(card.keywords.upright) >= 2
        assert len(card.keywords.reversed) >= 2

        if card.arcana == ArcanaType.MAJOR:
            assert card.suit is None
            assert 0 <= card.number <= 21
        else:
            assert card.suit is not None
            assert 1 <= card.number <= 14


def test_lookups():
    fool = get_card_by_id("the_fool")
    assert fool is not None
    assert fool.name == "The Fool"
    assert fool.name_zh == "愚者"
    assert fool.number == 0

    ace_wands = get_card_by_name("Ace of Wands")
    assert ace_wands is not None
    assert ace_wands.id == "ace_of_wands"
    assert ace_wands.suit == Suit.WANDS

    three_cups = get_card_by_name("圣杯三")
    assert three_cups is not None
    assert three_cups.id == "three_of_cups"


def test_filter_cards():
    wands = filter_cards(suit=Suit.WANDS)
    assert len(wands) == 14

    majors = filter_cards(arcana=ArcanaType.MAJOR)
    assert len(majors) == 22

    water_cards = filter_cards(element=Element.WATER)
    # 14 cups + Major arcana water cards (High Priestess, Chariot, Hanged Man, Death, Moon = 5) -> 19
    assert len(water_cards) >= 14
