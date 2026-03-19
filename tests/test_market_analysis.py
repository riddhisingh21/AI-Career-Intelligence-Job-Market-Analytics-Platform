import unittest

from market_analysis import analyze_market_skill_trends, recommend_career_path, recommend_job_roles


class JobRoleMatchingTests(unittest.TestCase):
    def test_recommend_job_roles_prioritizes_data_analyst_for_analytics_resume(self):
        resume = """
        Skills
        Python, SQL, Tableau, Power BI, Excel
        Experience
        Built reporting dashboards and performed business data analysis.
        """

        matches = recommend_job_roles(resume, top_n=3)

        self.assertEqual(matches[0]["name"], "Data Analyst")
        self.assertIn("python", matches[0]["matched_skills"])
        self.assertIn("sql", matches[0]["matched_skills"])
        self.assertIn("tableau", matches[0]["matched_skills"])

    def test_recommend_job_roles_includes_missing_skills_for_role_growth(self):
        resume = """
        Skills
        Python, SQL, Docker, FastAPI, AWS
        Projects
        Built backend APIs and deployed services to AWS.
        """

        matches = recommend_job_roles(resume, top_n=2)

        self.assertEqual(matches[0]["name"], "Backend Developer")
        self.assertIn("django", matches[0]["missing_skills"])
        self.assertEqual(len(matches), 2)

    def test_recommend_career_path_returns_next_steps_for_backend_resume(self):
        resume = """
        Skills
        Python, SQL, Docker, FastAPI, AWS
        Projects
        Built backend APIs and deployed services to AWS.
        """

        career_path = recommend_career_path(resume)

        self.assertEqual(career_path["current_role"], "Backend Developer")
        self.assertTrue(career_path["next_steps"])
        self.assertIn("django", career_path["priority_skills"])
        self.assertEqual(career_path["next_steps"][0]["name"], "Senior Backend Developer")

    def test_recommend_career_path_for_analytics_resume_suggests_data_growth(self):
        resume = """
        Skills
        Python, SQL, Tableau, Power BI, Excel
        Experience
        Built reporting dashboards and performed business data analysis.
        """

        career_path = recommend_career_path(resume)

        self.assertEqual(career_path["current_role"], "Data Analyst")
        next_step_names = [step["name"] for step in career_path["next_steps"]]
        self.assertIn("Data Scientist", next_step_names)
        self.assertIn("machine learning", career_path["priority_skills"])

    def test_analyze_market_skill_trends_identifies_high_demand_backend_gaps(self):
        resume = """
        Skills
        Python, SQL, Docker, FastAPI, AWS
        Projects
        Built backend APIs and deployed services to AWS.
        """
        job_desc = "Required skills: Python, SQL, AWS, Docker, Kubernetes"

        market_trends = analyze_market_skill_trends(job_desc, resume)

        top_skill_names = [item["skill"] for item in market_trends["top_trending_skills"]]
        self.assertIn("python", top_skill_names)
        self.assertIn("aws", top_skill_names)
        self.assertIn("django", market_trends["missing_trending_skills"])
        self.assertIn("Backend Developer", market_trends["target_roles"])
        self.assertGreater(market_trends["market_readiness_score"], 50)

    def test_analyze_market_skill_trends_uses_job_description_to_boost_target_skills(self):
        resume = """
        Skills
        Python, SQL, Tableau, Power BI, Excel
        Experience
        Built reporting dashboards and performed business data analysis.
        """
        job_desc = "Required skills: Python, SQL, Tableau, Power BI, Statistics"

        market_trends = analyze_market_skill_trends(job_desc, resume)

        self.assertIn("statistics", market_trends["job_aligned_trending_skills"])
        self.assertIn("statistics", market_trends["missing_trending_skills"])
        self.assertEqual(market_trends["target_roles"][0], "Data Analyst")


if __name__ == "__main__":
    unittest.main()