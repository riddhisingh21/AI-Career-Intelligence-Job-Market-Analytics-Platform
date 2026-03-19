import re


skills_list = [
    "python",
    "java",
    "sql",
    "aws",
    "machine learning",
    "deep learning",
    "nlp",
    "data analysis",
    "react",
    "django",
    "tensorflow",
    "pandas",
    "numpy",
]

SKILL_CATEGORY_KEYWORDS = {
    "Programming": {
        "python",
        "java",
        "javascript",
        "typescript",
        "c++",
        "c#",
    },
    "Databases": {
        "sql",
        "mysql",
        "postgresql",
        "postgres",
        "mongodb",
        "database",
    },
    "Data & AI": {
        "machine learning",
        "deep learning",
        "nlp",
        "data analysis",
        "pandas",
        "numpy",
        "tensorflow",
        "pytorch",
        "statistics",
    },
    "Web Development": {
        "django",
        "flask",
        "fastapi",
        "react",
        "angular",
        "vue",
        "frontend",
        "backend",
        "full stack",
        "api",
    },
    "Cloud & DevOps": {
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "linux",
        "terraform",
        "jenkins",
        "cloud",
        "devops",
        "ci/cd",
    },
}

SKILL_CUE_PATTERNS = [
    r"(?:experience|expertise|knowledge|proficient|proficiency|skilled|familiarity)\s+(?:with|in)\s+([^\n;:]+)",
    r"(?:skills|technologies|tools|stack|requirements?)\s*[:\-]\s*([^\n;]+)",
]

GENERIC_SKILL_TERMS = {
    "ability",
    "analysis",
    "analytical",
    "bachelor",
    "bachelors",
    "communication",
    "computer science",
    "degree",
    "development",
    "engineering",
    "experience",
    "good",
    "hands on",
    "hands-on",
    "knowledge",
    "preferred",
    "problem solving",
    "required",
    "requirements",
    "responsibilities",
    "role",
    "science",
    "skills",
    "strong",
    "team",
    "work",
    "working",
    "years",
}

SEPARATOR_PATTERN = re.compile(r",|;|\||\band\b|(?<=\s)/(?=\s)", re.IGNORECASE)
SPECIAL_SKILL_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z0-9.+#/-]*[+#/.-][a-zA-Z0-9.+#/-]*\b")


def normalize_skill(skill):
    skill = skill.strip().lower()
    skill = re.sub(r"\s+", " ", skill)
    return skill.strip(" .,:;|-")


def _looks_like_skill(candidate):
    candidate = normalize_skill(candidate)

    if not candidate or candidate in GENERIC_SKILL_TERMS:
        return False

    words = candidate.split()

    if len(words) > 4:
        return False

    if all(word in GENERIC_SKILL_TERMS for word in words):
        return False

    if len(candidate) < 2:
        return False

    return True


def _extract_candidates(fragment):
    fragment = fragment.replace("•", " ")
    parts = SEPARATOR_PATTERN.split(fragment)
    candidates = []

    for part in parts:
        candidate = normalize_skill(part.split(":")[-1])

        if candidate.startswith("using "):
            candidate = candidate.removeprefix("using ")

        if candidate.startswith("with "):
            candidate = candidate.removeprefix("with ")

        if candidate.startswith("in "):
            candidate = candidate.removeprefix("in ")

        if _looks_like_skill(candidate):
            candidates.append(candidate)

    return candidates


def extract_skills_from_text(text):
    normalized_text = text.lower()
    detected_skills = {skill for skill in skills_list if skill in normalized_text}

    for pattern in SKILL_CUE_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            detected_skills.update(_extract_candidates(match.group(1)))

    for line in text.splitlines():
        stripped_line = line.strip(" -*\t")

        if not stripped_line:
            continue

        if any(separator in stripped_line for separator in [",", ";", "|", " / "]):
            detected_skills.update(_extract_candidates(stripped_line))

    for match in SPECIAL_SKILL_PATTERN.findall(text):
        candidate = normalize_skill(match)

        if _looks_like_skill(candidate):
            detected_skills.add(candidate)

    return sorted(detected_skills)


def categorize_skill(skill):
    normalized_skill = normalize_skill(skill)

    for category, keywords in SKILL_CATEGORY_KEYWORDS.items():
        if normalized_skill in keywords:
            return category

    for category, keywords in SKILL_CATEGORY_KEYWORDS.items():
        if any(keyword in normalized_skill or normalized_skill in keyword for keyword in keywords):
            return category

    return "Other / Specialized"


def group_skills_by_category(skills):
    grouped_skills = {}

    for skill in skills:
        category = categorize_skill(skill)
        grouped_skills.setdefault(category, set()).add(skill)

    return {
        category: sorted(values)
        for category, values in sorted(grouped_skills.items(), key=lambda item: item[0])
    }


def count_skill_occurrences(text, skills):
    normalized_text = text.lower()
    occurrences = {}

    for skill in skills:
        pattern = rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])"
        occurrences[skill] = len(re.findall(pattern, normalized_text))

    return occurrences