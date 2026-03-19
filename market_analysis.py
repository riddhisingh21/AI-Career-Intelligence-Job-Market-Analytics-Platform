from skills import extract_skills_from_text


ROLE_PROFILES = [
    {
        "name": "Data Analyst",
        "focus_area": "Analytics & BI",
        "summary": "Works with dashboards, reporting, SQL querying, and business insights.",
        "skills": ["python", "sql", "data analysis", "excel", "tableau", "power bi"],
    },
    {
        "name": "Data Scientist",
        "focus_area": "ML & Advanced Analytics",
        "summary": "Builds predictive models and experiments using statistics and machine learning.",
        "skills": ["python", "sql", "machine learning", "deep learning", "nlp", "pandas", "numpy"],
    },
    {
        "name": "Machine Learning Engineer",
        "focus_area": "ML Systems",
        "summary": "Deploys and productionizes machine learning models and data pipelines.",
        "skills": ["python", "machine learning", "tensorflow", "aws", "docker", "sql"],
    },
    {
        "name": "Backend Developer",
        "focus_area": "Server-side Development",
        "summary": "Builds APIs, services, and application logic for server-side systems.",
        "skills": ["python", "java", "sql", "django", "fastapi", "aws", "docker"],
    },
    {
        "name": "Frontend Developer",
        "focus_area": "Client-side Development",
        "summary": "Develops interactive web interfaces and user-facing application features.",
        "skills": ["react", "javascript", "html", "css", "typescript", "figma"],
    },
    {
        "name": "Full Stack Developer",
        "focus_area": "Web Application Development",
        "summary": "Works across frontend and backend systems to deliver complete web apps.",
        "skills": ["python", "react", "sql", "django", "javascript", "aws"],
    },
    {
        "name": "Cloud / DevOps Engineer",
        "focus_area": "Cloud Infrastructure",
        "summary": "Automates deployment, cloud operations, and infrastructure reliability.",
        "skills": ["aws", "docker", "kubernetes", "terraform", "python", "linux"],
    },
]

CAREER_PATHS = {
    "Data Analyst": [
        {
            "name": "Senior Data Analyst",
            "summary": "Take ownership of deeper reporting, stakeholder communication, and advanced analytics.",
            "skills": ["python", "sql", "tableau", "power bi", "excel", "statistics"],
        },
        {
            "name": "Data Scientist",
            "summary": "Transition into predictive modeling, experimentation, and machine learning workflows.",
            "skills": ["python", "sql", "machine learning", "statistics", "pandas", "numpy"],
        },
    ],
    "Data Scientist": [
        {
            "name": "Senior Data Scientist",
            "summary": "Lead modeling projects, experimentation strategy, and business impact analysis.",
            "skills": ["python", "sql", "machine learning", "deep learning", "nlp", "statistics"],
        },
        {
            "name": "Machine Learning Engineer",
            "summary": "Move toward model deployment, scalability, and production ML systems.",
            "skills": ["python", "machine learning", "tensorflow", "aws", "docker", "sql"],
        },
    ],
    "Machine Learning Engineer": [
        {
            "name": "Senior Machine Learning Engineer",
            "summary": "Own end-to-end ML platforms, deployment, monitoring, and system reliability.",
            "skills": ["python", "machine learning", "tensorflow", "aws", "docker", "kubernetes"],
        },
        {
            "name": "AI Engineer",
            "summary": "Build intelligent applications using applied ML, NLP, and production systems.",
            "skills": ["python", "nlp", "machine learning", "aws", "docker", "tensorflow"],
        },
    ],
    "Backend Developer": [
        {
            "name": "Senior Backend Developer",
            "summary": "Take on larger API architectures, reliability, and backend system design.",
            "skills": ["python", "sql", "django", "fastapi", "aws", "docker"],
        },
        {
            "name": "Full Stack Developer",
            "summary": "Expand into user-facing features and complete web application ownership.",
            "skills": ["python", "sql", "react", "javascript", "django", "aws"],
        },
        {
            "name": "Cloud / DevOps Engineer",
            "summary": "Shift toward cloud deployment, automation, and infrastructure operations.",
            "skills": ["aws", "docker", "kubernetes", "terraform", "python", "linux"],
        },
    ],
    "Frontend Developer": [
        {
            "name": "Senior Frontend Developer",
            "summary": "Lead UI architecture, performance optimization, and frontend quality standards.",
            "skills": ["react", "javascript", "html", "css", "typescript", "figma"],
        },
        {
            "name": "Full Stack Developer",
            "summary": "Broaden from frontend into backend services and database-backed applications.",
            "skills": ["react", "javascript", "python", "sql", "django", "aws"],
        },
    ],
    "Full Stack Developer": [
        {
            "name": "Senior Full Stack Developer",
            "summary": "Handle end-to-end application architecture, delivery, and system ownership.",
            "skills": ["python", "react", "sql", "django", "javascript", "aws"],
        },
        {
            "name": "Technical Lead",
            "summary": "Grow into technical decision-making, mentoring, and delivery leadership.",
            "skills": ["python", "react", "sql", "aws", "system design", "leadership"],
        },
    ],
    "Cloud / DevOps Engineer": [
        {
            "name": "Senior Cloud / DevOps Engineer",
            "summary": "Lead infrastructure reliability, platform automation, and scalable deployment practices.",
            "skills": ["aws", "docker", "kubernetes", "terraform", "python", "linux"],
        },
        {
            "name": "Platform Engineer",
            "summary": "Build internal tooling and scalable developer platforms for engineering teams.",
            "skills": ["aws", "docker", "kubernetes", "terraform", "python", "sql"],
        },
    ],
}


