import json
import tempfile
import unittest
from pathlib import Path

from scripts.provenance_check import active_claim_markers, validate_provenance


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "source_material").mkdir()
        (self.root / "resumes").mkdir()
        (self.root / "source_material" / "EXPERIENCE.md").write_text(
            "## Example Co\nReduced latency by 30 percent.\n", encoding="utf-8"
        )
        self.tex = self.root / "resumes" / "target_resume.tex"
        self.tex.write_text(
            r"""\begin{document}
% source: example-role
\resumeSubheading{Engineer}{Jan 2024 -- Present}{Example Co}{Remote}
% source: latency
\resumeItem{Reduced request latency by 30\%}
\end{document}
""",
            encoding="utf-8",
        )
        self.manifest = self.root / "resumes" / "target_provenance.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "claims": {
                        "example-role": {
                            "sources": [{
                                "file": "source_material/EXPERIENCE.md",
                                "section": "Example Co",
                                "evidence": "Example Co",
                            }]
                        },
                        "latency": {
                            "sources": [{
                                "file": "source_material/EXPERIENCE.md",
                                "section": "Example Co",
                                "evidence": "Reduced latency by 30 percent.",
                            }]
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_valid_manifest_passes(self):
        result = validate_provenance(self.tex, self.manifest, self.root)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual([claim["id"] for claim in result["claims"]], ["example-role", "latency"])

    def test_active_claim_without_marker_fails(self):
        tex = self.tex.read_text(encoding="utf-8").replace("% source: latency\n", "")
        _, errors = active_claim_markers(tex)
        self.assertTrue(any("no preceding" in error for error in errors))

    def test_source_path_cannot_escape_source_material(self):
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["claims"]["latency"]["sources"][0]["file"] = "README.md"
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        result = validate_provenance(self.tex, self.manifest, self.root)
        self.assertFalse(result["passed"])
        self.assertTrue(any("inside source_material" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
