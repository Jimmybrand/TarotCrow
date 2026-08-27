"""Data models and enums for Rider-Waite-Smith (RWS) Tarot Canon."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ArcanaType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"


class Suit(str, Enum):
    WANDS = "wands"
    CUPS = "cups"
    SWORDS = "swords"
    PENTACLES = "pentacles"


class Element(str, Enum):
    FIRE = "fire"
    WATER = "water"
    AIR = "air"
    EARTH = "earth"
    SPIRIT = "spirit"


class CardMeaning(BaseModel):
    upright: List[str] = Field(
        default_factory=list,
        description="Key themes and keywords when upright",
    )
    reversed: List[str] = Field(
        default_factory=list,
        description="Key themes and keywords when reversed",
    )


class TarotCard(BaseModel):
    id: str = Field(..., description="Unique card identifier, e.g., 'the_fool', 'ace_of_wands'")
    name: str = Field(..., description="English card name")
    name_zh: str = Field(..., description="Chinese card name")
    arcana: ArcanaType = Field(..., description="Major or Minor Arcana")
    number: int = Field(..., description="Card number (0-21 for Major, 1-14 for Minor)")
    suit: Optional[Suit] = Field(None, description="Suit if Minor Arcana")
    element: Optional[Element] = Field(None, description="Associated elemental energy")
    astrology: Optional[str] = Field(None, description="Astrological correspondence or zodiac/planet")
    keywords: CardMeaning = Field(..., description="Upright and reversed keywords")
    archetype: Optional[str] = Field(None, description="Symbolic archetype or core motif")
    description: str = Field(..., description="Visual symbolism description in RWS deck")
    upright_interpretation: str = Field(..., description="Detailed upright reading interpretation")
    reversed_interpretation: str = Field(..., description="Detailed reversed reading interpretation")
