"""Tarot card domain model (RWS-oriented, extensible).

Unified schema merging:

* ``canon.models.TarotCard`` — flat RWS catalogue fields
  (name / name_zh / description / upright|reversed interpretation)
* B2 ``Card`` hierarchy — Pip/Trump discrimination, rank, structured
  meanings, imagery, and ``metadata`` extension

Defines:

* ``Card`` — shared identity, correspondences, meanings, and metadata
* ``PipCard`` — Minor Arcana (suit + rank; Ace–10 and court)
* ``TrumpCard`` — Major Arcana / trumps (numbers 0–21)

Canon interop aliases: ``ArcanaType``, ``CardMeaning``.
Convenience properties mirror TarotCard: ``name``, ``name_zh``,
``upright_interpretation``, ``reversed_interpretation``.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ---------------------------------------------------------------------------
# Enums (Rider-Waite-Smith conventions)
# ---------------------------------------------------------------------------


class Arcana(str, Enum):
    """Major vs Minor Arcana."""

    MAJOR = "major"
    MINOR = "minor"


# Canon alias (models.ArcanaType)
ArcanaType = Arcana


class Suit(str, Enum):
    """Four suits of the Minor Arcana (RWS)."""

    WANDS = "wands"
    CUPS = "cups"
    SWORDS = "swords"
    PENTACLES = "pentacles"


class Rank(str, Enum):
    """Pip and court ranks within a suit."""

    ACE = "ace"
    TWO = "two"
    THREE = "three"
    FOUR = "four"
    FIVE = "five"
    SIX = "six"
    SEVEN = "seven"
    EIGHT = "eight"
    NINE = "nine"
    TEN = "ten"
    PAGE = "page"
    KNIGHT = "knight"
    QUEEN = "queen"
    KING = "king"


class Element(str, Enum):
    """Classical elements; SPIRIT is used for some Major Arcana."""

    FIRE = "fire"
    WATER = "water"
    AIR = "air"
    EARTH = "earth"
    SPIRIT = "spirit"


# Suit → element (RWS elemental attributions)
SUIT_ELEMENTS: dict[Suit, Element] = {
    Suit.WANDS: Element.FIRE,
    Suit.CUPS: Element.WATER,
    Suit.SWORDS: Element.AIR,
    Suit.PENTACLES: Element.EARTH,
}

# Rank → Minor Arcana number (Ace=1 … King=14)
RANK_NUMBERS: dict[Rank, int] = {
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
}


# ---------------------------------------------------------------------------
# Nested / composable value objects
# ---------------------------------------------------------------------------


class AstrologyCorrespondence(BaseModel):
    """Astrological links (planet, sign, decan, or free-form notes).

    Canon ``TarotCard.astrology`` is a plain string; coerce via
    ``AstrologyCorrespondence(notes=...)`` or Card's str validator.
    """

    model_config = ConfigDict(extra="allow")

    planet: Optional[str] = Field(default=None, description="Planetary ruler or correspondence")
    zodiac: Optional[str] = Field(default=None, description="Zodiac sign or modality link")
    decan: Optional[str] = Field(default=None, description="Decan / face attribution if used")
    notes: Optional[str] = Field(default=None, description="Additional astrological notes")

    def as_canon_string(self) -> Optional[str]:
        """Flatten to a single string compatible with TarotCard.astrology."""
        parts = [p for p in (self.planet, self.zodiac, self.decan, self.notes) if p]
        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        return " / ".join(parts)


class OrientedStrings(BaseModel):
    """Upright / reversed string lists (keywords, advice fragments, etc.)."""

    model_config = ConfigDict(extra="allow")

    upright: list[str] = Field(default_factory=list)
    reversed: list[str] = Field(default_factory=list)


class OrientedText(BaseModel):
    """Upright / reversed prose meanings."""

    model_config = ConfigDict(extra="allow")

    upright: str = ""
    reversed: str = ""


class CardKeywords(OrientedStrings):
    """Primary upright / reversed keywords (canon CardMeaning shape)."""


# Canon alias (models.CardMeaning)
CardMeaning = CardKeywords


class CardMeanings(BaseModel):
    """Layered meanings: general prose plus optional per-domain overlays.

    ``general`` holds canon upright_interpretation / reversed_interpretation.
    ``by_domain`` keys are free-form (e.g. love, career, health, spiritual)
    so new reading domains can be added without schema migration.
    """

    model_config = ConfigDict(extra="allow")

    general: OrientedText = Field(default_factory=OrientedText)
    by_domain: dict[str, OrientedText] = Field(
        default_factory=dict,
        description="Domain-scoped meaning overlays keyed by domain id",
    )


class ImageryNotes(BaseModel):
    """Structured RWS-style visual notes; extend via extra fields / metadata."""

    model_config = ConfigDict(extra="allow")

    summary: str = Field(default="", description="Short scene summary")
    figures: list[str] = Field(default_factory=list, description="People / creatures depicted")
    objects: list[str] = Field(default_factory=list, description="Notable objects / props")
    setting: Optional[str] = Field(default=None, description="Landscape or interior setting")
    colors: list[str] = Field(default_factory=list, description="Salient colour cues")
    gestures: list[str] = Field(default_factory=list, description="Pose / gesture motifs")


class CardMetadata(BaseModel):
    """Extensible card metadata bag.

    Prefer putting forward-compatible keys here (deck variants, source refs,
    localization provenance, AI prompt hints) rather than widening ``Card``.
    """

    model_config = ConfigDict(extra="allow")

    deck_system: str = Field(
        default="rws",
        description="Canonical system tag; default Rider-Waite-Smith",
    )
    source: Optional[str] = Field(default=None, description="Provenance / source reference")
    tags: list[str] = Field(default_factory=list)
    extras: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary nested extension payload",
    )


# ---------------------------------------------------------------------------
# Card hierarchy
# ---------------------------------------------------------------------------


class Card(BaseModel):
    """Unified tarot card model shared by Major and Minor Arcana.

    Field retention map
    -------------------
    From canon ``TarotCard``:
      id, arcana, number, suit, element, archetype, keywords,
      description, name→canonical_name, name_zh→localized_names['zh'],
      upright/reversed interpretation→meanings.general,
      astrology (str coerced into AstrologyCorrespondence.notes)

    From B2 core ``Card``:
      rank, PipCard/TrumpCard, localized_names, structured astrology,
      meanings.by_domain, domains, symbolism, imagery, light/shadow,
      advice, warnings, metadata

    Unknown top-level keys are rejected; use ``metadata`` for extension.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    id: str = Field(..., description="Stable unique id, e.g. 'the_fool', 'ace_of_wands'")
    arcana: Arcana = Field(..., description="Major or Minor Arcana")
    suit: Optional[Suit] = Field(default=None, description="Suit when Minor Arcana")
    rank: Optional[Rank] = Field(default=None, description="Rank when Minor Arcana")
    number: int = Field(
        ...,
        description="Trump number 0–21, or pip/court number 1–14 within a suit",
    )
    canonical_name: str = Field(..., description="Canonical English RWS name (canon: name)")
    localized_names: dict[str, str] = Field(
        default_factory=dict,
        description="Locale code → localized display name, e.g. {'zh': '愚者'} (canon: name_zh)",
    )
    element: Optional[Element] = Field(default=None, description="Elemental correspondence")
    astrology: Optional[AstrologyCorrespondence] = Field(
        default=None,
        description="Astrological correspondence block (accepts plain str from canon)",
    )
    archetype: Optional[str] = Field(default=None, description="Core archetype / motif label")
    keywords: CardKeywords = Field(default_factory=CardKeywords)
    meanings: CardMeanings = Field(default_factory=CardMeanings)
    description: str = Field(
        default="",
        description="Visual symbolism description in RWS deck (canon TarotCard.description)",
    )
    domains: list[str] = Field(
        default_factory=list,
        description="Primary life / reading domains this card strongly maps to",
    )
    symbolism: list[str] = Field(
        default_factory=list,
        description="Symbolic motifs (numbers, animals, tools, etc.)",
    )
    imagery: Optional[ImageryNotes] = Field(
        default=None,
        description="Structured visual / RWS imagery notes",
    )
    light_aspect: Optional[str] = Field(
        default=None,
        description="Constructive / conscious expression of the card",
    )
    shadow_aspect: Optional[str] = Field(
        default=None,
        description="Shadow / unconscious expression of the card",
    )
    advice: list[str] = Field(default_factory=list, description="Actionable guidance lines")
    warnings: list[str] = Field(default_factory=list, description="Cautions or pitfalls")
    metadata: CardMetadata = Field(default_factory=CardMetadata)

    @field_validator("astrology", mode="before")
    @classmethod
    def _coerce_astrology(cls, value: Any) -> Any:
        """Accept canon plain-string astrology as AstrologyCorrespondence.notes."""
        if value is None or isinstance(value, AstrologyCorrespondence):
            return value
        if isinstance(value, str):
            return AstrologyCorrespondence(notes=value)
        if isinstance(value, dict):
            return value
        raise TypeError(
            "astrology must be AstrologyCorrespondence, str, dict, or None"
        )

    # --- Canon TarotCard field mirrors ---

    @property
    def name(self) -> str:
        """English display name (canon TarotCard.name)."""
        return self.canonical_name

    @property
    def name_zh(self) -> Optional[str]:
        """Chinese display name (canon TarotCard.name_zh)."""
        return self.localized_names.get("zh")

    @property
    def upright_interpretation(self) -> str:
        """Detailed upright reading (canon TarotCard.upright_interpretation)."""
        return self.meanings.general.upright

    @property
    def reversed_interpretation(self) -> str:
        """Detailed reversed reading (canon TarotCard.reversed_interpretation)."""
        return self.meanings.general.reversed

    def display_name(self, locale: Optional[str] = None) -> str:
        """Return localized name when available, else canonical English name."""
        if locale and locale in self.localized_names:
            return self.localized_names[locale]
        return self.canonical_name


