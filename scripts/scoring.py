#!/usr/bin/env python3
"""Shared scoring policy for verifier panels and round orchestration."""

from __future__ import annotations

import statistics
from typing import Any


DIMS = ("relevance", "ats", "impact", "credibility", "writing", "formatting")

BASE_WEIGHTS = {
    "relevance": 25,
    "ats": 20,
    "impact": 20,
    "credibility": 15,
    "writing": 10,
    "formatting": 10,
}

FAMILY_ADJUSTMENTS = {
    "big_tech": {},
    "quant_swe": {"credibility": 20, "ats": 15},
    "quant_research": {"credibility": 25, "impact": 15, "ats": 15},
    "quant_trading": {"relevance": 30, "credibility": 20, "ats": 10},
    "research_lab": {"credibility": 25, "relevance": 20, "ats": 15},
    "startup": {"impact": 25, "relevance": 20},
    "other": {},
}


class ScoreValidationError(ValueError):
    """Raised when a reviewer response does not satisfy the score contract."""


def weights_for(family: str) -> dict[str, int]:
    if family not in FAMILY_ADJUSTMENTS:
        raise ScoreValidationError(f"unknown role family: {family}")
    weights = dict(BASE_WEIGHTS)
    weights.update(FAMILY_ADJUSTMENTS[family])
    if sum(weights.values()) != 100:
        raise ScoreValidationError(f"weights for {family} do not sum to 100")
    return weights


def validate_review(payload: Any) -> dict[str, Any]:
    """Validate and normalize one review returned by an LLM verifier."""
    if not isinstance(payload, dict):
        raise ScoreValidationError("review must be a JSON object")
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ScoreValidationError("review.dimensions must be an object")

    normalized_dimensions: dict[str, dict[str, Any]] = {}
    for dim in DIMS:
        item = dimensions.get(dim)
        if not isinstance(item, dict):
            raise ScoreValidationError(f"missing dimension object: {dim}")
        score = item.get("score")
        reason = item.get("reason")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ScoreValidationError(f"{dim}.score must be numeric")
        if not 0 <= score <= 100:
            raise ScoreValidationError(f"{dim}.score must be between 0 and 100")
        if not isinstance(reason, str) or not reason.strip():
            raise ScoreValidationError(f"{dim}.reason must be a non-empty string")
        normalized_dimensions[dim] = {
            "score": round(float(score), 1),
            "reason": reason.strip(),
        }

    normalized: dict[str, Any] = {"dimensions": normalized_dimensions}
    for key in ("fabrication_flags", "keyword_flags", "format_flags"):
        value = payload.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ScoreValidationError(f"{key} must be an array of strings")
        normalized[key] = [v.strip() for v in value if v.strip()]

    summary = payload.get("summary", "")
    if not isinstance(summary, str):
        raise ScoreValidationError("summary must be a string")
    normalized["summary"] = summary.strip()
    return normalized


def score_values(review: dict[str, Any]) -> dict[str, float]:
    return {dim: review["dimensions"][dim]["score"] for dim in DIMS}


def composite(scores: dict[str, float], weights: dict[str, int]) -> float:
    return round(sum(scores[dim] * weights[dim] for dim in DIMS) / 100, 1)


def aggregate_reviews(
    reviews: dict[str, dict[str, Any]], weights: dict[str, int]
) -> dict[str, Any]:
    if not reviews:
        raise ScoreValidationError("cannot aggregate an empty panel")
    dimensions = {
        dim: round(statistics.median(score_values(review)[dim] for review in reviews.values()), 1)
        for dim in DIMS
    }
    return {"dimensions": dimensions, "composite": composite(dimensions, weights)}


def keep_decision(
    incumbent: dict[str, float],
    candidate: dict[str, float],
    weights: dict[str, int],
    *,
    min_delta: float,
    max_dimension_drop: float = 5.0,
) -> dict[str, Any]:
    before = composite(incumbent, weights)
    after = composite(candidate, weights)
    delta = round(after - before, 1)
    regressions = {
        dim: round(candidate[dim] - incumbent[dim], 1)
        for dim in DIMS
        if candidate[dim] - incumbent[dim] < -max_dimension_drop
    }
    keep = delta >= min_delta and not regressions
    reasons = []
    if delta < min_delta:
        reasons.append(f"composite delta {delta:+.1f} is below +{min_delta:.1f}")
    if regressions:
        reasons.append(
            f"dimension regression exceeds {max_dimension_drop:g} points: "
            + ", ".join(regressions)
        )
    return {
        "decision": "KEEP" if keep else "REVERT",
        "incumbent_composite": before,
        "candidate_composite": after,
        "delta": delta,
        "min_delta": min_delta,
        "regressions": regressions,
        "reasons": reasons,
    }
