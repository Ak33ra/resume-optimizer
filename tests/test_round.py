import json
import tempfile
import unittest
from pathlib import Path

from scripts.round import (
    RoundError,
    TargetPaths,
    atomic_json,
    finish_round,
    init_target,
    load_state,
    panel_scores,
    prepend_log_entry,
    sha256_text,
    start_round,
)
from scripts.scoring import DIMS


def panel_payload(score=80):
    return {
        "panel": {
            "valid": True,
            "decorrelated": True,
            "completed": ["codex", "gemini"],
            "reviewer_families": {"codex": "openai", "gemini": "google"},
        },
        "aggregate": {
            "dimensions": {dim: score for dim in DIMS},
            "composite": score,
        },
    }


class RoundTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        for directory in ("resumes", "outputs", "job_descriptions", "source_material"):
            (self.root / directory).mkdir()
        self.paths = TargetPaths(self.root, "example")
        self.paths.jd.write_text("Job", encoding="utf-8")
        self.paths.canonical.write_text(
            "\\begin{document}\n% source: role\n\\resumeSubheading{Engineer}{Jan 2024 -- Present}{Co}{Remote}\n\\end{document}\n",
            encoding="utf-8",
        )
        self.paths.output_pdf.write_bytes(b"PDF")
        source = self.root / "source_material" / "EXPERIENCE.md"
        source.write_text("Engineer at Co", encoding="utf-8")
        self.paths.provenance.write_text(
            json.dumps({
                "schema_version": 1,
                "claims": {
                    "role": {"sources": [{
                        "file": "source_material/EXPERIENCE.md",
                        "section": "Co",
                        "evidence": "Engineer at Co",
                    }]}
                },
            }),
            encoding="utf-8",
        )
        self.paths.log.write_text("# Optimization Log\n\n## Rounds\n\nold\n", encoding="utf-8")
        self.panel = self.root / "panel.json"
        self.panel.write_text(json.dumps(panel_payload()), encoding="utf-8")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_init_creates_state_and_baseline_log(self):
        state = init_target(self.paths, "big_tech", self.panel, "passed")
        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["canonical"]["scores"]["composite"], 80)
        log = self.paths.log.read_text(encoding="utf-8")
        self.assertLess(log.index("baseline"), log.index("old"))

    def test_start_copies_canonical_and_provenance(self):
        init_target(self.paths, "big_tech", self.panel, "passed")
        state = start_round(self.paths, "move stronger evidence upward")
        self.assertEqual(state["status"], "editing")
        self.assertEqual(state["round"], 1)
        self.assertEqual(sha256_text(self.paths.candidate), sha256_text(self.paths.canonical))
        self.assertTrue(self.paths.candidate_provenance.exists())

    def test_start_detects_out_of_band_canonical_edit(self):
        init_target(self.paths, "big_tech", self.panel, "passed")
        self.paths.canonical.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(RoundError, "outside the orchestrator"):
            start_round(self.paths, "test")

    def test_invalid_panel_is_rejected(self):
        value = panel_payload()
        value["panel"]["valid"] = False
        with self.assertRaisesRegex(RoundError, "not valid"):
            panel_scores(value)

    def test_log_insert_requires_round_marker(self):
        bad_log = self.root / "bad.md"
        bad_log.write_text("# no marker", encoding="utf-8")
        with self.assertRaisesRegex(RoundError, "missing"):
            prepend_log_entry(bad_log, "entry")

    def test_load_state_rejects_wrong_slug(self):
        init_target(self.paths, "big_tech", self.panel, "passed")
        state = json.loads(self.paths.state.read_text(encoding="utf-8"))
        state["slug"] = "other"
        self.paths.state.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(RoundError, "slug"):
            load_state(self.paths)

    def test_finish_keep_promotes_exact_gated_candidate(self):
        init_target(self.paths, "big_tech", self.panel, "passed")
        state = start_round(self.paths, "improve relevance")
        self.paths.candidate.write_text(
            self.paths.candidate.read_text(encoding="utf-8") + "% stronger candidate\n",
            encoding="utf-8",
        )
        self.paths.candidate_pdf.write_bytes(b"CANDIDATE PDF")
        state["status"] = "gated"
        state["pending"]["gate"] = {
            "passed": True,
            "candidate_sha256": sha256_text(self.paths.candidate),
        }
        atomic_json(self.paths.state, state)
        paired = panel_payload()
        paired["input"] = {
            "incumbent_sha256": sha256_text(self.paths.canonical),
            "candidate_sha256": sha256_text(self.paths.candidate),
        }
        paired["aggregate"] = {
            "incumbent": panel_payload(80)["aggregate"],
            "candidate": panel_payload(82)["aggregate"],
        }
        paired["recommendation"] = {"decision": "KEEP", "min_delta": 1.0}
        paired["review_flags"] = {
            "candidate": {"fabrication_flags": [], "keyword_flags": [], "format_flags": []}
        }
        paired_path = self.root / "paired.json"
        paired_path.write_text(json.dumps(paired), encoding="utf-8")

        final_state, decision = finish_round(
            self.paths, paired_path, "surfaced stronger evidence", [], None, False
        )

        self.assertEqual(decision, "KEEP")
        self.assertEqual(final_state["canonical"]["scores"]["composite"], 82)
        self.assertIn("stronger candidate", self.paths.canonical.read_text(encoding="utf-8"))
        self.assertEqual(self.paths.output_pdf.read_bytes(), b"CANDIDATE PDF")
        self.assertFalse(self.paths.candidate.exists())
        self.assertIn("decision: KEEP", self.paths.log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
