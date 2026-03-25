import json
import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import extra_streamlit_components as stx
from datetime import datetime, timezone, timedelta
from pathlib import Path

from analyzer import (
    analyze_resume_sections,
    benchmark_similarity_methods,
    describe_similarity_method,
    skill_analysis,
    highlight_skills,
)
from dashboard_utils import build_dashboard_snapshot
from evaluation_utils import REQUIRED_DATASET_COLUMNS, evaluate_dataset_csv_text
from firebase_auth import (
    FirebaseAuthError,
    refresh_id_token,
    resolve_firebase_api_key,
    resolve_firebase_project_id,
    send_password_reset_email,
    sign_in_with_email_password,
    sign_up_with_email_password,
)
from firestore_store import (
    clear_analyses_firestore,
    get_recent_analyses_firestore,
    save_analysis_firestore,
)
from gemini_analysis import (
    GeminiAnalysisError,
    analyze_resume_with_gemini,
    resolve_gemini_api_key,
    resolve_gemini_model,
)
from export_utils import (
    build_csv_report,
    build_dataset_evaluation_csv_report,
    build_dataset_evaluation_text_report,
    build_pdf_report,
)
from history_store import (
    clear_analysis_history,
    get_recent_analyses,
    init_history_storage,
    save_analysis,
)
from pdf_parser import extract_text_from_resume
from market_analysis import (
    analyze_market_skill_trends,
    job_skill_analysis,
    recommend_career_path,
    recommend_job_roles,
)
from suggestions import (
    build_export_report,
    generate_suggestions,
    interpret_score,
    improvement_report,
)


AUTH_USER_SESSION_KEY = "auth_user"
SESSION_NOTICE_KEY = "session_notice"
FIREBASE_SESSION_COOKIE = "firebase_session"


# ---------------------------------------------------------------------------
# Cookie-based session persistence helpers
# ---------------------------------------------------------------------------

def _get_cookie_manager():
    """Return the app-wide CookieManager instance (rendered once per run)."""
    return stx.CookieManager(key="firebase_session_manager")


def _save_session_cookie(cookie_manager, auth_user):
    """Persist the Firebase refresh token + identity info to a 30-day cookie."""
    payload = json.dumps({
        "rt": auth_user.get("refresh_token", ""),
        "em": auth_user.get("email", ""),
        "uid": auth_user.get("local_id", ""),
    })
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    cookie_manager.set(FIREBASE_SESSION_COOKIE, payload, expires_at=expires_at)


def _delete_session_cookie(cookie_manager):
    """Remove the Firebase session cookie (called on sign-out)."""
    try:
        cookie_manager.delete(FIREBASE_SESSION_COOKIE)
    except Exception:
        pass


def _try_restore_session(cookie_value, api_key):
    """Try to rebuild auth_user from a stored cookie value by refreshing the ID token.

    ``cookie_value`` is the raw string stored in the browser cookie (may be None).
    Returns a valid auth_user dict on success, or None if the cookie is absent
    or the refresh token has been revoked / expired.
    """
    try:
        if not cookie_value:
            return None
        data = json.loads(cookie_value)
        refresh_token = data.get("rt", "")
        email = data.get("em", "")
        local_id = data.get("uid", "")
        if not refresh_token or not email:
            return None
        token_data = refresh_id_token(refresh_token, api_key=api_key)
        return {
            "email": email,
            "local_id": local_id,
            "id_token": token_data["id_token"],
            "refresh_token": token_data["refresh_token"],
            "expires_in": token_data["expires_in"],
        }
    except Exception:
        return None


def render_recent_history(auth_user=None):
    st.sidebar.subheader("Recent Analyses")

    user_id = (auth_user or {}).get("local_id", "")
    id_token = (auth_user or {}).get("id_token", "")
    user_email = (auth_user or {}).get("email", "")
    project_id = resolve_firebase_project_id(st.secrets)
    use_firestore = bool(project_id and user_id and id_token)

    if use_firestore:
        st.sidebar.caption("Synced to your Firebase account.")
        try:
            history_items = get_recent_analyses_firestore(user_id, id_token, project_id)
        except Exception:
            history_items = get_recent_analyses(user_email=user_email)
    else:
        st.sidebar.caption("Saved locally for this signed-in account on this device.")
        history_items = get_recent_analyses(user_email=user_email)

    if history_items and st.sidebar.button("Clear History", use_container_width=True):
        try:
            if use_firestore:
                clear_analyses_firestore(user_id, id_token, project_id)
            else:
                clear_analysis_history(user_email=user_email)
            st.sidebar.success("Analysis history cleared.")
            st.rerun()
        except Exception:
            st.sidebar.error("Could not clear analysis history.")

    if not history_items:
        st.sidebar.info("No saved analyses yet.")
        return

    for item in history_items:
        score_label = f"{item['score']:.2f}"

        with st.sidebar.expander(f"{item['resume_name']} ({score_label}%)"):
            st.write("Saved:", item["created_at"])
            st.write("Interpretation:", item["interpretation"])
            st.write("Matched Skills:", ", ".join(item["matched_skills"]) or "None")
            st.write("Missing Skills:", ", ".join(item["missing_skills"]) or "None")


def get_authenticated_user():
    auth_user = st.session_state.get(AUTH_USER_SESSION_KEY)
    return auth_user if isinstance(auth_user, dict) else None


def set_session_notice(level, message):
    st.session_state[SESSION_NOTICE_KEY] = {"level": level, "message": message}


