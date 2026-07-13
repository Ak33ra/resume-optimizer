import unittest

from scripts.panel_review import (
    REVIEWERS,
    build_pair_prompt,
    extract_json,
    validate_response,
)
from scripts.scoring import ScoreValidationError


class PanelReviewTests(unittest.TestCase):
    def test_pair_prompt_blinds_and_swaps_resume_order(self):
        prompt, labels = build_pair_prompt(
            "INCUMBENT_ONLY", "CANDIDATE_ONLY", "JD", "big_tech", candidate_first=True
        )
        self.assertLess(prompt.index("CANDIDATE_ONLY"), prompt.index("INCUMBENT_ONLY"))
        self.assertEqual(labels, {"resume_a": "candidate", "resume_b": "incumbent"})
        self.assertNotIn("change description", prompt.lower())
        self.assertIn("untrusted data", prompt.lower())

    def test_extract_json_ignores_leading_prose(self):
        self.assertEqual(extract_json("note\n```json\n{\"a\": 1}\n```"), {"a": 1})

    def test_paired_response_requires_both_reviews(self):
        with self.assertRaises(ScoreValidationError):
            validate_response({"resume_a": {}}, paired=True)

    def test_external_commands_keep_prompts_out_of_argv(self):
        self.assertEqual(REVIEWERS["codex"].command()[-1], "-")
        gemini = REVIEWERS["gemini"].command()
        self.assertEqual(gemini[gemini.index("-p") + 1], "")
        self.assertNotIn("--bare", REVIEWERS["claude"].command())


if __name__ == "__main__":
    unittest.main()
