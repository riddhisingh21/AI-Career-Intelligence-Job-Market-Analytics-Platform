import csv
import io

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure


def build_csv_report(
    score,
    interpretation,
    similarity_method_label,
    matched_skills,
    missing_skills,
    skill_counts,
    job_skills,
    suggestions,
    report,
    section_analysis=None,
    missing_sections=None,
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "item", "value"])
    writer.writerow(["summary", "ats_match_score", score])
    writer.writerow(["summary", "interpretation", interpretation])
    writer.writerow(["summary", "similarity_engine", similarity_method_label])

    for skill in matched_skills or ["None"]:
        writer.writerow(["matched_skills", skill, "matched"])

    for skill in missing_skills or ["None"]:
        writer.writerow(["missing_skills", skill, "missing"])

    for skill in job_skills or ["None"]:
        writer.writerow(["job_skills", skill, "required"])

    for section in section_analysis or []:
        writer.writerow(["section_analysis", section["name"], section["score"]])
        writer.writerow(
            [
                "section_matched_skills",
                section["name"],
                "; ".join(section["matched_skills"]) or "None",
            ]
        )

    for section_name in missing_sections or []:
        writer.writerow(["missing_resume_sections", section_name, "not_detected"])

    if skill_counts:
        for skill, count in skill_counts.items():
            writer.writerow(["skill_occurrences", skill, count])
    else:
        writer.writerow(["skill_occurrences", "None", 0])

    for item in suggestions or ["None"]:
        writer.writerow(["suggestions", item, ""])

    for item in report or ["None"]:
        writer.writerow(["improvement_report", item, ""])

    return output.getvalue()


def _format_expectation_value(value):
    if value is None:
        return "N/A"

    return "pass" if value else "fail"


def build_dataset_evaluation_csv_report(summary, results):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "item", "value"])
    writer.writerow(["summary", "total_pairs", summary["total_pairs"]])
    writer.writerow(["summary", "average_score", summary["average_score"]])
    writer.writerow(["summary", "average_score_gap", summary["average_score_gap"]])
    writer.writerow(["summary", "average_matched_skill_count", summary["average_matched_skill_count"]])
    writer.writerow(["summary", "pairs_above_70", summary["pairs_above_70"]])
    writer.writerow(["summary", "pairs_above_70_ratio", summary["pairs_above_70_ratio"]])
    writer.writerow(["summary", "score_expectation_checks", summary["score_expectation_checks"]])
    writer.writerow(["summary", "score_expectation_passes", summary["score_expectation_passes"]])
    writer.writerow(
        [
            "summary",
            "score_expectation_pass_rate",
            summary["score_expectation_pass_rate"] if summary["score_expectation_pass_rate"] is not None else "N/A",
        ]
    )
    writer.writerow(["summary", "role_expectation_checks", summary["role_expectation_checks"]])
    writer.writerow(["summary", "role_expectation_passes", summary["role_expectation_passes"]])
    writer.writerow(
        [
            "summary",
            "role_expectation_pass_rate",
            summary["role_expectation_pass_rate"] if summary["role_expectation_pass_rate"] is not None else "N/A",
        ]
    )

    for method in summary.get("selected_method_breakdown", []):
        writer.writerow(["selected_method_breakdown", method["label"], method["count"]])

    writer.writerow([])
    writer.writerow(
        [
            "pair_name",
            "score",
            "interpretation",
            "selected_method",
            "score_gap",
            "top_role",
            "top_role_score",
            "matched_skill_count",
            "missing_skill_count",
            "expected_min_score",
            "score_expectation_met",
            "expected_top_role",
            "role_expectation_met",
        ]
    )

    for result in results:
        writer.writerow(
            [
                result["pair_name"],
                result["score"],
                result["interpretation"],
                result["selected_method_label"],
                result["score_gap"],
                result["top_role"],
                result["top_role_score"],
                result["matched_skill_count"],
                result["missing_skill_count"],
                result["expected_min_score"] if result["expected_min_score"] is not None else "N/A",
                _format_expectation_value(result["score_expectation_met"]),
                result["expected_top_role"] or "N/A",
                _format_expectation_value(result["role_expectation_met"]),
            ]
        )

    return output.getvalue()


def build_dataset_evaluation_text_report(summary, results):
    lines = [
        "Dataset Evaluation Report",
        "=" * 25,
        f"Total pairs: {summary['total_pairs']}",
        f"Average ATS match score: {summary['average_score']:.2f}%",
        f"Average benchmark delta: {summary['average_score_gap']:.2f}%",
        f"Average matched skills: {summary['average_matched_skill_count']:.2f}",
        f"Pairs scoring at least 70%: {summary['pairs_above_70']} ({summary['pairs_above_70_ratio']:.2f}%)",
    ]

    if summary["score_expectation_checks"]:
        lines.append(
            "Score expectation pass rate: "
            f"{summary['score_expectation_passes']}/{summary['score_expectation_checks']} "
            f"({summary['score_expectation_pass_rate']:.2f}%)"
        )
    else:
        lines.append("Score expectation pass rate: N/A")

    if summary["role_expectation_checks"]:
        lines.append(
            "Role expectation pass rate: "
            f"{summary['role_expectation_passes']}/{summary['role_expectation_checks']} "
            f"({summary['role_expectation_pass_rate']:.2f}%)"
        )
    else:
        lines.append("Role expectation pass rate: N/A")

    if summary.get("selected_method_breakdown"):
        lines.append("Selected engine usage:")
        for method in summary["selected_method_breakdown"]:
            lines.append(f"- {method['label']}: {method['count']}")

    lines.extend(["", "Per-pair results:"])

    for result in results:
        score_check = _format_expectation_value(result["score_expectation_met"])
        role_check = _format_expectation_value(result["role_expectation_met"])
        lines.append(
            f"- {result['pair_name']}: {result['score']:.2f}% using {result['selected_method_label']}; "
            f"top role {result['top_role']} ({result['top_role_score']:.2f}%); "
            f"matched {result['matched_skill_count']} / missing {result['missing_skill_count']} skills; "
            f"score check {score_check}; role check {role_check}."
        )

    return "\n".join(lines)


def build_pdf_report(report_text):
    pdf_buffer = io.BytesIO()
    lines = report_text.splitlines() or [""]
    lines_per_page = 42

    with PdfPages(pdf_buffer) as pdf:
        for start_index in range(0, len(lines), lines_per_page):
            figure = Figure(figsize=(8.27, 11.69))
            axis = figure.add_subplot(111)
            axis.axis("off")

            y_position = 0.98
            for line in lines[start_index:start_index + lines_per_page]:
                axis.text(
                    0.03,
                    y_position,
                    line if line else " ",
                    fontsize=9,
                    family="monospace",
                    va="top",
                    transform=axis.transAxes,
                )
                y_position -= 0.022

            pdf.savefig(figure)

    return pdf_buffer.getvalue()