def render_session_notice():
    notice = st.session_state.pop(SESSION_NOTICE_KEY, None)

    if not isinstance(notice, dict):
        return

    level = str(notice.get("level", "info"))
    message = str(notice.get("message", "")).strip()

    if not message:
        return

    getattr(st, level, st.info)(message)


def render_status_list(title, items, renderer, empty_message):
    st.subheader(title)

    if items:
        for item in items:
            renderer(item)
    else:
        st.info(empty_message)


def render_bullet_list(title, items, empty_message):
    st.subheader(title)

    if items:
        for item in items:
            st.write(f"- {item}")
    else:
        st.info(empty_message)


def render_section_analysis(section_analysis):
    st.subheader("Section-wise Resume Analysis")

    sections = section_analysis["sections"]
    missing_sections = section_analysis["missing_sections"]

    detected_col, missing_col = st.columns(2)
    detected_col.metric("Detected Sections", len(sections))
    missing_col.metric("Undetected Standard Sections", len(missing_sections))

    if len(sections) == 1 and sections[0]["name"] == "General":
        st.info(
            "Clear headings like Skills, Experience, Projects, and Education were not detected, "
            "so the resume was analyzed as general content."
        )
    elif missing_sections:
        st.caption("Sections not clearly found: " + ", ".join(missing_sections))

    for section in sections:
        matched_skills = ", ".join(section["matched_skills"]) or "None"
        detected_skills = ", ".join(section["detected_skills"][:6]) or "None"

        with st.expander(f"{section['name']} — {section['score']:.2f}%"):
            st.write("Interpretation:", interpret_score(section["score"]))
            st.caption(f"Similarity engine: {describe_similarity_method(section['method'])}")
            st.write("Matched job skills in this section:", matched_skills)
            st.write("Detected skills in this section:", detected_skills)


def render_role_matches(role_matches):
    st.subheader("Job Role Matching")
    st.caption("Best-fit roles based on the skills detected in the uploaded resume.")

    if not role_matches:
        st.info("No role recommendations are available yet.")
        return

    top_role = role_matches[0]
    top_role_col, count_col = st.columns(2)
    top_role_col.metric("Top Recommended Role", top_role["name"])
    count_col.metric("Role Recommendations", len(role_matches))

    for role in role_matches:
        matched_skills = ", ".join(role["matched_skills"]) or "None"
        missing_skills = ", ".join(role["missing_skills"][:5]) or "None"

        with st.expander(f"{role['name']} — {role['score']:.2f}%"):
            st.write("Focus area:", role["focus_area"])
            st.write("Role summary:", role["summary"])
            st.write("Matched skills:", matched_skills)
            st.write("Skills to strengthen:", missing_skills)


def render_career_path(career_path):
    st.subheader("Career Path Recommendation")
    st.caption("Suggested next-step roles and priority skills based on the current best-fit role.")

    if not career_path["current_role"]:
        st.info("Career path recommendations are not available yet.")
        return

    role_col, readiness_col = st.columns(2)
    role_col.metric("Current Best-fit Role", career_path["current_role"])
    readiness_col.metric("Current Role Alignment", f"{career_path['current_role_score']:.2f}%")

    priority_skills = ", ".join(career_path["priority_skills"]) or "None"
    st.write("Priority skills to build next:", priority_skills)

    for step in career_path["next_steps"]:
        matched_skills = ", ".join(step["matched_skills"]) or "None"
        missing_skills = ", ".join(step["missing_skills"][:5]) or "None"

        with st.expander(f"{step['name']} — readiness {step['readiness_score']:.2f}%"):
            st.write("Career move summary:", step["summary"])
            st.write("Already demonstrated:", matched_skills)
            st.write("Skills to build:", missing_skills)


def render_market_trends(market_trends):
    st.subheader("Job Market Skill Trend Analysis")
    st.caption("In-demand skills inferred from your target roles, growth paths, and the current job description.")

    top_trending_skills = market_trends["top_trending_skills"]

    if not top_trending_skills:
        st.info("Market trend insights are not available yet.")
        return

    readiness_col, matched_col, gaps_col = st.columns(3)
    readiness_col.metric("Market Readiness", f"{market_trends['market_readiness_score']:.2f}%")
    matched_col.metric("In-demand Skills Present", len(market_trends["matched_trending_skills"]))
    gaps_col.metric("High-demand Gaps", len(market_trends["missing_trending_skills"]))

    trend_chart = go.Figure(
        go.Bar(
            x=[item["skill"] for item in top_trending_skills],
            y=[item["demand_score"] for item in top_trending_skills],
            marker_color=["#22c55e" if item["in_resume"] else "#f59e0b" for item in top_trending_skills],
        )
    )
    trend_chart.update_layout(
        height=320,
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        xaxis_title="Skills",
        yaxis_title="Demand score",
    )
    st.plotly_chart(trend_chart, use_container_width=True)

    trend_col1, trend_col2 = st.columns(2)

    with trend_col1:
        render_bullet_list(
            "Market-aligned Skills Already Present",
            market_trends["matched_trending_skills"],
            "No market-aligned skills were detected yet.",
        )

    with trend_col2:
        render_bullet_list(
            "High-demand Skills to Add",
            market_trends["missing_trending_skills"],
            "No high-demand skill gaps were detected.",
        )

    st.caption("Target role context: " + ", ".join(market_trends["target_roles"]))


