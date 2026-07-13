import unittest

from scripts.ats_rules import hard_checks_pass, tex_checks, text_checks


BASE_TEXT = """Jane Candidate
jane@example.com | 617-555-0100
Education
Example University
Experience
Engineer                                           Jan 2024 -- Present
Built a sufficiently detailed system description that makes this extracted resume text longer.
Projects
Created another project with measurable outcomes and enough prose for extraction checks.
Technical Skills
Python, SQL, distributed systems
"""

BASE_TEX = r"""\input{glyphtounicode}
\pdfgentounicode=1
\pagestyle{fancy}
\fancyhf{}
\begin{document}
Jane Candidate jane@example.com
\section{Experience}
\end{document}
"""


class AtsRuleTests(unittest.TestCase):
    def test_valid_rendered_text_passes_hard_checks(self):
        self.assertTrue(hard_checks_pass(text_checks(BASE_TEXT)))

    def test_volunteering_is_a_standard_heading(self):
        text = BASE_TEXT.replace("Projects", "Volunteering")
        heading_check = next(
            check for check in text_checks(text) if check["name"] == "standard section headings detected"
        )
        self.assertTrue(heading_check["passed"])
        self.assertIn("volunteering", heading_check["detail"])

    def test_malformed_year_only_date_range_fails(self):
        checks = text_checks(BASE_TEXT.replace("Jan 2024 -- Present", "2024 -- 2025"))
        date_check = next(check for check in checks if check["name"].startswith("date ranges"))
        self.assertFalse(date_check["passed"])

    def test_tex_source_checks_unicode_body_contact_and_layout(self):
        self.assertTrue(hard_checks_pass(tex_checks(BASE_TEX)))
        bad = BASE_TEX.replace("\\begin{document}", "\\begin{document}\n\\begin{multicols}{2}")
        layout = next(check for check in tex_checks(bad) if check["name"] == "single-column source structure")
        self.assertFalse(layout["passed"])

    def test_nonempty_header_content_fails(self):
        checks = tex_checks(BASE_TEX.replace("\\fancyhf{}", "\\fancyhead[L]{Jane Candidate}"))
        header = next(check for check in checks if check["name"] == "no content in headers or footers")
        self.assertFalse(header["passed"])


if __name__ == "__main__":
    unittest.main()