def job_skill_analysis(job_desc):
    return extract_skills_from_text(job_desc)


def recommend_job_roles(resume_text, top_n=3):
    resume_skills = set(extract_skills_from_text(resume_text))
    role_matches = []

    for role in ROLE_PROFILES:
        role_skills = role["skills"]
        matched_skills = [skill for skill in role_skills if skill in resume_skills]
        missing_skills = [skill for skill in role_skills if skill not in resume_skills]
        score = round((len(matched_skills) / len(role_skills)) * 100, 2) if role_skills else 0.0

        role_matches.append(
            {
                "name": role["name"],
                "focus_area": role["focus_area"],
                "summary": role["summary"],
                "score": score,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
            }
        )

    role_matches.sort(
        key=lambda item: (-item["score"], -len(item["matched_skills"]), item["name"])
    )
    return role_matches[:top_n]


def recommend_career_path(resume_text, role_matches=None):
    resume_skills = set(extract_skills_from_text(resume_text))
    role_matches = role_matches or recommend_job_roles(resume_text)

    if not role_matches:
        return {
            "current_role": None,
            "current_role_score": 0.0,
            "priority_skills": [],
            "next_steps": [],
        }

    top_role = role_matches[0]
    path_profiles = CAREER_PATHS.get(top_role["name"], [])
    next_steps = []
    missing_skill_counts = {}

    for path in path_profiles:
        path_skills = path["skills"]
        matched_skills = [skill for skill in path_skills if skill in resume_skills]
        missing_skills = [skill for skill in path_skills if skill not in resume_skills]
        readiness_score = round((len(matched_skills) / len(path_skills)) * 100, 2) if path_skills else 0.0

        for skill in missing_skills:
            missing_skill_counts[skill] = missing_skill_counts.get(skill, 0) + 1

        next_steps.append(
            {
                "name": path["name"],
                "summary": path["summary"],
                "readiness_score": readiness_score,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
            }
        )

    priority_skills = [
        skill
        for skill, _ in sorted(
            missing_skill_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ][:5]

    next_steps.sort(
        key=lambda item: (-item["readiness_score"], -len(item["matched_skills"]), item["name"])
    )

    return {
        "current_role": top_role["name"],
        "current_role_score": top_role["score"],
        "priority_skills": priority_skills,
        "next_steps": next_steps,
    }


def analyze_market_skill_trends(job_desc, resume_text, role_matches=None, top_n=6):
    resume_skills = set(extract_skills_from_text(resume_text))
    job_skills = set(extract_skills_from_text(job_desc))
    role_matches = role_matches or recommend_job_roles(resume_text, top_n=3)
    demand_scores = {}

    for index, role in enumerate(role_matches):
        role_weight = max(1, 3 - index)
        role_profile = next(
            (profile for profile in ROLE_PROFILES if profile["name"] == role["name"]),
            None,
        )

        if role_profile:
            for skill in role_profile["skills"]:
                demand_scores[skill] = demand_scores.get(skill, 0) + role_weight

        for next_step in CAREER_PATHS.get(role["name"], []):
            for skill in next_step["skills"]:
                demand_scores[skill] = demand_scores.get(skill, 0) + 1

    for skill in job_skills:
        demand_scores[skill] = demand_scores.get(skill, 0) + 3

    top_skills = [
        {
            "skill": skill,
            "demand_score": score,
            "in_resume": skill in resume_skills,
            "in_job_desc": skill in job_skills,
        }
        for skill, score in sorted(
            demand_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )[:top_n]
    ]

    matched_trending_skills = [item["skill"] for item in top_skills if item["in_resume"]]
    missing_trending_skills = [item["skill"] for item in top_skills if not item["in_resume"]]
    job_aligned_trending_skills = [item["skill"] for item in top_skills if item["in_job_desc"]]
    market_readiness_score = (
        round((len(matched_trending_skills) / len(top_skills)) * 100, 2)
        if top_skills
        else 0.0
    )

    return {
        "market_readiness_score": market_readiness_score,
        "top_trending_skills": top_skills,
        "matched_trending_skills": matched_trending_skills,
        "missing_trending_skills": missing_trending_skills,
        "job_aligned_trending_skills": job_aligned_trending_skills,
        "target_roles": [role["name"] for role in role_matches],
    }