def render_analytics_dashboard(dashboard_snapshot):
    st.subheader("Interactive Analytics Dashboard")
    st.caption("Compare skill coverage, section performance, role fit, and next-step readiness in one view.")

    role_scores = dashboard_snapshot["role_scores"]
    career_readiness = dashboard_snapshot["career_readiness"]
    recruiter_summary = dashboard_snapshot["recruiter_summary"]
    resume_dimensions = dashboard_snapshot["resume_dimensions"]
    skill_categories = dashboard_snapshot["skill_categories"]

    coverage_col, role_col, career_col, market_col = st.columns(4)
    coverage_col.metric("Skill Coverage", f"{dashboard_snapshot['skill_coverage_ratio']:.2f}%")
    role_col.metric("Top Role Fit", f"{role_scores[0]['score']:.2f}%" if role_scores else "0.00%")
    career_col.metric(
        "Best Next-step Readiness",
        f"{career_readiness[0]['score']:.2f}%" if career_readiness else "0.00%",
    )
    market_col.metric("Market Readiness", f"{dashboard_snapshot['market_readiness_score']:.2f}%")

    top_row_col1, top_row_col2 = st.columns(2)

    with top_row_col1:
        coverage_chart = go.Figure(
            go.Pie(
                labels=[item["label"] for item in dashboard_snapshot["skill_coverage"]],
                values=[item["value"] for item in dashboard_snapshot["skill_coverage"]],
                hole=0.55,
                marker_colors=["#22c55e", "#ef4444"],
            )
        )
        coverage_chart.update_layout(height=320, margin={"l": 20, "r": 20, "t": 40, "b": 20}, title="Skill Coverage")
        st.plotly_chart(coverage_chart, use_container_width=True)

    with top_row_col2:
        if resume_dimensions:
            radar_labels = [item["label"] for item in resume_dimensions]
            radar_scores = [item["score"] for item in resume_dimensions]
            radar_chart = go.Figure(
                go.Scatterpolar(
                    r=radar_scores + [radar_scores[0]],
                    theta=radar_labels + [radar_labels[0]],
                    fill="toself",
                    line={"color": "#6366f1"},
                    fillcolor="rgba(99, 102, 241, 0.25)",
                    name="Resume dimensions",
                )
            )
            radar_chart.update_layout(
                height=320,
                margin={"l": 20, "r": 20, "t": 40, "b": 20},
                title="Resume Dimensions Radar",
                showlegend=False,
                polar={"radialaxis": {"visible": True, "range": [0, 100]}},
            )
            st.plotly_chart(radar_chart, use_container_width=True)
        else:
            st.info("Resume-dimension analytics are not available yet.")

    middle_row_col1, middle_row_col2 = st.columns(2)

    with middle_row_col1:
        if dashboard_snapshot["section_scores"]:
            section_chart = go.Figure(
                go.Bar(
                    x=[item["label"] for item in dashboard_snapshot["section_scores"]],
                    y=[item["score"] for item in dashboard_snapshot["section_scores"]],
                    marker_color="#14b8a6",
                )
            )
            section_chart.update_layout(
                height=320,
                margin={"l": 20, "r": 20, "t": 40, "b": 20},
                title="Section Performance",
                xaxis_title="Resume sections",
                yaxis_title="Score",
            )
            st.plotly_chart(section_chart, use_container_width=True)
        else:
            st.info("Section comparison is not available yet.")

    with middle_row_col2:
        st.markdown("#### Recruiter-style Summary Card")

        if recruiter_summary["hiring_signal"] == "Strong shortlist":
            st.success(f"Hiring signal: {recruiter_summary['hiring_signal']}")
        elif recruiter_summary["hiring_signal"] == "Needs stronger alignment":
            st.warning(f"Hiring signal: {recruiter_summary['hiring_signal']}")
        else:
            st.info(f"Hiring signal: {recruiter_summary['hiring_signal']}")

        st.write(recruiter_summary["headline"])
        st.caption(recruiter_summary["profile_note"])

        summary_metric_col1, summary_metric_col2 = st.columns(2)
        summary_metric_col1.metric("Best-fit Role", recruiter_summary["top_role"])
        summary_metric_col2.metric("Strongest Section", recruiter_summary["strongest_section"])

        render_bullet_list(
            "Recruiter Notes",
            recruiter_summary["summary_lines"],
            "No recruiter notes are available yet.",
        )

        strengths_col, gaps_col = st.columns(2)

        with strengths_col:
            render_bullet_list(
                "Top Strengths",
                recruiter_summary["top_strengths"],
                "No clear strengths were identified yet.",
            )

        with gaps_col:
            render_bullet_list(
                "Priority Gaps",
                recruiter_summary["priority_gaps"],
                "No priority gaps were identified yet.",
            )

    bottom_row_col1, bottom_row_col2 = st.columns(2)

    with bottom_row_col1:
        if role_scores:
            role_chart = go.Figure(
                go.Bar(
                    x=[item["label"] for item in role_scores],
                    y=[item["score"] for item in role_scores],
                    marker_color="#3b82f6",
                )
            )
            role_chart.update_layout(
                height=320,
                margin={"l": 20, "r": 20, "t": 40, "b": 20},
                title="Role Match Comparison",
                xaxis_title="Roles",
                yaxis_title="Score",
            )
            st.plotly_chart(role_chart, use_container_width=True)
        else:
            st.info("Role comparison is not available yet.")

    with bottom_row_col2:
        if career_readiness:
            readiness_chart = go.Figure(
                go.Bar(
                    x=[item["label"] for item in career_readiness],
                    y=[item["score"] for item in career_readiness],
                    marker_color="#8b5cf6",
                )
            )
            readiness_chart.update_layout(
                height=320,
                margin={"l": 20, "r": 20, "t": 40, "b": 20},
                title="Career Readiness Comparison",
                xaxis_title="Next-step roles",
                yaxis_title="Readiness",
            )
            st.plotly_chart(readiness_chart, use_container_width=True)
        else:
            st.info("Career readiness comparison is not available yet.")

    st.markdown("#### Skill-category Grouping")

    if skill_categories:
        category_chart = go.Figure()
        category_chart.add_trace(
            go.Bar(
                name="Matched",
                x=[item["category"] for item in skill_categories],
                y=[item["matched_count"] for item in skill_categories],
                marker_color="#22c55e",
            )
        )
        category_chart.add_trace(
            go.Bar(
                name="Missing",
                x=[item["category"] for item in skill_categories],
                y=[item["missing_count"] for item in skill_categories],
                marker_color="#ef4444",
            )
        )
        category_chart.update_layout(
            barmode="group",
            height=320,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            xaxis_title="Skill categories",
            yaxis_title="Skill count",
        )
        st.plotly_chart(category_chart, use_container_width=True)

        category_col1, category_col2 = st.columns(2)

        with category_col1:
            matched_category_lines = [
                f"{item['category']}: {', '.join(item['matched_skills'])}"
                for item in skill_categories
                if item["matched_skills"]
            ]
            render_bullet_list(
                "Category Strengths",
                matched_category_lines,
                "No category strengths were identified yet.",
            )

        with category_col2:
            missing_category_lines = [
                f"{item['category']}: {', '.join(item['missing_skills'])}"
                for item in skill_categories
                if item["missing_skills"]
            ]
            render_bullet_list(
                "Category Gaps",
                missing_category_lines,
                "No category gaps were identified yet.",
            )
    else:
        st.info("Skill-category insights are not available yet.")

    insights_col1, insights_col2 = st.columns(2)

    with insights_col1:
        render_bullet_list(
            "Priority Skills to Build",
            dashboard_snapshot["priority_skills"],
            "No priority skills were identified yet.",
        )

    with insights_col2:
        render_bullet_list(
            "Top Trending Skills Snapshot",
            dashboard_snapshot["top_trending_skills"],
            "No trending skills were available for the dashboard.",
        )


