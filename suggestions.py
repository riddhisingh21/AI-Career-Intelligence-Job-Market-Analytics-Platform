def generate_suggestions(missing_skills):

    suggestions = []

    for skill in missing_skills:

        suggestions.append(
            f"Consider adding projects or experience related to {skill}"
        )

    return suggestions


def interpret_score(score):

    if score >= 80:
        return "Excellent match with the job role"

    elif score >= 60:
        return "Good match but resume can improve"

    elif score >= 40:
        return "Moderate match. Consider improving skills"

    else:
        return "Low match. Resume needs improvement"


def improvement_report(score, missing_skills):

    report = []

    if score < 60:
        report.append("Your resume needs stronger alignment with the job description.")

    if missing_skills:

        report.append("Consider adding these skills:")

        for skill in missing_skills:
            report.append("- " + skill)

    report.append("Include measurable achievements in projects.")

    report.append("Use action verbs like Developed, Built, Implemented.")

    return report


def build_export_report(
    score,
    interpretation,
    matched_skills,
    missing_skills,
    skill_counts,
    job_skills,
    suggestions,
    report,
    similarity_method_label=None,
    section_analysis=None,
    missing_sections=None,
):

    matched_text = ", ".join(matched_skills) if matched_skills else "None"
    missing_text = ", ".join(missing_skills) if missing_skills else "None"
    job_skills_text = ", ".join(job_skills) if job_skills else "None"

    skill_count_lines = [f"- {skill}: {count} times" for skill, count in skill_counts.items()]

    if not skill_count_lines:
        skill_count_lines = ["- None"]

    suggestion_lines = [f"- {item}" for item in suggestions] or ["- None"]
    report_lines = [item if item.startswith("- ") else f"- {item}" for item in report] or ["- None"]
    section_lines = [
        f"- {item['name']}: {item['score']}% | Matched skills: {', '.join(item['matched_skills']) or 'None'}"
        for item in (section_analysis or [])
    ] or ["- None"]
    missing_sections_text = ", ".join(missing_sections) if missing_sections else "None"

    sections = [
        "AI Resume Analyzer Report",
        "",
        f"ATS Match Score: {score}%",
        f"Interpretation: {interpretation}",
        f"Similarity Engine: {similarity_method_label or 'Not Available'}",
        "",
        f"Matched Skills: {matched_text}",
        f"Missing Skills: {missing_text}",
        f"Top Skills Required in Job: {job_skills_text}",
        "",
        "Skill Occurrences in Resume:",
        *skill_count_lines,
        "",
        "Section-wise Resume Analysis:",
        *section_lines,
        f"Sections Not Clearly Found: {missing_sections_text}",
        "",
        "Improvement Suggestions:",
        *suggestion_lines,
        "",
        "Resume Improvement Report:",
        *report_lines,
    ]

    return "\n".join(sections)