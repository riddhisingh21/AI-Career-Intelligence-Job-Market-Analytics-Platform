import unittest

from suggestions import build_export_report


class ExportReportTests(unittest.TestCase):
    def test_build_export_report_includes_key_sections(self):
        report_text = build_export_report(
            82.5,
            "Excellent match with the job role",
            ["python", "streamlit"],
            ["sql"],
            {"python": 2, "streamlit": 1},
            ["python", "sql", "streamlit"],
            ["Add more SQL project work"],
            ["Consider adding these skills:", "- sql"],
            "Embeddings (sentence-transformers)",
            [{"name": "Skills", "score": 91.0, "matched_skills": ["python", "streamlit"]}],
            ["Projects"],
        )

        self.assertIn("AI Resume Analyzer Report", report_text)
        self.assertIn("ATS Match Score: 82.5%", report_text)
        self.assertIn("Similarity Engine: Embeddings (sentence-transformers)", report_text)
        self.assertIn("Section-wise Resume Analysis:", report_text)
        self.assertIn("- Skills: 91.0% | Matched skills: python, streamlit", report_text)
        self.assertIn("Sections Not Clearly Found: Projects", report_text)
        self.assertIn("Matched Skills: python, streamlit", report_text)
        self.assertIn("Missing Skills: sql", report_text)
        self.assertNotIn("Download", report_text)
        self.assertIn("- sql", report_text)

    def test_build_export_report_handles_empty_sections(self):
        report_text = build_export_report(
            30,
            "Low match. Resume needs improvement",
            [],
            [],
            {},
            [],
            [],
            [],
            None,
            None,
            None,
        )

        self.assertIn("Matched Skills: None", report_text)
        self.assertIn("Missing Skills: None", report_text)
        self.assertIn("Top Skills Required in Job: None", report_text)
        self.assertIn("Skill Occurrences in Resume:\n- None", report_text)


if __name__ == "__main__":
    unittest.main()