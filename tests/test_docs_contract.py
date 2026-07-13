import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_log_schema_includes_all_decisions_and_panel_metadata(self):
        log = self.read("optimization_log.md")
        for decision in ("BASELINE", "KEEP", "REVERT"):
            self.assertIn(decision, log)
        self.assertIn("- panel:", log)
        self.assertIn("- benchmark:", log)

    def test_documented_gate_checks_pdf_and_tex(self):
        tools = self.read("TOOLS.md")
        self.assertIn("scripts/ats_check.py", tools)
        self.assertIn("--tex resumes/<slug>_resume.candidate.tex", tools)
        self.assertIn("scripts/provenance_check.py", tools)

    def test_panel_docs_require_optimizer_family(self):
        for name in ("TOOLS.md", "OPTIMIZATION_LOOP.md", "docs/cross-agent-review.md"):
            self.assertIn("--optimizer-family", self.read(name), name)

    def test_privacy_docs_scope_the_exception(self):
        privacy = self.read("PRIVACY.md")
        self.assertIn("resumeopt.privateRemote", privacy)
        self.assertIn("resumeopt.privatePushUrl", privacy)


if __name__ == "__main__":
    unittest.main()
