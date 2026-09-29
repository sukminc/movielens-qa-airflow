import csv
import json
import sqlite3
from pathlib import Path
from uuid import uuid4


PRACTICE_DIR = Path(__file__).resolve().parent
DB_PATH = PRACTICE_DIR / "movielens.db"
OUTPUT_DIR = PRACTICE_DIR / "outputs"

FIELDNAMES = [
    "rank",
    "movie_id",
    "rating_count",
    "rating_total",
    "average_rating",
]


def build_rankings(db_path, output_dir):
    """Build a candidate ranking from a consistent database snapshot."""
    db_path = Path(db_path).resolve()

    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")

    connection = sqlite3.connect(
        db_path.as_uri() + "?mode=ro",
        uri=True,
    )

    try:
        # Read source totals and movie aggregates from the same snapshot.
        connection.execute("BEGIN")

        source_count, source_total = connection.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(rating), 0)
            FROM ratings
            """
        ).fetchone()

        if source_count == 0:
            raise ValueError("The ratings table is empty.")

        movies = connection.execute(
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
            """
        ).fetchall()

    finally:
        connection.close()

    # Reconcile all movie aggregates before selecting the top 100.
    grouped_count = sum(row[1] for row in movies)
    grouped_total = sum(row[2] for row in movies)

    if grouped_count != source_count:
        raise ValueError("Aggregation did not preserve the rating count.")

    if grouped_total != source_total:
        raise ValueError("Aggregation did not preserve the rating total.")

    # Keep each candidate separate so later runs do not overwrite it.
    candidate_dir = Path(output_dir) / "candidates" / uuid4().hex
    candidate_dir.mkdir(parents=True, exist_ok=False)
    candidate_path = candidate_dir / "top_100_movies.csv"

    with candidate_path.open("x", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(FIELDNAMES)

        for rank, row in enumerate(movies[:100], start=1):
            writer.writerow((rank, *row))

    return {
        "candidate_path": str(candidate_path),
        "source_rating_count": source_count,
        "source_rating_total": source_total,
        "rated_movie_count": len(movies),
        "exported_movie_count": min(100, len(movies)),
    }


def main():
    result = build_rankings(DB_PATH, OUTPUT_DIR)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()