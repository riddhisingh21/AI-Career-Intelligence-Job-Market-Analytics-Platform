import json
import os

from skills import normalize_skill
from suggestions import interpret_score


DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "number"},
        "interpretation": {"type": "string"},
        "matched_skills": {"type": "array", "items": {"type": "string"}},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "job_skills": {"type": "array", "items": {"type": "string"}},
        "section_analysis": {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "score": {"type": "number"},
                            "matched_skills": {"type": "array", "items": {"type": "string"}},
                            "detected_skills": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "missing_sections": {"type": "array", "items": {"type": "string"}},
            },
        },
        "role_matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "focus_area": {"type": "string"},
                    "summary": {"type": "string"},
                    "score": {"type": "number"},
                    "matched_skills": {"type": "array", "items": {"type": "string"}},
                    "missing_skills": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "career_path": {
            "type": "object",
            "properties": {
                "current_role": {"type": "string"},
                "current_role_score": {"type": "number"},
                "priority_skills": {"type": "array", "items": {"type": "string"}},
                "next_steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "summary": {"type": "string"},
                            "readiness_score": {"type": "number"},
                            "matched_skills": {"type": "array", "items": {"type": "string"}},
                            "missing_skills": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        },
        "market_trends": {
            "type": "object",
            "properties": {
                "market_readiness_score": {"type": "number"},
                "top_trending_skills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "skill": {"type": "string"},
                            "demand_score": {"type": "number"},
                            "in_resume": {"type": "boolean"},
                            "in_job_desc": {"type": "boolean"},
                        },
                    },
                },
                "matched_trending_skills": {"type": "array", "items": {"type": "string"}},
                "missing_trending_skills": {"type": "array", "items": {"type": "string"}},
                "job_aligned_trending_skills": {"type": "array", "items": {"type": "string"}},
                "target_roles": {"type": "array", "items": {"type": "string"}},
            },
        },
        "suggestions": {"type": "array", "items": {"type": "string"}},
        "report": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overall_score",
        "interpretation",
        "matched_skills",
        "missing_skills",
        "job_skills",
        "section_analysis",
        "role_matches",
        "career_path",
        "market_trends",
        "suggestions",
        "report",
    ],
}


class GeminiAnalysisError(RuntimeError):
    pass


def _get_mapping_value(mapping, *keys):
    current = mapping

    for key in keys:
        if current is None:
            return None

        try:
            current = current.get(key)
        except AttributeError:
            try:
                current = current[key]
            except Exception:
                return None
        except Exception:
            return None

    return current