def render_similarity_benchmark(similarity_benchmark):
    st.subheader("Similarity Benchmark Comparison")
    st.caption("Lightweight evaluation comparing semantic embeddings with the TF-IDF baseline for this resume-job pair.")

    embedding_result = next(
        (item for item in similarity_benchmark["methods"] if item["method"] == "embeddings"),
        None,
    )
    tfidf_result = next(
        (item for item in similarity_benchmark["methods"] if item["method"] == "tfidf_baseline"),
        None,
    )
    available_methods = [item for item in similarity_benchmark["methods"] if item["available"]]

    engine_col, embedding_col, tfidf_col, gap_col = st.columns(4)
    engine_col.metric("Selected Engine", similarity_benchmark["selected_method_label"])
    embedding_col.metric(
        "Embeddings Score",
        f"{embedding_result['score']:.2f}%" if embedding_result and embedding_result["available"] else "Unavailable",
    )
    tfidf_col.metric(
        "TF-IDF Baseline",
        f"{tfidf_result['score']:.2f}%" if tfidf_result and tfidf_result["available"] else "Unavailable",
    )
    gap_col.metric("Score Delta", f"{similarity_benchmark['score_gap']:.2f}%")

    if available_methods:
        benchmark_chart = go.Figure(
            go.Bar(
                x=[item["label"] for item in available_methods],
                y=[item["score"] for item in available_methods],
                marker_color=["#2563eb", "#f59e0b"][: len(available_methods)],
            )
        )
        benchmark_chart.update_layout(
            height=320,
            margin={"l": 20, "r": 20, "t": 30, "b": 20},
            xaxis_title="Similarity methods",
            yaxis_title="Score",
        )
        st.plotly_chart(benchmark_chart, use_container_width=True)

    st.caption(similarity_benchmark["benchmark_note"])


def run_local_analysis(resume_text, job_desc, similarity_benchmark=None):
    similarity_benchmark = similarity_benchmark or benchmark_similarity_methods(resume_text, job_desc)
    score = similarity_benchmark["selected_score"]
    matched, missing = skill_analysis(resume_text, job_desc)
    section_analysis = analyze_resume_sections(resume_text, job_desc)
    skill_counts = highlight_skills(resume_text, matched)
    job_skills = job_skill_analysis(job_desc)
    role_matches = recommend_job_roles(resume_text)
    career_path = recommend_career_path(resume_text, role_matches)
    market_trends = analyze_market_skill_trends(job_desc, resume_text, role_matches)
    dashboard_snapshot = build_dashboard_snapshot(
        score,
        matched,
        missing,
        section_analysis,
        role_matches,
        career_path,
        market_trends,
    )

    return {
        "score": score,
        "analysis_engine_label": similarity_benchmark["selected_method_label"],
        "similarity_benchmark": similarity_benchmark,
        "matched": matched,
        "missing": missing,
        "section_analysis": section_analysis,
        "skill_counts": skill_counts,
        "job_skills": job_skills,
        "role_matches": role_matches,
        "career_path": career_path,
        "market_trends": market_trends,
        "dashboard_snapshot": dashboard_snapshot,
        "suggestions": generate_suggestions(missing),
        "interpretation": interpret_score(score),
        "report": improvement_report(score, missing),
        "notice_type": None,
        "notice_message": None,
        "uses_gemini": False,
    }


