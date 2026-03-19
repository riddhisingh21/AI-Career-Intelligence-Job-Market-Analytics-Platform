import unittest
from unittest.mock import patch

from analyzer import analyze_resume_sections, extract_resume_sections, highlight_skills, skill_analysis
from market_analysis import job_skill_analysis
from skills import extract_skills_from_text


class DynamicSkillExtractionTests(unittest.TestCase):
    def test_extract_skills_from_text_finds_dynamic_skills(self):
        job_desc = """
        Required skills: Python, SQL, Docker, Kubernetes, GraphQL
        Experience with React and Node.js.
        """

        extracted = extract_skills_from_text(job_desc)

        self.assertIn("python", extracted)
        self.assertIn("sql", extracted)
        self.assertIn("docker", extracted)
        self.assertIn("kubernetes", extracted)
        self.assertIn("graphql", extracted)
        self.assertIn("node.js", extracted)

    def test_skill_analysis_matches_dynamic_job_skills(self):
        resume = "Experienced in Python, Docker, GraphQL and Node.js APIs."
        job_desc = "Required skills: Python, Docker, Kubernetes, GraphQL, Node.js"

        matched, missing = skill_analysis(resume, job_desc)

        self.assertEqual(matched, ["docker", "graphql", "node.js", "python"])
        self.assertEqual(missing, ["kubernetes"])

    def test_job_skill_analysis_uses_dynamic_extraction(self):
        job_desc = "Technologies: FastAPI, PostgreSQL, Redis, AWS"

        job_skills = job_skill_analysis(job_desc)

        self.assertIn("fastapi", job_skills)
        self.assertIn("postgresql", job_skills)
        self.assertIn("redis", job_skills)
        self.assertIn("aws", job_skills)

    def test_highlight_skills_counts_special_character_skills(self):
        resume = "Node.js services with GraphQL. Node.js powers the API."

        counts = highlight_skills(resume, ["node.js", "graphql"])

        self.assertEqual(counts["node.js"], 2)
        self.assertEqual(counts["graphql"], 1)


class ResumeSectionAnalysisTests(unittest.TestCase):
    def test_extract_resume_sections_groups_common_headings(self):
        resume = """
        SUMMARY
        Data analyst with Python and SQL experience.
        TECHNICAL SKILLS
        Python, SQL, Tableau
        PROJECTS
        Built dashboards using Python and SQL.
        EDUCATION
        B.Tech in Computer Science
        """

        sections = extract_resume_sections(resume)

        self.assertEqual(list(sections), ["Summary", "Skills", "Projects", "Education"])
        self.assertIn("Data analyst", sections["Summary"])
        self.assertIn("Python, SQL, Tableau", sections["Skills"])

    def test_extract_resume_sections_falls_back_to_general_when_no_headings_exist(self):
        sections = extract_resume_sections("Python developer with SQL and AWS project experience.")

        self.assertEqual(list(sections), ["General"])

    def test_analyze_resume_sections_returns_scores_and_missing_sections(self):
        resume = """
        Summary
        Python backend developer.
        Skills
        Python, SQL, Docker
        Projects
        Built Python APIs and SQL services.
        """

        with patch(
            "analyzer.calculate_similarity_details",
            side_effect=[
                {"score": 70.0, "method": "embeddings"},
                {"score": 92.0, "method": "tfidf_fallback"},
                {"score": 80.0, "method": "embeddings"},
            ],
        ):
            result = analyze_resume_sections(resume, "Required skills: Python, SQL, AWS")

        self.assertEqual([section["name"] for section in result["sections"]], ["Summary", "Skills", "Projects"])
        self.assertEqual(result["sections"][1]["matched_skills"], ["python", "sql"])
        self.assertEqual(result["missing_sections"], ["Experience", "Education", "Certifications"])


if __name__ == "__main__":
    unittest.main()