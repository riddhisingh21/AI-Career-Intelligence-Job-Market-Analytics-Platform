import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gemini_analysis import GeminiAnalysisError, analyze_resume_with_gemini, resolve_gemini_api_key


class GeminiConfigTests(unittest.TestCase):
    @patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}, clear=True)
    def test_resolve_gemini_api_key_prefers_environment_value(self):
        secrets = {"GEMINI_API_KEY": "secret-key", "gemini": {"api_key": "nested-secret"}}

        self.assertEqual(resolve_gemini_api_key(secrets), "env-key")

    @patch.dict(os.environ, {}, clear=True)
    def test_resolve_gemini_api_key_supports_nested_secrets(self):
        self.assertEqual(resolve_gemini_api_key({"gemini": {"api_key": "nested-secret"}}), "nested-secret")


class GeminiAnalysisTests(unittest.TestCase):
    @patch("gemini_analysis._build_gemini_client")
    def test_analyze_resume_with_gemini_normalizes_structured_response(self, mock_build_gemini_client):
        payload = {
            "overall_score": 84,
            "interpretation": "Strong match for backend work.",
            "matched_skills": ["Python", "SQL", "Python"],
            "missing_skills": ["AWS"],
            "job_skills": ["Python", "SQL", "AWS"],
            "section_analysis": {
                "sections": [
                    {
                        "name": "Experience",
                        "score": 90,
                        "matched_skills": ["Python", "SQL"],
                        "detected_skills": ["Python", "SQL", "Docker"],
                    }
                ],
                "missing_sections": ["Certifications"],
            },
            "role_matches": [
                {
                    "name": "Backend Developer",
                    "focus_area": "Server-side",
                    "summary": "Best fit role.",
                    "score": 86,
                    "matched_skills": ["Python", "SQL"],
                    "missing_skills": ["AWS"],
                }
            ],
            "career_path": {
                "current_role": "Backend Developer",
                "current_role_score": 86,
                "priority_skills": ["AWS", "System Design"],
                "next_steps": [
                    {
                        "name": "Senior Backend Developer",
                        "summary": "Natural next step.",
                        "readiness_score": 72,
                        "matched_skills": ["Python"],
                        "missing_skills": ["AWS", "System Design"],
                    }
                ],
            },
            "market_trends": {
                "market_readiness_score": 67,
                "top_trending_skills": [
                    {"skill": "Python", "demand_score": 9, "in_resume": True, "in_job_desc": True},
                    {"skill": "AWS", "demand_score": 8, "in_resume": False, "in_job_desc": True},
                ],
                "matched_trending_skills": ["Python"],
                "missing_trending_skills": ["AWS"],
                "job_aligned_trending_skills": ["Python", "AWS"],
                "target_roles": ["Backend Developer"],
            },
            "suggestions": ["Add AWS deployment examples."],
            "report": ["Show more cloud impact in projects."],
        }
        mock_client = Mock()
        mock_client.models.generate_content.return_value = Mock(text=json.dumps(payload))
        fake_types = Mock()
        fake_types.GenerateContentConfig.side_effect = lambda **kwargs: kwargs
        mock_build_gemini_client.return_value = (mock_client, fake_types)

        result = analyze_resume_with_gemini("resume text", "job text", api_key="test-key", model="gemini-test")

        self.assertEqual(result["overall_score"], 84.0)
        self.assertEqual(result["matched_skills"], ["python", "sql"])
        self.assertEqual(result["missing_skills"], ["aws"])
        self.assertEqual(result["job_skills"], ["python", "sql", "aws"])
        self.assertEqual(result["section_analysis"]["sections"][0]["method"], "gemini_structured")
        self.assertEqual(result["market_trends"]["top_trending_skills"][0]["skill"], "python")
        self.assertEqual(result["career_path"]["priority_skills"], ["aws", "system design"])
        self.assertEqual(result["analysis_engine_label"], "Gemini (gemini-test)")

    @patch.dict(os.environ, {}, clear=True)
    def test_analyze_resume_with_gemini_requires_api_key(self):
        with self.assertRaisesRegex(GeminiAnalysisError, "GEMINI_API_KEY"):
            analyze_resume_with_gemini("resume text", "job text")

    @patch("gemini_analysis._build_gemini_client")
    def test_analyze_resume_with_gemini_accepts_code_fenced_json(self, mock_build_gemini_client):
        payload = {
            "overall_score": 75,
            "interpretation": "Solid fit.",
            "matched_skills": ["Python"],
            "missing_skills": ["Docker"],
            "job_skills": ["Python", "Docker"],
            "section_analysis": {"sections": [], "missing_sections": []},
            "role_matches": [],
            "career_path": {"current_role": "Engineer", "current_role_score": 75, "priority_skills": [], "next_steps": []},
            "market_trends": {"market_readiness_score": 50, "top_trending_skills": [], "matched_trending_skills": [], "missing_trending_skills": [], "job_aligned_trending_skills": [], "target_roles": []},
            "suggestions": ["Add Docker experience."],
            "report": ["Strengthen deployment examples."],
        }
        mock_client = Mock()
        mock_client.models.generate_content.return_value = Mock(text=f"```json\n{json.dumps(payload)}\n```")
        fake_types = Mock()
        fake_types.GenerateContentConfig.side_effect = lambda **kwargs: kwargs
        mock_build_gemini_client.return_value = (mock_client, fake_types)

        result = analyze_resume_with_gemini("resume text", "job text", api_key="test-key", model="gemini-test")

        self.assertEqual(result["overall_score"], 75.0)
        self.assertEqual(result["missing_skills"], ["docker"])

    @patch("gemini_analysis._build_gemini_client")
    def test_analyze_resume_with_gemini_reads_candidate_part_text(self, mock_build_gemini_client):
        payload = {
            "overall_score": 81,
            "interpretation": "Good alignment.",
            "matched_skills": ["Python"],
            "missing_skills": ["AWS"],
            "job_skills": ["Python", "AWS"],
            "section_analysis": {"sections": [], "missing_sections": []},
            "role_matches": [],
            "career_path": {"current_role": "Engineer", "current_role_score": 81, "priority_skills": [], "next_steps": []},
            "market_trends": {"market_readiness_score": 55, "top_trending_skills": [], "matched_trending_skills": [], "missing_trending_skills": [], "job_aligned_trending_skills": [], "target_roles": []},
            "suggestions": ["Add cloud examples."],
            "report": ["Show production deployment impact."],
        }
        response = SimpleNamespace(
            text="",
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[SimpleNamespace(text=f"Here is the JSON payload:\n{json.dumps(payload)}")]
                    )
                )
            ],
        )
        mock_client = Mock()
        mock_client.models.generate_content.return_value = response
        fake_types = Mock()
        fake_types.GenerateContentConfig.side_effect = lambda **kwargs: kwargs
        mock_build_gemini_client.return_value = (mock_client, fake_types)

        result = analyze_resume_with_gemini("resume text", "job text", api_key="test-key", model="gemini-test")

        self.assertEqual(result["overall_score"], 81.0)
        self.assertEqual(result["matched_skills"], ["python"])


if __name__ == "__main__":
    unittest.main()