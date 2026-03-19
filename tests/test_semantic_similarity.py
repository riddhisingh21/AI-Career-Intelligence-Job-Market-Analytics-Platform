import unittest
from unittest.mock import patch

from analyzer import (
    benchmark_similarity_methods,
    calculate_similarity,
    calculate_similarity_details,
    describe_similarity_method,
)


class SemanticSimilarityTests(unittest.TestCase):
    def test_calculate_similarity_prefers_embedding_score_when_available(self):
        with patch("analyzer._calculate_embedding_similarity", return_value=91.25) as embedding_mock:
            with patch("analyzer._calculate_tfidf_similarity", return_value=35.0) as tfidf_mock:
                score = calculate_similarity("Python APIs", "Backend Python development")

        self.assertEqual(score, 91.25)
        embedding_mock.assert_called_once()
        tfidf_mock.assert_not_called()

    def test_calculate_similarity_falls_back_to_tfidf_on_embedding_error(self):
        with patch("analyzer._calculate_embedding_similarity", side_effect=RuntimeError("model error")):
            with patch("analyzer._calculate_tfidf_similarity", return_value=42.5) as tfidf_mock:
                score = calculate_similarity("resume text", "job text")

        self.assertEqual(score, 42.5)
        tfidf_mock.assert_called_once_with("resume text", "job text")

    def test_calculate_similarity_returns_zero_for_empty_text(self):
        self.assertEqual(calculate_similarity("", "job description"), 0.0)
        self.assertEqual(calculate_similarity("resume text", "   "), 0.0)

    def test_calculate_similarity_details_reports_method(self):
        with patch("analyzer._calculate_embedding_similarity", return_value=77.0):
            result = calculate_similarity_details("resume text", "job text")

        self.assertEqual(result, {"score": 77.0, "method": "embeddings"})

    def test_benchmark_similarity_methods_reports_both_scores_when_available(self):
        with patch("analyzer._calculate_embedding_similarity", return_value=84.5):
            with patch("analyzer._calculate_tfidf_similarity", return_value=61.25):
                result = benchmark_similarity_methods("resume text", "job text")

        self.assertEqual(result["selected_score"], 84.5)
        self.assertEqual(result["selected_method"], "embeddings")
        self.assertEqual(result["selected_method_label"], "Embeddings (sentence-transformers)")
        self.assertEqual(result["score_gap"], 23.25)
        self.assertTrue(result["methods"][0]["available"])
        self.assertEqual(result["methods"][0]["score"], 84.5)
        self.assertTrue(result["methods"][1]["available"])
        self.assertEqual(result["methods"][1]["score"], 61.25)

    def test_benchmark_similarity_methods_falls_back_when_embeddings_fail(self):
        with patch("analyzer._calculate_embedding_similarity", side_effect=RuntimeError("model error")):
            with patch("analyzer._calculate_tfidf_similarity", return_value=42.5):
                result = benchmark_similarity_methods("resume text", "job text")

        self.assertEqual(result["selected_score"], 42.5)
        self.assertEqual(result["selected_method"], "tfidf_fallback")
        self.assertEqual(result["selected_method_label"], "TF-IDF fallback")
        self.assertEqual(result["score_gap"], 0.0)
        self.assertFalse(result["methods"][0]["available"])
        self.assertIsNone(result["methods"][0]["score"])
        self.assertTrue(result["methods"][1]["available"])
        self.assertEqual(result["methods"][1]["score"], 42.5)

    def test_describe_similarity_method_returns_human_readable_label(self):
        self.assertEqual(
            describe_similarity_method("tfidf_fallback"),
            "TF-IDF fallback",
        )


if __name__ == "__main__":
    unittest.main()