def resolve_gemini_api_key(secrets=None):
    env_value = os.getenv("GEMINI_API_KEY", "").strip()

    if env_value:
        return env_value

    for candidate in (
        _get_mapping_value(secrets, "GEMINI_API_KEY"),
        _get_mapping_value(secrets, "gemini", "api_key"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    return None


def resolve_gemini_model(secrets=None):
    env_value = os.getenv("GEMINI_MODEL", "").strip()

    if env_value:
        return env_value

    for candidate in (
        _get_mapping_value(secrets, "GEMINI_MODEL"),
        _get_mapping_value(secrets, "gemini", "model"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    return DEFAULT_GEMINI_MODEL


def _build_gemini_client(api_key):
    try:
        from google import genai
        from google.genai import types
    except ImportError as error:
        raise GeminiAnalysisError(
            "google-genai is not installed. Install dependencies before using Gemini analysis."
        ) from error

    return genai.Client(api_key=api_key), types


def _clamp_score(value, default=0.0):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        numeric_value = float(default)

    return round(max(0.0, min(100.0, numeric_value)), 2)


def _unique_strings(values, normalizer):
    normalized_values = []
    seen = set()

    for value in values or []:
        normalized_value = normalizer(value)

        if not normalized_value:
            continue

        identity = normalized_value.casefold()

        if identity in seen:
            continue

        seen.add(identity)
        normalized_values.append(normalized_value)

    return normalized_values


def _normalize_skill_list(values):
    return _unique_strings(values, lambda value: normalize_skill(str(value)))


def _normalize_text_list(values):
    return _unique_strings(values, lambda value: str(value).strip())


def _coerce_mapping(value):
    if isinstance(value, dict):
        return value

    if value is None:
        return None

    for method_name in ("model_dump", "dict", "to_dict"):
        method = getattr(value, method_name, None)

        if not callable(method):
            continue

        try:
            dumped = method()
        except TypeError:
            try:
                dumped = method(mode="json")
            except Exception:
                continue
        except Exception:
            continue

        if isinstance(dumped, dict):
            return dumped

    return None


def _strip_json_fences(text):
    cleaned = (text or "").strip()

    if cleaned.startswith("```"):
        cleaned = cleaned[3:]

        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]

        cleaned = cleaned.strip()

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    return cleaned


def _iterable_items(value):
    return value if isinstance(value, (list, tuple)) else []


def _iter_response_text_candidates(response):
    seen = set()

    def add_text(value):
        if not isinstance(value, str):
            return

        cleaned = value.strip()

        if not cleaned or cleaned in seen:
            return

        seen.add(cleaned)
        yield cleaned

    try:
        yield from add_text(getattr(response, "text", None))
    except Exception:
        pass

    for part in _iterable_items(getattr(response, "parts", None)):
        try:
            yield from add_text(getattr(part, "text", None))
        except Exception:
            continue

    for candidate in _iterable_items(getattr(response, "candidates", None)):
        content = getattr(candidate, "content", None)

        for part in _iterable_items(getattr(content, "parts", None)):
            try:
                yield from add_text(getattr(part, "text", None))
            except Exception:
                continue


def _try_parse_json_text(text):
    decoder = json.JSONDecoder()

    for candidate_text in (text, _strip_json_fences(text)):
        if not candidate_text:
            continue

        try:
            parsed = json.loads(candidate_text)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, dict):
            return parsed

        for index, character in enumerate(candidate_text):
            if character not in "[{":
                continue

            try:
                parsed, _ = decoder.raw_decode(candidate_text[index:])
            except json.JSONDecodeError:
                continue

            if isinstance(parsed, dict):
                return parsed

    return None


def _extract_json_payload(response):
    parsed = _coerce_mapping(getattr(response, "parsed", None))

    if isinstance(parsed, dict):
        return parsed

    text_candidates = list(_iter_response_text_candidates(response))

    if not text_candidates:
        raise GeminiAnalysisError("Gemini returned an empty response.")

    for response_text in text_candidates:
        payload = _try_parse_json_text(response_text)

        if isinstance(payload, dict):
            return payload

    raise GeminiAnalysisError("Gemini returned invalid JSON.")


def _normalize_section_analysis(section_analysis, overall_score):
    raw_analysis = section_analysis or {}
    normalized_sections = []

    for item in raw_analysis.get("sections") or []:
        section_name = str(item.get("name", "")).strip() or "General"
        matched_skills = _normalize_skill_list(item.get("matched_skills"))
        detected_skills = _normalize_skill_list(item.get("detected_skills")) or matched_skills
        normalized_sections.append(
            {
                "name": section_name,
                "score": _clamp_score(item.get("score"), default=overall_score),
                "method": "gemini_structured",
                "matched_skills": matched_skills,
                "detected_skills": detected_skills,
            }
        )

    if not normalized_sections:
        normalized_sections = [
            {
                "name": "General",
                "score": overall_score,
                "method": "gemini_structured",
                "matched_skills": [],
                "detected_skills": [],
            }
        ]

    return {
        "sections": normalized_sections,
        "missing_sections": _normalize_text_list(raw_analysis.get("missing_sections")),
    }


def _normalize_role_matches(role_matches):
    normalized_matches = []
    seen = set()

    for item in role_matches or []:
        role_name = str(item.get("name", "")).strip()

        if not role_name or role_name.casefold() in seen:
            continue

        seen.add(role_name.casefold())
        normalized_matches.append(
            {
                "name": role_name,
                "focus_area": str(item.get("focus_area", "General alignment")).strip() or "General alignment",
                "summary": str(item.get("summary", "")).strip() or "No summary available.",
                "score": _clamp_score(item.get("score")),
                "matched_skills": _normalize_skill_list(item.get("matched_skills")),
                "missing_skills": _normalize_skill_list(item.get("missing_skills")),
            }
        )

    return normalized_matches[:3]


def _normalize_career_path(career_path, role_matches):
    raw_path = career_path or {}
    top_role = role_matches[0] if role_matches else None
    next_steps = []
    seen = set()

    for item in raw_path.get("next_steps") or []:
        step_name = str(item.get("name", "")).strip()

        if not step_name or step_name.casefold() in seen:
            continue

        seen.add(step_name.casefold())
        next_steps.append(
            {
                "name": step_name,
                "summary": str(item.get("summary", "")).strip() or "No summary available.",
                "readiness_score": _clamp_score(item.get("readiness_score")),
                "matched_skills": _normalize_skill_list(item.get("matched_skills")),
                "missing_skills": _normalize_skill_list(item.get("missing_skills")),
            }
        )

    priority_skills = _normalize_skill_list(raw_path.get("priority_skills"))

    if not priority_skills:
        priority_skills = _unique_strings(
            [skill for step in next_steps for skill in step["missing_skills"]],
            lambda value: str(value).strip(),
        )

    return {
        "current_role": str(raw_path.get("current_role", "")).strip() or (top_role["name"] if top_role else None),
        "current_role_score": _clamp_score(
            raw_path.get("current_role_score"),
            default=top_role["score"] if top_role else 0.0,
        ),
        "priority_skills": priority_skills[:5],
        "next_steps": next_steps[:3],
    }


def _normalize_market_trends(market_trends, job_skills, role_matches):
    raw_trends = market_trends or {}
    job_skill_set = set(job_skills)
    top_trending_skills = []
    seen = set()

    for item in raw_trends.get("top_trending_skills") or []:
        skill = normalize_skill(str(item.get("skill", "")))

        if not skill or skill in seen:
            continue

        seen.add(skill)
        top_trending_skills.append(
            {
                "skill": skill,
                "demand_score": _clamp_score(item.get("demand_score"), default=0.0),
                "in_resume": bool(item.get("in_resume")),
                "in_job_desc": bool(item.get("in_job_desc", skill in job_skill_set)),
            }
        )

    matched_trending_skills = _normalize_skill_list(raw_trends.get("matched_trending_skills"))
    missing_trending_skills = _normalize_skill_list(raw_trends.get("missing_trending_skills"))
    job_aligned_trending_skills = _normalize_skill_list(raw_trends.get("job_aligned_trending_skills"))

    if top_trending_skills:
        if not matched_trending_skills:
            matched_trending_skills = [item["skill"] for item in top_trending_skills if item["in_resume"]]
        if not missing_trending_skills:
            missing_trending_skills = [item["skill"] for item in top_trending_skills if not item["in_resume"]]
        if not job_aligned_trending_skills:
            job_aligned_trending_skills = [item["skill"] for item in top_trending_skills if item["in_job_desc"]]

    target_roles = _normalize_text_list(raw_trends.get("target_roles")) or [role["name"] for role in role_matches]
    default_market_score = (
        round((len(matched_trending_skills) / len(top_trending_skills)) * 100, 2)
        if top_trending_skills
        else 0.0
    )

    return {
        "market_readiness_score": _clamp_score(
            raw_trends.get("market_readiness_score"),
            default=default_market_score,
        ),
        "top_trending_skills": top_trending_skills[:6],
        "matched_trending_skills": matched_trending_skills,
        "missing_trending_skills": missing_trending_skills,
        "job_aligned_trending_skills": job_aligned_trending_skills,
        "target_roles": target_roles,
    }


def _normalize_analysis_payload(payload, model):
    overall_score = _clamp_score(payload.get("overall_score"))
    matched_skills = _normalize_skill_list(payload.get("matched_skills"))
    missing_skills = _normalize_skill_list(payload.get("missing_skills"))
    job_skills = _normalize_skill_list(payload.get("job_skills")) or _normalize_skill_list(matched_skills + missing_skills)
    role_matches = _normalize_role_matches(payload.get("role_matches"))
    career_path = _normalize_career_path(payload.get("career_path"), role_matches)

    if not role_matches and career_path["current_role"]:
        role_matches = [
            {
                "name": career_path["current_role"],
                "focus_area": "Primary fit",
                "summary": payload.get("interpretation") or "Best-fit role inferred from Gemini analysis.",
                "score": career_path["current_role_score"],
                "matched_skills": matched_skills[:6],
                "missing_skills": missing_skills[:6],
            }
        ]

    return {
        "overall_score": overall_score,
        "interpretation": str(payload.get("interpretation", "")).strip() or interpret_score(overall_score),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "job_skills": job_skills,
        "section_analysis": _normalize_section_analysis(payload.get("section_analysis"), overall_score),
        "role_matches": role_matches,
        "career_path": career_path,
        "market_trends": _normalize_market_trends(payload.get("market_trends"), job_skills, role_matches),
        "suggestions": _normalize_text_list(payload.get("suggestions"))[:6],
        "report": _normalize_text_list(payload.get("report"))[:8],
        "analysis_engine_label": f"Gemini ({model})",
        "analysis_engine_model": model,
    }


def _build_prompt(resume_text, job_desc):
    return (
        "Analyze the uploaded resume against the target job description and return only JSON.\n"
        "Use only evidence from the provided texts.\n"
        "Make the output dynamic, specific, and concise.\n"
        "Constraints:\n"
        "- all scores must be from 0 to 100\n"
        "- skill phrases must be lowercase and concise\n"
        "- return up to 3 role_matches, up to 3 career_path.next_steps, and up to 6 market_trends.top_trending_skills\n"
        "- suggestions and report should be actionable bullet-style strings\n\n"
        f"Resume:\n{resume_text}\n\n"
        f"Job Description:\n{job_desc}"
    )


def analyze_resume_with_gemini(resume_text, job_desc, api_key=None, model=None, secrets=None):
    resolved_api_key = api_key or resolve_gemini_api_key(secrets)

    if not resolved_api_key:
        raise GeminiAnalysisError("GEMINI_API_KEY is not configured.")

    resolved_model = model or resolve_gemini_model(secrets)
    client, types = _build_gemini_client(resolved_api_key)

    try:
        response = client.models.generate_content(
            model=resolved_model,
            contents=_build_prompt(resume_text, job_desc),
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are an expert ATS resume reviewer and career strategist. "
                    "Return valid JSON only and keep every field grounded in the provided resume and job description."
                ),
                temperature=0.2,
                max_output_tokens=4096,
                response_mime_type="application/json",
                response_json_schema=GEMINI_ANALYSIS_SCHEMA,
            ),
        )
    except Exception as error:
        raise GeminiAnalysisError(f"Gemini request failed: {error}") from error

    return _normalize_analysis_payload(_extract_json_payload(response), resolved_model)