import re
from functools import lru_cache

from skills import count_skill_occurrences, extract_skills_from_text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_METHOD_LABELS = {
    "embeddings": "Embeddings (sentence-transformers)",
    "tfidf_baseline": "TF-IDF baseline",
    "tfidf_fallback": "TF-IDF fallback",
    "empty_input": "No content",
}
RESUME_SECTION_ALIASES = {
    "Summary": {
        "summary",
        "professional summary",
        "profile",
        "objective",
        "career objective",
    },
    "Skills": {
        "skills",
        "technical skills",
        "core skills",
        "key skills",
        "technical proficiencies",
        "technical stack",
        "tech stack",
    },
    "Experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "internship experience",
        "internships",
    },
    "Projects": {
        "projects",
        "project experience",
        "academic projects",
        "personal projects",
        "key projects",
    },
    "Education": {
        "education",
        "academic background",
        "qualifications",
    },
    "Certifications": {
        "certifications",
        "certificates",
        "licenses",
        "licenses and certifications",
    },
}
RESUME_SECTION_ORDER = list(RESUME_SECTION_ALIASES)


def _normalize_section_heading(line):
    normalized = re.sub(r"[^a-z0-9 ]+", " ", line.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _identify_resume_section(line):
    normalized = _normalize_section_heading(line)

    for section_name, aliases in RESUME_SECTION_ALIASES.items():
        if normalized in aliases:
            return section_name

    return None


def extract_resume_sections(resume_text):
    collected_sections = {}
    current_section = None
    preamble_lines = []

    for raw_line in resume_text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        section_name = _identify_resume_section(line)

        if section_name:
            current_section = section_name
            collected_sections.setdefault(section_name, [])
            continue

        if current_section:
            collected_sections[current_section].append(line)
        else:
            preamble_lines.append(line)

    sections = {}

    for section_name in RESUME_SECTION_ORDER:
        section_text = "\n".join(collected_sections.get(section_name, [])).strip()

        if section_text:
            sections[section_name] = section_text

    if sections:
        return sections

    general_text = "\n".join(preamble_lines).strip() or resume_text.strip()

    return {"General": general_text} if general_text else {}


def analyze_resume_sections(resume_text, job_desc):
    sections = extract_resume_sections(resume_text)
    job_skills = extract_skills_from_text(job_desc)
    section_results = []

    for section_name, section_text in sections.items():
        similarity = calculate_similarity_details(section_text, job_desc)
        detected_skills = extract_skills_from_text(section_text)
        detected_skill_set = set(detected_skills)
        matched_skills = [skill for skill in job_skills if skill in detected_skill_set]

        section_results.append(
            {
                "name": section_name,
                "score": similarity["score"],
                "method": similarity["method"],
                "matched_skills": matched_skills,
                "detected_skills": detected_skills,
            }
        )

    if "General" in sections:
        missing_sections = RESUME_SECTION_ORDER.copy()
    else:
        missing_sections = [section_name for section_name in RESUME_SECTION_ORDER if section_name not in sections]

    return {
        "sections": section_results,
        "missing_sections": missing_sections,
    }


@lru_cache(maxsize=1)
def _get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def _calculate_tfidf_similarity(resume, job_desc):
    documents = [resume, job_desc]
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(documents)
    similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0] * 100

    return round(similarity, 2)


def _calculate_embedding_similarity(resume, job_desc):
    from sentence_transformers import util

    model = _get_embedding_model()
    embeddings = model.encode([resume, job_desc], convert_to_tensor=True)
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
    normalized_similarity = max(0.0, min(1.0, (similarity + 1) / 2))

    return round(normalized_similarity * 100, 2)


def benchmark_similarity_methods(resume, job_desc):
    benchmark_methods = [
        {
            "method": "embeddings",
            "label": describe_similarity_method("embeddings"),
            "score": None,
            "available": False,
        },
        {
            "method": "tfidf_baseline",
            "label": describe_similarity_method("tfidf_baseline"),
            "score": None,
            "available": False,
        },
    ]

    if not resume.strip() or not job_desc.strip():
        return {
            "selected_score": 0.0,
            "selected_method": "empty_input",
            "selected_method_label": describe_similarity_method("empty_input"),
            "methods": benchmark_methods,
            "score_gap": 0.0,
            "benchmark_note": "No benchmark comparison is available because one or both inputs are empty.",
        }

    tfidf_score = _calculate_tfidf_similarity(resume, job_desc)
    benchmark_methods[1]["score"] = tfidf_score
    benchmark_methods[1]["available"] = True

    try:
        embedding_score = _calculate_embedding_similarity(resume, job_desc)
        benchmark_methods[0]["score"] = embedding_score
        benchmark_methods[0]["available"] = True

        return {
            "selected_score": embedding_score,
            "selected_method": "embeddings",
            "selected_method_label": describe_similarity_method("embeddings"),
            "methods": benchmark_methods,
            "score_gap": round(abs(embedding_score - tfidf_score), 2),
            "benchmark_note": "Embeddings are available, so the semantic score is used as the primary analysis engine.",
        }
    except Exception:
        return {
            "selected_score": tfidf_score,
            "selected_method": "tfidf_fallback",
            "selected_method_label": describe_similarity_method("tfidf_fallback"),
            "methods": benchmark_methods,
            "score_gap": 0.0,
            "benchmark_note": "Embeddings were unavailable for this run, so the app used the TF-IDF fallback score.",
        }


def calculate_similarity_details(resume, job_desc):
    if not resume.strip() or not job_desc.strip():
        return {"score": 0.0, "method": "empty_input"}

    try:
        return {
            "score": _calculate_embedding_similarity(resume, job_desc),
            "method": "embeddings",
        }
    except Exception:
        return {
            "score": _calculate_tfidf_similarity(resume, job_desc),
            "method": "tfidf_fallback",
        }


def calculate_similarity(resume, job_desc):
    return calculate_similarity_details(resume, job_desc)["score"]


def describe_similarity_method(method):
    return SIMILARITY_METHOD_LABELS.get(method, method.replace("_", " ").title())


def skill_analysis(resume, job_desc):

    job_skills = extract_skills_from_text(job_desc)
    resume_skills = set(extract_skills_from_text(resume))

    matched = [skill for skill in job_skills if skill in resume_skills]
    missing = [skill for skill in job_skills if skill not in resume_skills]

    return matched, missing


def highlight_skills(resume, matched_skills):
    return count_skill_occurrences(resume, matched_skills)