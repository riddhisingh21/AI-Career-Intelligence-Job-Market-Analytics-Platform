import unittest
from unittest.mock import patch

from evaluation_utils import evaluate_dataset_rows, load_dataset_rows


class DatasetEvaluationLoadingTests(unittest.TestCase):
    def test_load_dataset_rows_parses_required_and_optional_columns(self):
        csv_text = (
            "pair_name,resume_text,job_description,expected_min_score,expected_top_role\n"
            "Backend Pair,Python SQL backend resume,Python SQL AWS role,75,Backend Developer\n"
            ",React frontend resume,React TypeScript CSS role,,Frontend Developer\n"
        )

        rows = load_dataset_rows(csv_text)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["pair_name"], "Backend Pair")
        self.assertEqual(rows[0]["expected_min_score"], 75.0)
        self.assertEqual(rows[0]["expected_top_role"], "Backend Developer")
        self.assertEqual(rows[1]["pair_name"], "Pair 2")
        self.assertIsNone(rows[1]["expected_min_score"])

    def test_load_dataset_rows_rejects_missing_required_columns(self):
        with self.assertRaisesRegex(ValueError, "resume_text"):
            load_dataset_rows("pair_name,job_description\nPair 1,Backend role\n")


class DatasetEvaluationComputationTests(unittest.TestCase):
    @patch("evaluation_utils.recommend_job_roles")
    @patch("evaluation_utils.skill_analysis")
    @patch("evaluation_utils.benchmark_similarity_methods")
    def test_evaluate_dataset_rows_builds_summary_and_expectation_metrics(
        self,
        mock_benchmark_similarity_methods,
        mock_skill_analysis,
        mock_recommend_job_roles,
    ):
        mock_benchmark_similarity_methods.side_effect = [
            {
                "selected_score": 82.5,
                "selected_method": "embeddings",
                "selected_method_label": "Embeddings (sentence-transformers)",
                "score_gap": 6.5,
            },
            {
                "selected_score": 61.0,
                "selected_method": "tfidf_fallback",
                "selected_method_label": "TF-IDF fallback",
                "score_gap": 0.0,
            },
        ]
        mock_skill_analysis.side_effect = [
            (["python", "sql"], ["aws"]),
            (["react"], ["typescript", "css"]),
        ]
        mock_recommend_job_roles.side_effect = [
            [{"name": "Backend Developer", "score": 83.0}],
            [{"name": "Frontend Developer", "score": 65.0}],
        ]

        dataset_evaluation = evaluate_dataset_rows(
            [
                {
                    "pair_name": "Backend Pair",
                    "resume_text": "resume 1",
                    "job_description": "job 1",
                    "expected_min_score": 80.0,
                    "expected_top_role": "Backend Developer",
                },
                {
                    "pair_name": "Frontend Pair",
                    "resume_text": "resume 2",
                    "job_description": "job 2",
                    "expected_min_score": 70.0,
                    "expected_top_role": "Frontend Developer",
                },
            ]
        )

        self.assertEqual(dataset_evaluation["summary"]["total_pairs"], 2)
        self.assertEqual(dataset_evaluation["summary"]["average_score"], 71.75)
        self.assertEqual(dataset_evaluation["summary"]["average_score_gap"], 3.25)
        self.assertEqual(dataset_evaluation["summary"]["pairs_above_70"], 1)
        self.assertEqual(dataset_evaluation["summary"]["score_expectation_passes"], 1)
        self.assertEqual(dataset_evaluation["summary"]["role_expectation_passes"], 2)
        self.assertEqual(dataset_evaluation["results"][0]["score_expectation_met"], True)
        self.assertEqual(dataset_evaluation["results"][1]["score_expectation_met"], False)
        self.assertEqual(dataset_evaluation["results"][1]["top_role"], "Frontend Developer")
        self.assertEqual(
            {item["label"] for item in dataset_evaluation["summary"]["selected_method_breakdown"]},
            {"Embeddings (sentence-transformers)", "TF-IDF fallback"},
        )


if __name__ == "__main__":
    unittest.main()