from skills import group_skills_by_category


def _ranked_scores(items, label_key, score_key, limit=5):
    ranked_items = []

    for item in items:
        label = item.get(label_key)

        if not label:
            continue

        ranked_items.append(
            {
                "label": label,
                "score": round(float(item.get(score_key, 0.0)), 2),
            }
        )

    ranked_items.sort(key=lambda item: (-item["score"], item["label"]))
    return ranked_items[:limit]


def _average_score(items):
    if not items:
        return 0.0

    return round(sum(item["score"] for item in items) / len(items), 2)


def _build_skill_categories(matched, missing):
    matched_by_category = group_skills_by_category(matched)
    missing_by_category = group_skills_by_category(missing)
    grouped_categories = []

    for category in set(matched_by_category) | set(missing_by_category):
        matched_skills = matched_by_category.get(category, [])
        missing_skills = missing_by_category.get(category, [])
        grouped_categories.append(
            {
                "category": category,
                "matched_count": len(matched_skills),
                "missing_count": len(missing_skills),
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
            }
        )

    grouped_categories.sort(
        key=lambda item: (
            -(item["matched_count"] + item["missing_count"]),
            -item["matched_count"],
            item["category"],
        )
    )
    return grouped_categories


def _build_resume_dimensions(
    overall_score,
    skill_coverage_ratio,
    section_scores,
    role_scores,
    career_readiness,
    market_readiness_score,
):
    return [
        {"label": "ATS Match", "score": round(overall_score, 2)},
        {"label": "Skill Coverage", "score": round(skill_coverage_ratio, 2)},
        {"label": "Section Quality", "score": _average_score(section_scores)},
        {"label": "Role Fit", "score": role_scores[0]["score"] if role_scores else 0.0},
        {
            "label": "Career Readiness",
            "score": career_readiness[0]["score"] if career_readiness else 0.0,
        },
        {"label": "Market Readiness", "score": round(market_readiness_score, 2)},
    ]


def _build_recruiter_summary(
    overall_score,
    skill_coverage_ratio,
    matched,
    missing,
    priority_skills,
    section_scores,
    role_scores,
    market_readiness_score,
    market_alignment_count,
):
    if overall_score >= 80:
        hiring_signal = "Strong shortlist"
    elif overall_score >= 65:
        hiring_signal = "Promising fit"
    elif overall_score >= 50:
        hiring_signal = "Emerging fit"
    else:
        hiring_signal = "Needs stronger alignment"

    top_role = role_scores[0] if role_scores else None
    strongest_section = section_scores[0] if section_scores else None
    headline_target = top_role["label"] if top_role else "the target role"

    return {
        "headline": f"{hiring_signal} for {headline_target}",
        "hiring_signal": hiring_signal,
        "profile_note": (
            f"This resume currently covers {skill_coverage_ratio:.2f}% of the target skill set "
            f"and aligns best with {headline_target}."
        ),
        "top_role": top_role["label"] if top_role else "Not available",
        "top_role_score": top_role["score"] if top_role else 0.0,
        "strongest_section": strongest_section["label"] if strongest_section else "Not available",
        "strongest_section_score": strongest_section["score"] if strongest_section else 0.0,
        "top_strengths": matched[:4],
        "priority_gaps": (priority_skills or missing)[:4],
        "summary_lines": [
            (
                f"Top role alignment: {top_role['label']} ({top_role['score']:.2f}%)."
                if top_role
                else "Top role alignment is not available yet."
            ),
            (
                f"Strongest resume section: {strongest_section['label']} ({strongest_section['score']:.2f}%)."
                if strongest_section
                else "Section-level performance is not available yet."
            ),
            (
                f"Market readiness is {market_readiness_score:.2f}% with "
                f"{market_alignment_count} in-demand skills already present."
            ),
        ],
    }


def build_dashboard_snapshot(
    score,
    matched,
    missing,
    section_analysis,
    role_matches,
    career_path,
    market_trends,
):
    matched_count = len(matched)
    missing_count = len(missing)
    total_skills = matched_count + missing_count
    skill_coverage_ratio = round((matched_count / total_skills) * 100, 2) if total_skills else 0.0
    section_scores = _ranked_scores(section_analysis.get("sections", []), "name", "score")
    role_scores = _ranked_scores(role_matches, "name", "score", limit=3)
    career_readiness = _ranked_scores(
        career_path.get("next_steps", []), "name", "readiness_score", limit=3
    )
    market_readiness_score = round(float(market_trends.get("market_readiness_score", 0.0)), 2)
    skill_categories = _build_skill_categories(matched, missing)
    priority_skills = career_path.get("priority_skills", [])[:5]

    return {
        "overall_score": round(score, 2),
        "skill_coverage": [
            {"label": "Matched Skills", "value": matched_count},
            {"label": "Missing Skills", "value": missing_count},
        ],
        "skill_coverage_ratio": skill_coverage_ratio,
        "section_scores": section_scores,
        "role_scores": role_scores,
        "career_readiness": career_readiness,
        "market_readiness_score": market_readiness_score,
        "market_alignment_count": len(market_trends.get("matched_trending_skills", [])),
        "market_gap_count": len(market_trends.get("missing_trending_skills", [])),
        "priority_skills": priority_skills,
        "top_trending_skills": [
            item["skill"] for item in market_trends.get("top_trending_skills", [])[:5]
        ],
        "resume_dimensions": _build_resume_dimensions(
            score,
            skill_coverage_ratio,
            section_scores,
            role_scores,
            career_readiness,
            market_readiness_score,
        ),
        "recruiter_summary": _build_recruiter_summary(
            score,
            skill_coverage_ratio,
            matched,
            missing,
            priority_skills,
            section_scores,
            role_scores,
            market_readiness_score,
            len(market_trends.get("matched_trending_skills", [])),
        ),
        "skill_categories": skill_categories,
    }