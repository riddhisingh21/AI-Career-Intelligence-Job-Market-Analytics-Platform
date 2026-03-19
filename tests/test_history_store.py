import sqlite3
import tempfile
import unittest
from pathlib import Path

from history_store import clear_analysis_history, get_recent_analyses, init_history_storage, save_analysis


class HistoryStoreTests(unittest.TestCase):
    def test_get_recent_analyses_returns_empty_list_for_new_db(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "history.db"

            init_history_storage(db_path)

            self.assertEqual(get_recent_analyses(db_path=db_path), [])

    def test_save_analysis_persists_and_orders_latest_first(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "history.db"

            init_history_storage(db_path)
            save_analysis("resume_one.pdf", 55.5, "Moderate", ["python"], ["sql"], db_path)
            save_analysis("resume_two.docx", 88.0, "Excellent", ["python", "sql"], [], db_path)

            analyses = get_recent_analyses(limit=5, db_path=db_path)

            self.assertEqual(len(analyses), 2)
            self.assertEqual(analyses[0]["resume_name"], "resume_two.docx")
            self.assertEqual(analyses[0]["matched_skills"], ["python", "sql"])
            self.assertEqual(analyses[0]["missing_skills"], [])
            self.assertEqual(analyses[1]["resume_name"], "resume_one.pdf")

    def test_clear_analysis_history_removes_saved_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "history.db"

            init_history_storage(db_path)
            save_analysis("resume.pdf", 70.0, "Good", ["python"], [], db_path)

            clear_analysis_history(db_path)

            self.assertEqual(get_recent_analyses(db_path=db_path), [])

    def test_get_recent_analyses_filters_by_user_email(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "history.db"

            init_history_storage(db_path)
            save_analysis("user_one.pdf", 70.0, "Good", ["python"], [], db_path, user_email="one@example.com")
            save_analysis("user_two.pdf", 82.0, "Strong", ["sql"], [], db_path, user_email="two@example.com")

            analyses = get_recent_analyses(db_path=db_path, user_email="one@example.com")

            self.assertEqual(len(analyses), 1)
            self.assertEqual(analyses[0]["resume_name"], "user_one.pdf")

    def test_clear_analysis_history_only_removes_current_user_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "history.db"

            init_history_storage(db_path)
            save_analysis("user_one.pdf", 70.0, "Good", ["python"], [], db_path, user_email="one@example.com")
            save_analysis("user_two.pdf", 82.0, "Strong", ["sql"], [], db_path, user_email="two@example.com")

            clear_analysis_history(db_path, user_email="one@example.com")

            self.assertEqual(get_recent_analyses(db_path=db_path, user_email="one@example.com"), [])
            self.assertEqual(len(get_recent_analyses(db_path=db_path, user_email="two@example.com")), 1)

    def test_init_history_storage_adds_user_email_column_for_existing_db(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "history.db"
            connection = sqlite3.connect(db_path)

            try:
                connection.execute(
                    """
                    CREATE TABLE analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        resume_name TEXT NOT NULL,
                        score REAL NOT NULL,
                        interpretation TEXT NOT NULL,
                        matched_skills TEXT NOT NULL,
                        missing_skills TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
            finally:
                connection.close()

            init_history_storage(db_path)
            save_analysis("resume.pdf", 91.0, "Excellent", ["python"], [], db_path, user_email="legacy@example.com")

            analyses = get_recent_analyses(db_path=db_path, user_email="legacy@example.com")

            self.assertEqual(len(analyses), 1)
            self.assertEqual(analyses[0]["resume_name"], "resume.pdf")


if __name__ == "__main__":
    unittest.main()