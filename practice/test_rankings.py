import csv
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rankings import build_rankings
from validate_rankings import validate_rankings


class TestRankings(unittest.TestCase):
    def setUp(self):
        """Create an isolated database with manually calculated expectations."""
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.test_dir = Path(self.temp_dir.name)
        self.db_path = self.test_dir / "ratings.db"

        ratings = [
            (1, 10, 5, 1000),
            (2, 10, 5, 1001),
            (1, 20, 5, 1002),
            (1, 30, 3, 1003),
            (2, 30, 5, 1004),
            (1, 40, 4, 1005),
            (2, 40, 4, 1006),
        ]

        connection = sqlite3.connect(self.db_path)

        try:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE ratings (
                        user_id INTEGER,
                        movie_id INTEGER,
                        rating INTEGER,
                        timestamp INTEGER
                    )
                    """
                )
                connection.executemany(
                    "INSERT INTO ratings VALUES (?, ?, ?, ?)",
                    ratings,
                )
        finally:
            connection.close()

        candidate = build_rankings(self.db_path, self.test_dir)
        self.candidate_path = Path(candidate["candidate_path"])

    def read_candidate(self):
        with self.candidate_path.open(newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    def write_candidate(self, rows):
        with self.candidate_path.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "rank",
                    "movie_id",
                    "rating_count",
                    "rating_total",
                    "average_rating",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

    def test_generated_rankings_match_known_answers(self):
        rows = self.read_candidate()

        actual = [
            (
                int(row["rank"]),
                int(row["movie_id"]),
                int(row["rating_count"]),
                int(row["rating_total"]),
                float(row["average_rating"]),
            )
            for row in rows
        ]

        self.assertEqual(
            actual,
            [
                (1, 10, 2, 10, 5.0),
                (2, 20, 1, 5, 5.0),
                (3, 30, 2, 8, 4.0),
                (4, 40, 2, 8, 4.0),
            ],
        )

    def test_valid_candidate_passes_validation(self):
        result = validate_rankings(self.db_path, self.candidate_path)

        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["verified_movie_count"], 4)
        self.assertEqual(result["source_rating_count"], 7)

    def test_incorrect_movie_order_is_rejected(self):
        rows = self.read_candidate()

        # Swap tied movies while keeping consecutive rank numbers.
        rows[0], rows[1] = rows[1], rows[0]

        for rank, row in enumerate(rows, start=1):
            row["rank"] = str(rank)

        self.write_candidate(rows)

        with self.assertRaisesRegex(ValueError, "movie_id mismatch"):
            validate_rankings(self.db_path, self.candidate_path)

    def test_incorrect_average_is_rejected(self):
        rows = self.read_candidate()
        rows[0]["average_rating"] = "4.9"
        self.write_candidate(rows)

        with self.assertRaisesRegex(ValueError, "average rating mismatch"):
            validate_rankings(self.db_path, self.candidate_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)