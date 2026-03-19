import csv
import io

from analyzer import benchmark_similarity_methods, skill_analysis
from market_analysis import recommend_job_roles
from suggestions import interpret_score


REQUIRED_DATASET_COLUMNS = ("resume_text", "job_description")


def _normalize_column_name(value):
    return (value or "").strip().lower()


def _parse_optional_float(value, field_name, row_number):
    cleaned_value = (value or "").strip()

    if not cleaned_value:
        return None

    try:
        return float(cleaned_value)
    except ValueError as error:
        raise ValueError(
            f"Row {row_number} has an invalid numeric value for {field_name}: {cleaned_value}"
        ) from error


def load_dataset_rows(csv_text):
    reader = csv.DictReader(io.StringIO(csv_text))
    fieldnames = [_normalize_column_name(field) for field in (reader.fieldnames or [])]
    missing_columns = [column for column in REQUIRED_DATASET_COLUMNS if column not in fieldnames]

    if missing_columns:
        raise ValueError(
            "Dataset CSV is missing required columns: " + ", ".join(sorted(missing_columns))
        )

    rows = []

    for row_number, raw_row in enumerate(reader, start=1):
        normalized_row = {
            _normalize_column_name(key): (value or "")
            for key, value in raw_row.items()
            if key is not None
        }
        resume_text = normalized_row.get("resume_text", "").strip()
        job_description = normalized_row.get("job_description", "").strip()

        if not resume_text or not job_description:
            raise ValueError(
                f"Row {row_number} must include non-empty values for resume_text and job_description."
            )

        rows.append(
            {
                "pair_name": normalized_row.get("pair_name", "").strip() or f"Pair {row_number}",
                "resume_text": resume_text,
                "job_description": job_description,
                "expected_min_score": _parse_optional_float(
                    normalized_row.get("expected_min_score", ""),
                    "expected_min_score",
                    row_number,
                ),
                "expected_top_role": normalized_row.get("expected_top_role", "").strip(),
            }
        )

    if not rows:
        raise ValueError("Dataset CSV does not contain any evaluation rows.")

    return rows


def _rate(numerator, denominator):
    return round((numerator / denominator) * 100, 2) if denominator else None


def evaluate_dataset_rows(rows):
    results = []
    selected_method_counts = {}
    score_expectation_passes = 0
    score_expectation_checks = 0
    role_expectation_passes = 0
    role_expectation_checks = 0

    for row in rows:
        similarity_benchmark = benchmark_similarity_methods(
            row["resume_text"],
            row["job_description"],
        )
        score = similarity_benchmark["selected_score"]
        matched, missing = skill_analysis(row["resume_text"], row["job_description"])
        role_matches = recommend_job_roles(row["resume_text"])
        top_role = role_matches[0] if role_matches else None
        expected_min_score = row["expected_min_score"]
        expected_top_role = row["expected_top_role"]

        score_expectation_met = None
        if expected_min_score is not None:
            score_expectation_checks += 1
            score_expectation_met = score >= expected_min_score
            if score_expectation_met:
                score_expectation_passes += 1

        role_expectation_met = None
        if expected_top_role:
            role_expectation_checks += 1
            role_expectation_met = bool(top_role) and top_role["name"].casefold() == expected_top_role.casefold()
            if role_expectation_met:
                role_expectation_passes += 1

        selected_method_label = similarity_benchmark["selected_method_label"]
        selected_method_counts[selected_method_label] = selected_method_counts.get(selected_method_label, 0) + 1

        results.append(
            {
                "pair_name": row["pair_name"],
                "score": round(score, 2),
                "interpretation": interpret_score(score),
                "selected_method": similarity_benchmark["selected_method"],
                "selected_method_label": selected_method_label,
                "score_gap": round(similarity_benchmark["score_gap"], 2),
                "top_role": top_role["name"] if top_role else "Not available",
                "top_role_score": top_role["score"] if top_role else 0.0,
                "matched_skill_count": len(matched),
                "missing_skill_count": len(missing),
                "matched_skills": matched,
                "missing_skills": missing,
                "expected_min_score": expected_min_score,
                "expected_top_role": expected_top_role,
                "score_expectation_met": score_expectation_met,
                "role_expectation_met": role_expectation_met,
            }
        )

    total_pairs = len(results)
    strong_matches = sum(result["score"] >= 70.0 for result in results)
    average_score = round(sum(result["score"] for result in results) / total_pairs, 2) if results else 0.0
    average_score_gap = round(sum(result["score_gap"] for result in results) / total_pairs, 2) if results else 0.0
    average_matched_skill_count = (
        round(sum(result["matched_skill_count"] for result in results) / total_pairs, 2) if results else 0.0
    )

    return {
        "summary": {
            "total_pairs": total_pairs,
            "average_score": average_score,
            "average_score_gap": average_score_gap,
            "average_matched_skill_count": average_matched_skill_count,
            "pairs_above_70": strong_matches,
            "pairs_above_70_ratio": _rate(strong_matches, total_pairs) or 0.0,
            "score_expectation_checks": score_expectation_checks,
            "score_expectation_passes": score_expectation_passes,
            "score_expectation_pass_rate": _rate(score_expectation_passes, score_expectation_checks),
            "role_expectation_checks": role_expectation_checks,
            "role_expectation_passes": role_expectation_passes,
            "role_expectation_pass_rate": _rate(role_expectation_passes, role_expectation_checks),
            "selected_method_breakdown": [
                {"label": label, "count": count}
                for label, count in sorted(
                    selected_method_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
        },
        "results": results,
    }


def evaluate_dataset_csv_text(csv_text):
    return evaluate_dataset_rows(load_dataset_rows(csv_text))