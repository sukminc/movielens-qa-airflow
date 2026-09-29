import csv
import sqlite3
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
INITIAL_PATH = PROJECT_DIR / "practice" / "replay" / "initial_ratings.csv"
DB_PATH = PROJECT_DIR / "practice" / "movielens.db"


def load_initial_ratings(path):
    """Read the initial CSV into tuples for database insertion."""
    ratings = []

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            ratings.append(
                (
                    int(row["user_id"]),
                    int(row["movie_id"]),
                    int(row["rating"]),
                    int(row["timestamp"]),
                )
            )

    return ratings


def main():
    ratings = load_initial_ratings(INITIAL_PATH)

    if not ratings:
        raise ValueError("The initial ratings file is empty.")

    connection = sqlite3.connect(DB_PATH)

    try:
        # Commit all changes together, or roll them back on failure.
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ratings (
                    user_id INTEGER NOT NULL CHECK (user_id > 0),
                    movie_id INTEGER NOT NULL CHECK (movie_id > 0),
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                    timestamp INTEGER NOT NULL CHECK (timestamp >= 0),
                    PRIMARY KEY (user_id, movie_id)
                )
                """
            )

            existing_count = connection.execute(
                "SELECT COUNT(*) FROM ratings"
            ).fetchone()[0]

            if existing_count > 0:
                raise ValueError(
                    "The ratings table already contains data. "
                    "Initialization requires an empty table."
                )

            connection.executemany(
                """
                INSERT INTO ratings (
                    user_id,
                    movie_id,
                    rating,
                    timestamp
                )
                VALUES (?, ?, ?, ?)
                """,
                ratings,
            )

            stored_count = connection.execute(
                "SELECT COUNT(*) FROM ratings"
            ).fetchone()[0]

            if stored_count != len(ratings):
                raise ValueError(
                    f"Row count mismatch: source={len(ratings)}, "
                    f"stored={stored_count}"
                )

            top_movies = connection.execute(
                """
                SELECT
                    movie_id,
                    COUNT(*) AS rating_count,
                    SUM(rating) AS rating_total,
                    AVG(rating) AS average_rating
                FROM ratings
                GROUP BY movie_id
                ORDER BY
                    average_rating DESC,
                    rating_count DESC,
                    movie_id ASC
                LIMIT 10
                """
            ).fetchall()

        print(f"Database: {DB_PATH}")
        print(f"Initial CSV rows: {len(ratings):,}")
        print(f"Stored ratings: {stored_count:,}")
        print("Validation passed: stored row count matches the initial CSV.")

        print("\nTop 10 movies:")
        print(
            f"{'Movie ID':>10} "
            f"{'Count':>8} "
            f"{'Total':>8} "
            f"{'Average':>10}"
        )

        for movie_id, count, total, average in top_movies:
            print(
                f"{movie_id:>10} "
                f"{count:>8} "
                f"{total:>8} "
                f"{average:>10.4f}"
            )

    finally:
        connection.close()


if __name__ == "__main__":
    main()