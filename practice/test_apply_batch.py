import csv
import importlib.util
import io
import sqlite3
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


# Load the existing script without executing its main function.
SCRIPT_PATH = Path(__file__).resolve().parent / "04_apply_batch.py"

spec = importlib.util.spec_from_file_location("apply_batch", SCRIPT_PATH)
apply_batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apply_batch)


class TestApplyBatch(unittest.TestCase):
    def setUp(self):
        """Create an isolated database and input directory for each test."""
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.test_dir = Path(self.temp_dir.name)
        self.db_path = self.test_dir / "test.db"
        self.batch_path = self.test_dir / "ratings_test.csv"

        connection = sqlite3.connect(self.db_path)
        try:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE ratings (
                        user_id INTEGER NOT NULL CHECK (user_id > 0),
                        movie_id INTEGER NOT NULL CHECK (movie_id > 0),
                        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                        timestamp INTEGER NOT NULL CHECK (timestamp >= 0),
                        PRIMARY KEY (user_id, movie_id)
                    )
                    """
                )
        finally:
            connection.close()

    def write_batch(self, rows):
        """Write a small synthetic batch."""
        with self.batch_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["user_id", "movie_id", "rating", "timestamp"])
            writer.writerows(rows)

    def run_batch(self):
        """Run the existing code against temporary paths."""
        with patch.object(apply_batch, "DB_PATH", self.db_path):
            with patch.object(apply_batch, "BATCH_PATH", self.batch_path):
                with redirect_stdout(io.StringIO()):
                    apply_batch.main()

    def query(self, sql):
        """Read database state for assertions."""
        connection = sqlite3.connect(self.db_path)
        try:
            return connection.execute(sql).fetchall()
        finally:
            connection.close()

    def test_new_batch_saves_ratings_and_history(self):
        self.write_batch([
            (1, 10, 4, 1000),
            (2, 10, 5, 1001),
        ])

        self.run_batch()

        self.assertEqual(
            self.query(
                "SELECT user_id, movie_id, rating, timestamp "
                "FROM ratings ORDER BY user_id"
            ),
            [(1, 10, 4, 1000), (2, 10, 5, 1001)],
        )
        self.assertEqual(
            self.query("SELECT batch_name, row_count FROM processed_batches"),
            [("ratings_test.csv", 2)],
        )

    def test_repeated_batch_does_not_duplicate_data(self):
        self.write_batch([(1, 10, 4, 1000)])

        self.run_batch()
        self.run_batch()

        self.assertEqual(
            self.query("SELECT COUNT(*) FROM ratings"),
            [(1,)],
        )
        self.assertEqual(
            self.query("SELECT COUNT(*) FROM processed_batches"),
            [(1,)],
        )

    def test_changed_file_is_rejected(self):
        self.write_batch([(1, 10, 4, 1000)])
        self.run_batch()

        original_history = self.query("SELECT * FROM processed_batches")

        self.write_batch([(1, 10, 2, 1000)])

        with self.assertRaisesRegex(ValueError, "different file contents"):
            self.run_batch()

        self.assertEqual(
            self.query("SELECT rating FROM ratings"),
            [(4,)],
        )
        self.assertEqual(
            self.query("SELECT * FROM processed_batches"),
            original_history,
        )

    def test_invalid_rating_rolls_back_entire_batch(self):
        # Save one valid batch before attempting a failing batch.
        self.write_batch([(1, 10, 4, 1000)])
        self.run_batch()

        original_history = self.query("SELECT * FROM processed_batches")

        self.batch_path = self.test_dir / "ratings_invalid.csv"
        self.write_batch([
            (2, 20, 3, 1001),
            (3, 30, 9, 1002),
        ])

        with self.assertRaises(sqlite3.IntegrityError):
            self.run_batch()

        # The valid first row of the failing batch must also be rolled back.
        self.assertEqual(
            self.query(
                "SELECT user_id, movie_id, rating, timestamp FROM ratings"
            ),
            [(1, 10, 4, 1000)],
        )
        self.assertEqual(
            self.query("SELECT * FROM processed_batches"),
            original_history,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)