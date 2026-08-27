"""Data models for the Tarot knowledge base."""

from __future__ import annotations

from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, model_validator


class Suit(str, Enum):
    """The four tarot suits of the Minor Arcana."""

    WANDS = "wands"
    CUPS = "cups"
    SWORDS = "swords"
    PENTACLES = "pentacles"


class Arcana(str, Enum):
    """Major or Minor Arcana classification."""

    MAJOR = "major"
    MINOR = "minor"


class Element(str, Enum):
    """Classical elemental associations."""

    FIRE = "fire"
    WATER = "water"
    AIR = "air"
    EARTH = "earth"


class Planet(str, Enum):
    """Astrological planet associations."""

    MERCURY = "mercury"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    PLUTO = "pluto"
    SUN = "sun"
    MOON = "moon"


class Zodiac(str, Enum):
    """Zodiac sign associations."""

    ARIES = "aries"
    TAURUS = "taurus"
    GEMINI = "gemini"
    CANCER = "cancer"
    LEO = "leo"
    VIRGO = "virgo"
    LIBRA = "libra"
    SCORPIO = "scorpio"
    SAGITTARIUS = "sagittarius"
    CAPRICORN = "capricorn"
    AQUARIUS = "aquarius"
    PISCES = "pisces"


class CardOrientation(str, Enum):
    """Orientation of a drawn card."""

    UPRIGHT = "upright"
    REVERSED = "reversed"


class TarotCard(BaseModel):
    """A single tarot card with upright and reversed meanings."""

    id: str = Field(..., description="URL-safe unique identifier, e.g. 'the-fool'.")
    name: str = Field(..., description="Display name of the card.")
    number: int | None = Field(
        None,
        description="Major Arcana number (0-21) or Minor Arcana rank (1-10/11-14).",
    )
    arcana: Arcana = Field(..., description="Major or Minor Arcana.")
    suit: Suit | None = Field(None, description="Minor Arcana suit, if applicable.")
    element: Element | None = Field(None, description="Elemental association.")
    planet: Planet | None = Field(None, description="Astrological planet association.")
    zodiac: Zodiac | None = Field(None, description="Zodiac sign association.")
    keywords: list[str] = Field(default_factory=list, description="Core keywords.")
    upright_meaning: str = Field(..., description="Upright interpretation.")
    reversed_meaning: str = Field(..., description="Reversed interpretation.")
    description: str = Field(default="", description="Narrative description of imagery.")
    advice: str = Field(default="", description="Practical guidance for the querent.")

    @model_validator(mode="after")
    def _validate_arcana_consistency(self) -> Self:
        if self.arcana == Arcana.MINOR and self.suit is None:
            raise ValueError("Minor Arcana cards must have a suit.")
        if self.arcana == Arcana.MAJOR and self.suit is not None:
            raise ValueError("Major Arcana cards must not have a suit.")
        return self

    def meaning(self, orientation: CardOrientation = CardOrientation.UPRIGHT) -> str:
        """Return the meaning for a given orientation."""
        if orientation == CardOrientation.REVERSED:
            return self.reversed_meaning
        return self.upright_meaning


class SpreadPosition(BaseModel):
    """A named position within a tarot spread."""

    name: str = Field(..., description="Name of the position, e.g. 'Past'.")
    description: str = Field(..., description="What the position represents.")
    order: int = Field(..., ge=0, description="Zero-based order in the spread.")


class Spread(BaseModel):
    """A tarot spread definition."""

    id: str = Field(..., description="URL-safe unique identifier.")
    name: str = Field(..., description="Display name of the spread.")
    description: str = Field(default="", description="Overview of the spread.")
    positions: list[SpreadPosition] = Field(
        default_factory=list,
        min_length=1,
        description="Ordered positions in the spread.",
    )

    @model_validator(mode="after")
    def _validate_positions(self) -> Self:
        orders = [p.order for p in self.positions]
        if orders != sorted(orders):
            raise ValueError("Spread positions must be sorted by order.")
        if len(set(orders)) != len(orders):
            raise ValueError("Spread position orders must be unique.")
        return self


class DrawnCard(BaseModel):
    """A card drawn in a specific orientation for a spread position."""

    card: TarotCard
    orientation: CardOrientation = CardOrientation.UPRIGHT
    position: SpreadPosition | None = None
