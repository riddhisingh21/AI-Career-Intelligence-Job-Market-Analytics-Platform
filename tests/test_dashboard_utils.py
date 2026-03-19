import unittest

from dashboard_utils import build_dashboard_snapshot


class DashboardUtilsTests(unittest.TestCase):
    def test_build_dashboard_snapshot_summarizes_analysis_data(self):
        snapshot = build_dashboard_snapshot(
            82.34,
            ["python", "sql", "aws"],
            ["django", "kubernetes"],
            {
                "sections": [
                    {"name": "Experience", "score": 88.0},
                    {"name": "Skills", "score": 76.5},
                ]
            },
            [
                {"name": "Backend Developer", "score": 71.43},
                {"name": "Cloud / DevOps Engineer", "score": 50.0},
            ],
            {
                "priority_skills": ["django", "kubernetes", "linux"],
                "next_steps": [
                    {"name": "Senior Backend Developer", "readiness_score": 66.67},
                    {"name": "Cloud / DevOps Engineer", "readiness_score": 50.0},
                ],
            },
            {
                "market_readiness_score": 66.67,
                "matched_trending_skills": ["python", "aws"],
                "missing_trending_skills": ["django"],
                "top_trending_skills": [
                    {"skill": "python"},
                    {"skill": "aws"},
                    {"skill": "django"},
                ],
            },
        )

        self.assertEqual(snapshot["overall_score"], 82.34)
        self.assertEqual(snapshot["skill_coverage_ratio"], 60.0)
        self.assertEqual(snapshot["skill_coverage"][0]["value"], 3)
        self.assertEqual(snapshot["section_scores"][0]["label"], "Experience")
        self.assertEqual(snapshot["role_scores"][0]["label"], "Backend Developer")
        self.assertEqual(snapshot["career_readiness"][0]["label"], "Senior Backend Developer")
        self.assertEqual(snapshot["market_alignment_count"], 2)
        self.assertEqual(snapshot["market_gap_count"], 1)
        self.assertEqual(snapshot["priority_skills"], ["django", "kubernetes", "linux"])
        self.assertEqual(snapshot["top_trending_skills"], ["python", "aws", "django"])
        self.assertEqual(snapshot["market_readiness_score"], 66.67)
        self.assertEqual(snapshot["resume_dimensions"][0]["label"], "ATS Match")
        self.assertEqual(snapshot["resume_dimensions"][1]["score"], 60.0)
        self.assertEqual(snapshot["recruiter_summary"]["hiring_signal"], "Strong shortlist")
        self.assertEqual(snapshot["recruiter_summary"]["top_role"], "Backend Developer")
        self.assertEqual(snapshot["recruiter_summary"]["strongest_section"], "Experience")
        self.assertEqual(snapshot["recruiter_summary"]["priority_gaps"], ["django", "kubernetes", "linux"])

        skill_categories = {item["category"]: item for item in snapshot["skill_categories"]}
        self.assertEqual(skill_categories["Cloud & DevOps"]["matched_count"], 1)
        self.assertEqual(skill_categories["Cloud & DevOps"]["missing_count"], 1)
        self.assertEqual(skill_categories["Programming"]["matched_skills"], ["python"])
        self.assertEqual(skill_categories["Web Development"]["missing_skills"], ["django"])

    def test_build_dashboard_snapshot_handles_empty_inputs(self):
        snapshot = build_dashboard_snapshot(
            0.0,
            [],
            [],
            {"sections": []},
            [],
            {"priority_skills": [], "next_steps": []},
            {
                "market_readiness_score": 0.0,
                "matched_trending_skills": [],
                "missing_trending_skills": [],
                "top_trending_skills": [],
            },
        )

        self.assertEqual(snapshot["skill_coverage_ratio"], 0.0)
        self.assertEqual(snapshot["section_scores"], [])
        self.assertEqual(snapshot["role_scores"], [])
        self.assertEqual(snapshot["career_readiness"], [])
        self.assertEqual(snapshot["market_alignment_count"], 0)
        self.assertEqual(snapshot["market_gap_count"], 0)
        self.assertEqual(snapshot["priority_skills"], [])
        self.assertEqual(snapshot["top_trending_skills"], [])
        self.assertEqual(snapshot["market_readiness_score"], 0.0)
        self.assertEqual(snapshot["skill_categories"], [])
        self.assertEqual(snapshot["recruiter_summary"]["hiring_signal"], "Needs stronger alignment")
        self.assertEqual(len(snapshot["resume_dimensions"]), 6)


if __name__ == "__main__":
    unittest.main()