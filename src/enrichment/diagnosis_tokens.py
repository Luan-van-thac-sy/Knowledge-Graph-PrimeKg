"""
Tokenize free-text diagnoses for substring matching against PrimeKG disease names.
"""
from __future__ import annotations

import re
from typing import Dict, List

# Common clinical / chart filler — not useful for graph name matching
_STOP_WORDS = frozenset(
    {
        "with",
        "and",
        "or",
        "of",
        "the",
        "a",
        "an",
        "in",
        "on",
        "for",
        "to",
        "at",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "been",
        "type",
        "history",
        "due",
        "without",
        "not",
        "other",
        "nos",
        "unspecified",
        "primary",
        "secondary",
        "stage",
        "status",
        "post",
        "pre",
        "old",
        "new",
        "late",
        "early",
    }
)

_MIN_TOKEN_LEN = 3


def _normalize_tokens(raw_tokens: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for t in raw_tokens:
        t = t.strip().lower()
        if len(t) < _MIN_TOKEN_LEN or t in _STOP_WORDS:
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def tokenize_diagnosis(text: str) -> List[str]:
    """
    Split a diagnosis string into keywords for CONTAINS matching.

    Example:
        "Diabetes with peripheral circulatory disorders"
        -> ["diabetes", "peripheral", "circulatory", "disorders"]
    """
    text = (text or "").strip()
    if not text:
        return []

    raw = re.split(r"[^a-zA-Z0-9]+", text)
    tokens = _normalize_tokens(raw)
    if tokens:
        return tokens

    # Fallback: keep longer alphanumeric fragments even if stop-word filtered
    fallback = [t.strip().lower() for t in raw if len(t.strip()) >= _MIN_TOKEN_LEN]
    tokens = _normalize_tokens(fallback)
    if tokens:
        return tokens

    lowered = text.lower()
    if len(lowered) >= _MIN_TOKEN_LEN:
        return [lowered]
    return []


def build_diagnosis_specs(diagnoses: List[str]) -> List[Dict[str, object]]:
    """Build Neo4j parameter rows: ``{input_dx, tokens}`` per non-empty diagnosis."""
    specs: List[Dict[str, object]] = []
    for dx in diagnoses:
        dx = (dx or "").strip()
        if not dx:
            continue
        tokens = tokenize_diagnosis(dx)
        if not tokens:
            tokens = [dx.lower()]
        specs.append({"input_dx": dx, "tokens": tokens})
    return specs