def run_primary_analysis(resume_text, job_desc):
    similarity_benchmark = benchmark_similarity_methods(resume_text, job_desc)
    gemini_api_key = resolve_gemini_api_key(st.secrets)

    if not gemini_api_key:
        local_result = run_local_analysis(resume_text, job_desc, similarity_benchmark)
        local_result["notice_type"] = "info"
        local_result["notice_message"] = (
            "Gemini dynamic analysis is not configured yet. "
            "Set GEMINI_API_KEY to enable the Gemini-powered path."
        )
        return local_result

    try:
        gemini_result = analyze_resume_with_gemini(
            resume_text,
            job_desc,
            api_key=gemini_api_key,
            model=resolve_gemini_model(st.secrets),
        )
    except GeminiAnalysisError as error:
        local_result = run_local_analysis(resume_text, job_desc, similarity_benchmark)
        local_result["notice_type"] = "warning"
        local_result["notice_message"] = f"Gemini analysis failed ({error}). The app used the local fallback instead."
        return local_result

    score = gemini_result["overall_score"]
    matched = gemini_result["matched_skills"]
    missing = gemini_result["missing_skills"]
    section_analysis = gemini_result["section_analysis"]
    skill_counts = highlight_skills(resume_text, matched)
    job_skills = gemini_result["job_skills"]
    role_matches = gemini_result["role_matches"]
    career_path = gemini_result["career_path"]
    market_trends = gemini_result["market_trends"]
    dashboard_snapshot = build_dashboard_snapshot(
        score,
        matched,
        missing,
        section_analysis,
        role_matches,
        career_path,
        market_trends,
    )

    return {
        "score": score,
        "analysis_engine_label": gemini_result["analysis_engine_label"],
        "similarity_benchmark": similarity_benchmark,
        "matched": matched,
        "missing": missing,
        "section_analysis": section_analysis,
        "skill_counts": skill_counts,
        "job_skills": job_skills,
        "role_matches": role_matches,
        "career_path": career_path,
        "market_trends": market_trends,
        "dashboard_snapshot": dashboard_snapshot,
        "suggestions": gemini_result["suggestions"],
        "interpretation": gemini_result["interpretation"],
        "report": gemini_result["report"],
        "notice_type": "success",
        "notice_message": "Gemini-powered dynamic analysis is active for this run.",
        "uses_gemini": True,
    }


def _format_dataset_check(value):
    if value is None:
        return "N/A"

    return "Pass" if value else "Fail"


