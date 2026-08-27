"""Relevance-based memory retrieval for tarot readings.

The retriever filters a user's memory entries so that only context likely
to be useful for the current question is returned.  It is deliberately
conservative: returning nothing is preferred over returning irrelevant
memories that could pollute a reading.
"""

from __future__ import annotations

from .models import MemoryEntry, MemoryType
from .store import JsonMemoryStore

_STOP_WORDS = frozenset({
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "i",
    "in",
    "is",
    "it",
    "its",
    "may",
    "me",
    "might",
    "my",
    "of",
    "on",
    "or",
    "shall",
    "should",
    "so",
    "than",
    "that",
    "the",
    "then",
    "there",
    "these",
    "this",
    "those",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "about",
    "tell",
    "say",
    "says",
    "said",
    "ask",
    "asked",
})

# Expanded domain terms bridge the vocabulary gap between a user's question
# domain and the words used in stored memory entries.
_DOMAIN_TERMS: dict[str, set[str]] = {
    "career": {
        "career",
        "job",
        "jobs",
        "work",
        "works",
        "working",
        "worker",
        "profession",
        "professional",
        "employment",
        "employer",
        "employee",
        "promotion",
        "promotions",
        "promoted",
        "raise",
        "salary",
        "software",
        "engineering",
        "engineer",
        "engineers",
        "developer",
        "remote",
        "office",
        "manager",
        "management",
        "boss",
        "colleague",
    },
    "pets": {
        "pet",
        "pets",
        "dog",
        "dogs",
        "cat",
        "cats",
        "animal",
        "animals",
        "puppy",
        "kitten",
        "vet",
        "veterinary",
    },
    "love": {
        "love",
        "lover",
        "lovers",
        "relationship",
        "relationships",
        "partner",
        "partners",
        "dating",
        "date",
        "marriage",
        "married",
        "romance",
        "romantic",
        "boyfriend",
        "girlfriend",
        "spouse",
    },
}

_TYPE_BASE: dict[MemoryType, float] = {
    MemoryType.USER_STATED_FACT: 0.4,
    MemoryType.READING_CONTEXT: 0.2,
    MemoryType.MODEL_INTERPRETATION: 0.1,
    MemoryType.HYPOTHESIS: 0.05,
}


def _tokenise(text: str) -> set[str]:
    """Return a set of normalised, meaningful word tokens."""
    return {t for t in text.lower().split() if t not in _STOP_WORDS}


def _domain_tokens(domain: str) -> set[str]:
    """Return expanded query tokens for a life-area domain."""
    return _DOMAIN_TERMS.get(domain.lower(), {domain.lower()})


def _score_relevance(entry: MemoryEntry, query_tokens: set[str]) -> float:
    """Compute a simple relevance score for a memory entry.

    Scoring rules:
    - User-stated facts are strongly preferred because they are reliable.
    - Reading context is moderately preferred.
    - Model interpretations and hypotheses are weakly preferred unless they
      directly match the question/domain.
    - Token overlap between the entry content and the expanded question/domain
      adds a direct relevance bonus.
    - Stop words are ignored so that accidental one-token matches (e.g. "in")
      do not surface unrelated memories.
    """
    entry_tokens = _tokenise(entry.content)
    overlap = len(entry_tokens & query_tokens)

    # Every memory must share at least one meaningful token with the query
    # to be considered relevant.
    if overlap == 0:
        return 0.0

    base = _TYPE_BASE[entry.type]
    score = (base + 0.5 * overlap) * (0.5 + 0.5 * entry.confidence)

    return score


def retrieve_relevant(
    store: JsonMemoryStore,
    user_id: str,
    question: str,
    domain: str,
    *,
    limit: int = 5,
    min_score: float = 0.55,
) -> list[MemoryEntry]:
    """Return the most relevant memory entries for a reading.

    The function only considers non-expired entries belonging to `user_id`.
    Entries are scored by type reliability and token overlap with the
    question and domain.  Entries scoring below `min_score` are dropped to
    avoid polluting the reading with unrelated memories.

    Args:
        store: The memory store to query.
        user_id: The user whose memories should be searched.
        question: The user's current question.
        domain: The life area or domain of the question.
        limit: Maximum number of entries to return.
        min_score: Minimum relevance score required for inclusion.

    Returns:
        A list of `MemoryEntry` objects sorted by descending relevance.
    """
    query_tokens = _tokenise(question) | _domain_tokens(domain)

    candidates = store.query_by_user(user_id)
    scored: list[tuple[float, MemoryEntry]] = []
    for entry in candidates:
        score = _score_relevance(entry, query_tokens)
        if score >= min_score:
            scored.append((score, entry))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in scored[:limit]]
