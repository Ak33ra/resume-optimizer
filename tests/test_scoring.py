import unittest

from scripts.scoring import (
    DIMS,
    ScoreValidationError,
    aggregate_reviews,
    keep_decision,
    validate_review,
    weights_for,
)


def review(score=80, **overrides):
    scores = {dim: score for dim in DIMS}
    scores.update(overrides)
    return {
        "dimensions": {
            dim: {"score": value, "reason": f"reason for {dim}"}
            for dim, value in scores.items()
        },
        "fabrication_flags": [],
        "keyword_flags": [],
        "format_flags": [],
        "summary": "summary",
    }


class ScoringTests(unittest.TestCase):
    def test_all_family_weights_sum_to_100(self):
        for family in (
            "big_tech", "quant_swe", "quant_research", "quant_trading",
            "research_lab", "startup", "other",
        ):
            self.assertEqual(sum(weights_for(family).values()), 100)

    def test_review_requires_every_dimension(self):
        payload = review()
        del payload["dimensions"]["formatting"]
        with self.assertRaisesRegex(ScoreValidationError, "formatting"):
            validate_review(payload)

    def test_review_rejects_out_of_range_score(self):
        with self.assertRaisesRegex(ScoreValidationError, "between 0 and 100"):
            validate_review(review(relevance=101))

    def test_review_requires_dimension_reason(self):
        payload = review()
        payload["dimensions"]["ats"]["reason"] = ""
        with self.assertRaisesRegex(ScoreValidationError, "ats.reason"):
            validate_review(payload)

    def test_aggregate_uses_dimension_medians(self):
        aggregate = aggregate_reviews(
            {"a": validate_review(review(70)), "b": validate_review(review(90))},
            weights_for("big_tech"),
        )
        self.assertEqual(aggregate["dimensions"]["impact"], 80)
        self.assertEqual(aggregate["composite"], 80)

    def test_keep_requires_margin_and_bounded_regressions(self):
        weights = weights_for("big_tech")
        incumbent = {dim: 80.0 for dim in DIMS}
        candidate = dict(incumbent)
        candidate["relevance"] = 88
        self.assertEqual(
            keep_decision(incumbent, candidate, weights, min_delta=1.0)["decision"],
            "KEEP",
        )
        candidate["formatting"] = 74
        decision = keep_decision(incumbent, candidate, weights, min_delta=1.0)
        self.assertEqual(decision["decision"], "REVERT")
        self.assertEqual(decision["regressions"], {"formatting": -6.0})


if __name__ == "__main__":
    unittest.main()