class PipCard(Card):
    """Minor Arcana card (pip Ace–10 or court Page–King)."""

    arcana: Literal[Arcana.MINOR] = Arcana.MINOR
    suit: Suit = Field(..., description="Required suit for Minor Arcana")
    rank: Rank = Field(..., description="Required rank for Minor Arcana")
    number: int = Field(..., ge=1, le=14, description="1 (Ace) through 14 (King)")

    @model_validator(mode="after")
    def _align_number_with_rank(self) -> PipCard:
        expected = RANK_NUMBERS[self.rank]
        if self.number != expected:
            raise ValueError(
                f"PipCard number {self.number} does not match rank {self.rank.value} "
                f"(expected {expected})"
            )
        if self.element is None:
            self.element = SUIT_ELEMENTS[self.suit]
        return self


class TrumpCard(Card):
    """Major Arcana / trump card (The Fool … The World)."""

    arcana: Literal[Arcana.MAJOR] = Arcana.MAJOR
    suit: Optional[Suit] = Field(default=None, description="Always unset for trumps")
    rank: Optional[Rank] = Field(default=None, description="Always unset for trumps")
    number: int = Field(..., ge=0, le=21, description="Trump index 0–21")

    @field_validator("suit", "rank")
    @classmethod
    def _forbid_suit_and_rank(cls, value: Any) -> None:
        if value is not None:
            raise ValueError("TrumpCard must not have suit or rank")
        return None


AnyCard = Annotated[Union[PipCard, TrumpCard], Field(discriminator="arcana")]


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
