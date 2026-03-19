import unittest

from export_utils import (
    build_csv_report,
    build_dataset_evaluation_csv_report,
    build_dataset_evaluation_text_report,
    build_pdf_report,
)


class ExportUtilsTests(unittest.TestCase):
    def test_build_csv_report_contains_expected_sections(self):
        csv_text = build_csv_report(
            88.5,
            "Excellent match with the job role",
            "Embeddings (sentence-transformers)",
            ["python"],
            ["sql"],
            {"python": 2},
            ["python", "sql"],
            ["Add SQL experience"],
            ["Include measurable achievements."],
            [{"name": "Skills", "score": 95.0, "matched_skills": ["python"]}],
            ["Projects"],
        )

        self.assertIn("summary,ats_match_score,88.5", csv_text)
        self.assertIn("summary,similarity_engine,Embeddings (sentence-transformers)", csv_text)
        self.assertIn("matched_skills,python,matched", csv_text)
        self.assertIn("missing_skills,sql,missing", csv_text)
        self.assertIn("section_analysis,Skills,95.0", csv_text)
        self.assertIn("missing_resume_sections,Projects,not_detected", csv_text)

    def test_build_pdf_report_returns_pdf_bytes(self):
        pdf_bytes = build_pdf_report("AI Resume Analyzer Report\nATS Match Score: 88.5%")

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 100)

    def test_build_dataset_evaluation_csv_report_contains_summary_and_pair_rows(self):
        csv_text = build_dataset_evaluation_csv_report(
            {
                "total_pairs": 2,
                "average_score": 74.75,
                "average_score_gap": 4.5,
                "average_matched_skill_count": 2.5,
                "pairs_above_70": 1,
                "pairs_above_70_ratio": 50.0,
                "score_expectation_checks": 1,
                "score_expectation_passes": 1,
                "score_expectation_pass_rate": 100.0,
                "role_expectation_checks": 1,
                "role_expectation_passes": 1,
                "role_expectation_pass_rate": 100.0,
                "selected_method_breakdown": [
                    {"label": "Embeddings (sentence-transformers)", "count": 1},
                ],
            },
            [
                {
                    "pair_name": "Backend Pair",
                    "score": 88.5,
                    "interpretation": "Excellent match with the job role",
                    "selected_method_label": "Embeddings (sentence-transformers)",
                    "score_gap": 6.2,
                    "top_role": "Backend Developer",
                    "top_role_score": 83.0,
                    "matched_skill_count": 3,
                    "missing_skill_count": 1,
                    "expected_min_score": 80.0,
                    "score_expectation_met": True,
                    "expected_top_role": "Backend Developer",
                    "role_expectation_met": True,
                }
            ],
        )

        self.assertIn("summary,total_pairs,2", csv_text)
        self.assertIn("selected_method_breakdown,Embeddings (sentence-transformers),1", csv_text)
        self.assertIn("Backend Pair,88.5,Excellent match with the job role", csv_text)
        self.assertIn(",pass,Backend Developer,pass", csv_text)

    def test_build_dataset_evaluation_text_report_contains_key_metrics(self):
        report_text = build_dataset_evaluation_text_report(
            {
                "total_pairs": 1,
                "average_score": 82.5,
                "average_score_gap": 5.0,
                "average_matched_skill_count": 3.0,
                "pairs_above_70": 1,
                "pairs_above_70_ratio": 100.0,
                "score_expectation_checks": 1,
                "score_expectation_passes": 1,
                "score_expectation_pass_rate": 100.0,
                "role_expectation_checks": 1,
                "role_expectation_passes": 1,
                "role_expectation_pass_rate": 100.0,
                "selected_method_breakdown": [
                    {"label": "Embeddings (sentence-transformers)", "count": 1},
                ],
            },
            [
                {
                    "pair_name": "Pair 1",
                    "score": 82.5,
                    "selected_method_label": "Embeddings (sentence-transformers)",
                    "top_role": "Backend Developer",
                    "top_role_score": 83.0,
                    "matched_skill_count": 3,
                    "missing_skill_count": 1,
                    "score_expectation_met": True,
                    "role_expectation_met": True,
                }
            ],
        )

        self.assertIn("Dataset Evaluation Report", report_text)
        self.assertIn("Average ATS match score: 82.50%", report_text)
        self.assertIn("Score expectation pass rate: 1/1 (100.00%)", report_text)
        self.assertIn("Pair 1: 82.50% using Embeddings (sentence-transformers)", report_text)


if __name__ == "__main__":
    unittest.main()