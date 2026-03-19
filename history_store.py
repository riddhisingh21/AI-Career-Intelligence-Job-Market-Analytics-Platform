import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path


DEFAULT_DB_PATH = Path("analysis_history.db")


def init_history_storage(db_path=DEFAULT_DB_PATH):
    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                user_email TEXT NOT NULL DEFAULT '',
                resume_name TEXT NOT NULL,
                score REAL NOT NULL,
                interpretation TEXT NOT NULL,
                matched_skills TEXT NOT NULL,
                missing_skills TEXT NOT NULL
            )
            """
        )
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(analysis_history)").fetchall()
        }

        if "user_email" not in columns:
            connection.execute("ALTER TABLE analysis_history ADD COLUMN user_email TEXT NOT NULL DEFAULT ''")

        connection.commit()
    finally:
        connection.close()


def save_analysis(
    resume_name,
    score,
    interpretation,
    matched_skills,
    missing_skills,
    db_path=DEFAULT_DB_PATH,
    user_email="",
):
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    normalized_user_email = str(user_email or "").strip().lower()

    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            """
            INSERT INTO analysis_history (
                created_at,
                user_email,
                resume_name,
                score,
                interpretation,
                matched_skills,
                missing_skills
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                normalized_user_email,
                resume_name,
                score,
                interpretation,
                json.dumps(matched_skills),
                json.dumps(missing_skills),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def clear_analysis_history(db_path=DEFAULT_DB_PATH, user_email=None):
    normalized_user_email = str(user_email or "").strip().lower()
    connection = sqlite3.connect(db_path)

    try:
        if normalized_user_email:
            connection.execute("DELETE FROM analysis_history WHERE user_email = ?", (normalized_user_email,))
        else:
            connection.execute("DELETE FROM analysis_history")
        connection.commit()
    finally:
        connection.close()


def get_recent_analyses(limit=5, db_path=DEFAULT_DB_PATH, user_email=None):
    normalized_user_email = str(user_email or "").strip().lower()
    connection = sqlite3.connect(db_path)

    try:
        if normalized_user_email:
            rows = connection.execute(
                """
                SELECT created_at, resume_name, score, interpretation, matched_skills, missing_skills
                FROM analysis_history
                WHERE user_email = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (normalized_user_email, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT created_at, resume_name, score, interpretation, matched_skills, missing_skills
                FROM analysis_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        connection.close()

    return [
        {
            "created_at": row[0],
            "resume_name": row[1],
            "score": row[2],
            "interpretation": row[3],
            "matched_skills": json.loads(row[4]),
            "missing_skills": json.loads(row[5]),
        }
        for row in rows
    ]