def render_dataset_evaluation(dataset_evaluation):
    st.subheader("Dataset Evaluation Results")
    st.caption("Research-style benchmarking results for multiple resume/job-description pairs from a CSV dataset.")

    summary = dataset_evaluation["summary"]
    results = dataset_evaluation["results"]
    strong_match_label = f"{summary['pairs_above_70']} ({summary['pairs_above_70_ratio']:.2f}%)"
    score_expectation_label = (
        f"{summary['score_expectation_passes']}/{summary['score_expectation_checks']} ({summary['score_expectation_pass_rate']:.2f}%)"
        if summary["score_expectation_pass_rate"] is not None
        else "N/A"
    )
    role_expectation_label = (
        f"{summary['role_expectation_passes']}/{summary['role_expectation_checks']} ({summary['role_expectation_pass_rate']:.2f}%)"
        if summary["role_expectation_pass_rate"] is not None
        else "N/A"
    )

    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    metric_col1.metric("Evaluated Pairs", summary["total_pairs"])
    metric_col2.metric("Average Score", f"{summary['average_score']:.2f}%")
    metric_col3.metric("Strong Matches", strong_match_label)
    metric_col4.metric("Score Checks", score_expectation_label)
    metric_col5.metric("Role Checks", role_expectation_label)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        pair_score_chart = go.Figure(
            go.Bar(
                x=[item["pair_name"] for item in results],
                y=[item["score"] for item in results],
                marker_color="#2563eb",
            )
        )
        pair_score_chart.update_layout(
            height=320,
            margin={"l": 20, "r": 20, "t": 40, "b": 20},
            title="Dataset Pair Scores",
            xaxis_title="Pairs",
            yaxis_title="ATS match score",
        )
        st.plotly_chart(pair_score_chart, use_container_width=True)

    with chart_col2:
        method_breakdown = summary.get("selected_method_breakdown", [])
        if method_breakdown:
            engine_chart = go.Figure(
                go.Bar(
                    x=[item["label"] for item in method_breakdown],
                    y=[item["count"] for item in method_breakdown],
                    marker_color="#7c3aed",
                )
            )
            engine_chart.update_layout(
                height=320,
                margin={"l": 20, "r": 20, "t": 40, "b": 20},
                title="Selected Engine Usage",
                xaxis_title="Engine",
                yaxis_title="Pairs",
            )
            st.plotly_chart(engine_chart, use_container_width=True)
        else:
            st.info("No engine-breakdown data is available yet.")

    st.caption(f"Average benchmark delta across the dataset: {summary['average_score_gap']:.2f}%")

    st.dataframe(
        [
            {
                "Pair": result["pair_name"],
                "Score": f"{result['score']:.2f}%",
                "Interpretation": result["interpretation"],
                "Engine": result["selected_method_label"],
                "Top Role": result["top_role"],
                "Role Score": f"{result['top_role_score']:.2f}%",
                "Matched Skills": result["matched_skill_count"],
                "Missing Skills": result["missing_skill_count"],
                "Score Gap": f"{result['score_gap']:.2f}%",
                "Score Check": _format_dataset_check(result["score_expectation_met"]),
                "Role Check": _format_dataset_check(result["role_expectation_met"]),
            }
            for result in results
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_sidebar(auth_user=None, cookie_manager=None):
    if auth_user:
        st.sidebar.header("Workspace")
        st.sidebar.caption("Review recent analyses, manage your session, and revisit saved work.")
        st.sidebar.success(f"Signed in as {auth_user['email']}")

        if st.sidebar.button("Log Out", use_container_width=True):
            _delete_session_cookie(cookie_manager)
            st.session_state.pop(AUTH_USER_SESSION_KEY, None)
            set_session_notice("info", "You have been signed out.")
            st.rerun()

        st.sidebar.markdown("---")
        render_recent_history(auth_user)
    else:
        st.sidebar.header("Account Access")
        st.sidebar.caption("Sign in with Firebase email/password authentication to use the analyzer.")

        if resolve_firebase_api_key(st.secrets):
            st.sidebar.success("Firebase authentication is configured.")
        else:
            st.sidebar.warning("Add FIREBASE_API_KEY to enable login.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Quick Tips")
    st.sidebar.markdown(
        "- Upload a text-based **PDF** or **DOCX** resume\n"
        "- Paste the full job description for better skill extraction\n"
        "- Download the result as **TXT**, **CSV**, or **PDF**"
    )


def render_auth_screen(cookie_manager=None):
    st.title("AI Career Intelligence & Job Market Analytics Platform")
    st.caption("Sign in or create a Firebase-backed account to access the analyzer workspace.")
    render_session_notice()

    firebase_api_key = resolve_firebase_api_key(st.secrets)

    if not firebase_api_key:
        st.error("Firebase email/password authentication is not configured yet.")
        st.markdown(
            "1. Enable **Email/Password** under Firebase Console → Authentication → Sign-in method.\n"
            "2. Add `FIREBASE_API_KEY` to your environment or `.streamlit/secrets.toml`.\n"
            "3. Restart the Streamlit app and sign in again."
        )
        return

    auth_col, help_col = st.columns([1.3, 0.9])

    with auth_col:
        sign_in_tab, sign_up_tab = st.tabs(["Sign In", "Create Account"])

        with sign_in_tab:
            with st.form("firebase_sign_in_form"):
                sign_in_email = st.text_input("Email", key="firebase_sign_in_email")
                sign_in_password = st.text_input("Password", type="password", key="firebase_sign_in_password")
                sign_in_clicked = st.form_submit_button("Sign In", use_container_width=True)

            if sign_in_clicked:
                if not sign_in_email.strip() or not sign_in_password:
                    st.warning("Please enter both your email and password.")
                else:
                    try:
                        auth_user = sign_in_with_email_password(
                            sign_in_email,
                            sign_in_password,
                            api_key=firebase_api_key,
                        )
                        st.session_state[AUTH_USER_SESSION_KEY] = auth_user
                    except FirebaseAuthError as error:
                        st.error(str(error))
                    else:
                        _save_session_cookie(cookie_manager, auth_user)
                        set_session_notice("success", "Signed in successfully.")
                        st.rerun()

        with sign_up_tab:
            with st.form("firebase_sign_up_form"):
                sign_up_email = st.text_input("Email", key="firebase_sign_up_email")
                sign_up_password = st.text_input("Password", type="password", key="firebase_sign_up_password")
                sign_up_confirm = st.text_input("Confirm Password", type="password", key="firebase_sign_up_confirm")
                sign_up_clicked = st.form_submit_button("Create Account", use_container_width=True)

            if sign_up_clicked:
                if not sign_up_email.strip() or not sign_up_password or not sign_up_confirm:
                    st.warning("Please complete the email, password, and confirm password fields.")
                elif sign_up_password != sign_up_confirm:
                    st.error("Passwords do not match.")
                elif len(sign_up_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    try:
                        auth_user = sign_up_with_email_password(
                            sign_up_email,
                            sign_up_password,
                            api_key=firebase_api_key,
                        )
                        st.session_state[AUTH_USER_SESSION_KEY] = auth_user
                    except FirebaseAuthError as error:
                        st.error(str(error))
                    else:
                        _save_session_cookie(cookie_manager, auth_user)
                        set_session_notice("success", "Account created successfully. You are now signed in.")
                        st.rerun()

    with help_col:
        st.subheader("Secure access")
        st.markdown(
            "- Separate email/password accounts for multiple users\n"
            "- Firebase-managed authentication flow\n"
            "- Per-user local analysis history in the sidebar\n"
            "- Password reset support from the login screen"
        )

        with st.expander("Forgot your password?"):
            with st.form("firebase_password_reset_form"):
                reset_email = st.text_input("Reset Email", key="firebase_reset_email")
                reset_clicked = st.form_submit_button("Send Reset Link", use_container_width=True)

            if reset_clicked:
                if not reset_email.strip():
                    st.warning("Please enter your email address to receive a reset link.")
                else:
                    try:
                        send_password_reset_email(reset_email, api_key=firebase_api_key)
                    except FirebaseAuthError as error:
                        st.error(str(error))
                    else:
                        st.success("If the account exists, Firebase will send a password reset email.")


def render_authenticated_app():
    st.title("AI Career Intelligence & Job Market Analytics Platform")
    st.caption(
        "Upload a resume, paste a job description, and get a quick ATS-style analysis "
        "with skills, suggestions, history, and downloadable reports."
    )
    render_session_notice()

    dataset_evaluate_clicked = False
    uploaded_dataset = None

    with st.form("analysis_form"):
        col1, col2 = st.columns([1, 1.2])

        with col1:
            uploaded_resume = st.file_uploader("Upload Resume", type=["pdf", "docx"])
            st.caption("Supported formats: PDF and DOCX")

        with col2:
            job_desc = st.text_area(
                "Paste Job Description",
                height=220,
                placeholder="Paste the full job description here for the best analysis.",
            )

        analyze_clicked = st.form_submit_button("Analyze Resume", use_container_width=True)

    st.subheader("Optional CSV Dataset Evaluation")
    show_dataset_evaluation = st.toggle(
        "Show CSV dataset evaluation",
        key="show_dataset_evaluation",
        help="Benchmark multiple resume/job-description pairs from a CSV file.",
    )

    if show_dataset_evaluation:
        st.caption(
            "Upload a CSV with required columns: "
            + ", ".join(REQUIRED_DATASET_COLUMNS)
            + ". Optional columns: pair_name, expected_min_score, expected_top_role."
        )

        with st.form("dataset_evaluation_form"):
            uploaded_dataset = st.file_uploader("Upload Evaluation CSV", type=["csv"], key="dataset_evaluation_csv")
            dataset_evaluate_clicked = st.form_submit_button("Run Dataset Evaluation", use_container_width=True)

    if analyze_clicked:
        if uploaded_resume is None or not job_desc.strip():
            st.warning("Please upload a resume and paste a job description.")
        else:
            try:
                resume_text = extract_text_from_resume(uploaded_resume)
            except ValueError as error:
                st.error(str(error))
                st.stop()
            except Exception:
                st.error("Could not read the uploaded resume. Please upload a valid PDF or DOCX file.")
                st.stop()

            if not resume_text.strip():
                st.warning("Could not extract any text from the uploaded resume.")
                st.stop()

            analysis_result = run_primary_analysis(resume_text, job_desc)
            score = analysis_result["score"]
            analysis_engine_label = analysis_result["analysis_engine_label"]
            similarity_benchmark = analysis_result["similarity_benchmark"]
            matched = analysis_result["matched"]
            missing = analysis_result["missing"]
            section_analysis = analysis_result["section_analysis"]
            skill_counts = analysis_result["skill_counts"]
            job_skills = analysis_result["job_skills"]
            role_matches = analysis_result["role_matches"]
            career_path = analysis_result["career_path"]
            market_trends = analysis_result["market_trends"]
            dashboard_snapshot = analysis_result["dashboard_snapshot"]
            suggestions = analysis_result["suggestions"]
            interpretation = analysis_result["interpretation"]
            report = analysis_result["report"]
            resume_name = uploaded_resume.name if getattr(uploaded_resume, "name", "") else "resume"
            auth_user = get_authenticated_user() or {}

            if analysis_result["notice_message"]:
                getattr(st, analysis_result["notice_type"])(analysis_result["notice_message"])

            try:
                _project_id = resolve_firebase_project_id(st.secrets)
                _user_id = auth_user.get("local_id", "")
                _id_token = auth_user.get("id_token", "")
                if _project_id and _user_id and _id_token:
                    save_analysis_firestore(
                        _user_id,
                        _id_token,
                        _project_id,
                        resume_name,
                        score,
                        interpretation,
                        matched,
                        missing,
                    )
                else:
                    save_analysis(
                        resume_name,
                        score,
                        interpretation,
                        matched,
                        missing,
                        user_email=auth_user.get("email", ""),
                    )
            except Exception:
                st.warning("Analysis completed, but history could not be saved.")

            st.divider()
            st.subheader("Analysis Summary")

            summary_col, score_col = st.columns([1, 1.4])

            with summary_col:
                st.metric("ATS Match Score", f"{score:.2f}%")

                metrics_col1, metrics_col2 = st.columns(2)
                metrics_col1.metric("Matched Skills", len(matched))
                metrics_col2.metric("Missing Skills", len(missing))

                st.write("Interpretation:", interpretation)
                st.caption(f"Analysis engine: {analysis_engine_label}")

            with score_col:
                gauge = go.Figure(
                    go.Indicator(
                        mode="gauge+number",
                        value=score,
                        title={"text": "ATS Match Score"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "steps": [
                                {"range": [0, 40], "color": "#f87171"},
                                {"range": [40, 70], "color": "#facc15"},
                                {"range": [70, 100], "color": "#4ade80"},
                            ],
                        },
                    )
                )
                gauge.update_layout(height=320, margin={"l": 20, "r": 20, "t": 60, "b": 20})
                st.plotly_chart(gauge, use_container_width=True)

            if analysis_result["uses_gemini"]:
                st.caption(
                    "The ATS score, skills, section analysis, role matching, career path, and market insights above "
                    "are Gemini-driven. The benchmark panel below remains a supplementary local comparison."
                )

            render_similarity_benchmark(similarity_benchmark)
            render_analytics_dashboard(dashboard_snapshot)
            render_section_analysis(section_analysis)
            render_role_matches(role_matches)
            render_career_path(career_path)
            render_market_trends(market_trends)

            skills_col, details_col = st.columns(2)

            with skills_col:
                render_status_list("Matched Skills", matched, st.success, "No matched skills were found.")
                render_status_list("Missing Skills", missing, st.error, "No missing skills were detected.")

            with details_col:
                st.subheader("Skill Occurrences in Resume")

                if skill_counts:
                    for skill, count in skill_counts.items():
                        st.write(f"{skill}: {count} time(s)")
                else:
                    st.info("No matched skills were counted in the resume text.")

                render_bullet_list(
                    "Top Skills Required in Job",
                    job_skills,
                    "No job-specific skills were detected from the description.",
                )

            suggestions_col, report_col = st.columns(2)

            with suggestions_col:
                render_bullet_list(
                    "Improvement Suggestions",
                    suggestions,
                    "No improvement suggestions were generated.",
                )

            with report_col:
                render_bullet_list(
                    "Resume Improvement Report",
                    report,
                    "No report items were generated.",
                )

            export_text = build_export_report(
                score,
                interpretation,
                matched,
                missing,
                skill_counts,
                job_skills,
                suggestions,
                report,
                analysis_engine_label,
                section_analysis["sections"],
                section_analysis["missing_sections"],
            )
            export_csv = build_csv_report(
                score,
                interpretation,
                analysis_engine_label,
                matched,
                missing,
                skill_counts,
                job_skills,
                suggestions,
                report,
                section_analysis["sections"],
                section_analysis["missing_sections"],
            )
            export_pdf = build_pdf_report(export_text)

            export_name = Path(resume_name).stem

            st.subheader("Download Reports")
            st.caption("Save this analysis as plain text, CSV, or PDF.")

            export_col1, export_col2, export_col3 = st.columns(3)

            with export_col1:
                st.download_button(
                    "Download TXT Report",
                    data=export_text,
                    file_name=f"{export_name}_analysis_report.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

            with export_col2:
                st.download_button(
                    "Download CSV Report",
                    data=export_csv,
                    file_name=f"{export_name}_analysis_report.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            with export_col3:
                st.download_button(
                    "Download PDF Report",
                    data=export_pdf,
                    file_name=f"{export_name}_analysis_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            st.subheader("Skill Match Overview")
            labels = ["Matched Skills", "Missing Skills"]
            values = [len(matched), len(missing)]

            fig2, ax = plt.subplots(figsize=(5, 3))
            ax.bar(labels, values, color=["#22c55e", "#ef4444"])
            ax.set_ylabel("Count")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            st.pyplot(fig2)
            plt.close(fig2)
    if dataset_evaluate_clicked:
        st.divider()

        if uploaded_dataset is None:
            st.warning("Please upload a CSV file for dataset evaluation.")
        else:
            try:
                dataset_csv_text = uploaded_dataset.getvalue().decode("utf-8-sig")
            except UnicodeDecodeError:
                st.error("Could not read the uploaded CSV file. Please upload a UTF-8 encoded CSV.")
                st.stop()

            try:
                dataset_evaluation = evaluate_dataset_csv_text(dataset_csv_text)
            except ValueError as error:
                st.error(str(error))
            else:
                render_dataset_evaluation(dataset_evaluation)
                dataset_export_text = build_dataset_evaluation_text_report(
                    dataset_evaluation["summary"],
                    dataset_evaluation["results"],
                )
                dataset_export_csv = build_dataset_evaluation_csv_report(
                    dataset_evaluation["summary"],
                    dataset_evaluation["results"],
                )
                dataset_export_pdf = build_pdf_report(dataset_export_text)
                dataset_export_name = Path(getattr(uploaded_dataset, "name", "dataset_evaluation.csv")).stem

                st.subheader("Download Dataset Reports")
                st.caption("Save the multi-pair evaluation as TXT, CSV, or PDF for your report/demo.")

                dataset_export_col1, dataset_export_col2, dataset_export_col3 = st.columns(3)

                with dataset_export_col1:
                    st.download_button(
                        "Download Dataset TXT",
                        data=dataset_export_text,
                        file_name=f"{dataset_export_name}_dataset_evaluation.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )

                with dataset_export_col2:
                    st.download_button(
                        "Download Dataset CSV",
                        data=dataset_export_csv,
                        file_name=f"{dataset_export_name}_dataset_evaluation.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                with dataset_export_col3:
                    st.download_button(
                        "Download Dataset PDF",
                        data=dataset_export_pdf,
                        file_name=f"{dataset_export_name}_dataset_evaluation.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
    elif not analyze_clicked:
        st.info(
            "Start by uploading a resume and pasting the target job description. "
            "After each run, you can review local history and download TXT, CSV, or PDF reports. "
            "You can also use the optional CSV dataset evaluation expander above for multi-pair benchmarking."
        )


st.set_page_config(page_title="AI Career Intelligence & Job Market Analytics Platform", layout="wide")
init_history_storage()



def main():
    # Render the cookie component first — it must appear unconditionally so
    # Streamlit's component bridge can mount it and send cookies back to Python.
    cookie_manager = _get_cookie_manager()

    # get_all() returns None on the very first render (the browser component
    # hasn't communicated back yet).  Stop here so Streamlit re-runs once the
    # component has loaded; on the second render get_all() returns a dict.
    all_cookies = cookie_manager.get_all()
    if all_cookies is None:
        st.stop()

    auth_user = get_authenticated_user()

    # If the session was wiped by a page refresh, try to silently restore it
    # from the refresh token stored in the browser cookie.
    if not auth_user:
        api_key = resolve_firebase_api_key(st.secrets)
        if api_key:
            cookie_value = all_cookies.get(FIREBASE_SESSION_COOKIE)
            restored = _try_restore_session(cookie_value, api_key)
            if restored:
                st.session_state[AUTH_USER_SESSION_KEY] = restored
                auth_user = restored

    render_sidebar(auth_user, cookie_manager)

    if not auth_user:
        render_auth_screen(cookie_manager)
        return

    render_authenticated_app()


main()