"""Common tarot spread definitions."""

from __future__ import annotations

from tarot.knowledge.models import Spread, SpreadPosition

THREE_CARD_SPREAD = Spread(
    id="three-card",
    name="Three-Card Spread",
    description=(
        "A versatile spread exploring past influences, present situation, "
        "and future potential."
    ),
    positions=[
        SpreadPosition(
            name="Past",
            description="Influences and events leading to the present.",
            order=0,
        ),
        SpreadPosition(
            name="Present",
            description="The current situation or central energy.",
            order=1,
        ),
        SpreadPosition(
            name="Future",
            description="Likely outcome or direction if energy continues.",
            order=2,
        ),
    ],
)

CELTIC_CROSS_SPREAD = Spread(
    id="celtic-cross",
    name="Celtic Cross",
    description="A classic ten-card spread providing a comprehensive view of a situation.",
    positions=[
        SpreadPosition(
            name="Present",
            description="The core situation or central issue.",
            order=0,
        ),
        SpreadPosition(
            name="Challenge",
            description="The immediate obstacle or counter-energy.",
            order=1,
        ),
        SpreadPosition(
            name="Past",
            description="Recent influences and the foundation of the matter.",
            order=2,
        ),
        SpreadPosition(
            name="Future",
            description="Where the current path is heading in the near term.",
            order=3,
        ),
        SpreadPosition(
            name="Above",
            description="Conscious goals, ideals, and what you aspire to.",
            order=4,
        ),
        SpreadPosition(
            name="Below",
            description="Subconscious influences and hidden foundations.",
            order=5,
        ),
        SpreadPosition(
            name="Advice",
            description="Recommended attitude or action to take.",
            order=6,
        ),
        SpreadPosition(
            name="External Influences",
            description="People, events, or energies in the environment.",
            order=7,
        ),
        SpreadPosition(
            name="Hopes and Fears",
            description="What you desire or dread regarding the outcome.",
            order=8,
        ),
        SpreadPosition(
            name="Outcome",
            description="The probable result if current energies continue.",
            order=9,
        ),
    ],
)

ONE_CARD_SPREAD = Spread(
    id="one-card",
    name="One-Card Draw",
    description="A single card to answer a focused question or provide daily guidance.",
    positions=[
        SpreadPosition(
            name="Answer",
            description="The card's message for your question.",
            order=0,
        ),
    ],
)

RELATIONSHIP_SPREAD = Spread(
    id="relationship",
    name="Relationship Spread",
    description="A five-card spread examining the dynamics between two people.",
    positions=[
        SpreadPosition(
            name="You",
            description="Your energy in the relationship.",
            order=0,
        ),
        SpreadPosition(
            name="Partner",
            description="The other person's energy in the relationship.",
            order=1,
        ),
        SpreadPosition(
            name="Relationship",
            description="The shared energy or current state of the relationship.",
            order=2,
        ),
        SpreadPosition(
            name="Challenge",
            description="The main obstacle or tension between you.",
            order=3,
        ),
        SpreadPosition(
            name="Potential",
            description="The relationship's potential if the challenge is addressed.",
            order=4,
        ),
    ],
)

CAREER_PATH_SPREAD = Spread(
    id="career-path",
    name="Career Path Spread",
    description="A five-card spread for career decisions and professional growth.",
    positions=[
        SpreadPosition(
            name="Current Situation",
            description="Your present career state.",
            order=0,
        ),
        SpreadPosition(
            name="Strengths",
            description="Skills and assets you bring.",
            order=1,
        ),
        SpreadPosition(
            name="Obstacles",
            description="Challenges or blocks in your path.",
            order=2,
        ),
        SpreadPosition(
            name="Opportunities",
            description="Available paths or openings.",
            order=3,
        ),
        SpreadPosition(
            name="Outcome",
            description="Likely result of your current trajectory.",
            order=4,
        ),
    ],
)

ALL_SPREADS: list[Spread] = [
    ONE_CARD_SPREAD,
    THREE_CARD_SPREAD,
    CELTIC_CROSS_SPREAD,
    RELATIONSHIP_SPREAD,
    CAREER_PATH_SPREAD,
]
