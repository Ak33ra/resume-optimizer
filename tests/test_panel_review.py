import os
import unittest

from scripts.panel_review import (
    DEFAULT_REVIEWERS,
    REVIEWERS,
    _available,
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


class OssReviewerOptInTests(unittest.TestCase):
    """The opt-in oss reviewer must never affect a fresh, unconfigured clone."""

    _OSS_VARS = ("PANEL_OSS_BASE_URL", "PANEL_OSS_API_KEY", "PANEL_OSS_MODEL")

    def setUp(self):
        self._saved = {v: os.environ.pop(v, None) for v in self._OSS_VARS}

    def tearDown(self):
        for var, val in self._saved.items():
            if val is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = val

    def test_oss_excluded_from_default_panel(self):
        self.assertNotIn("oss", DEFAULT_REVIEWERS.split(","))

    def test_oss_unavailable_without_config(self):
        self.assertFalse(_available("oss"))

    def test_oss_available_when_configured(self):
        for var in self._OSS_VARS:
            os.environ[var] = "x"
        self.assertTrue(_available("oss"))

    def test_oss_unavailable_with_partial_config(self):
        os.environ["PANEL_OSS_BASE_URL"] = "x"  # missing key + model
        self.assertFalse(_available("oss"))


if __name__ == "__main__":
    unittest.main()
