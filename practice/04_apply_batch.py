import argparse
import csv
import hashlib
import io
import sqlite3
from datetime import date
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "practice" / "movielens.db"
BATCH_DIR = PROJECT_DIR / "practice" / "replay" / "daily_batches"

# Preserve the default entry point used by the existing regression tests.
BATCH_PATH = BATCH_DIR / "ratings_1997-10-01.csv"


def load_batch(path):
    """Read and fingerprint the same file contents."""
    contents = path.read_bytes()
    file_hash = hashlib.sha256(contents).hexdigest()

    reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))
    ratings = [
        (
            int(row["user_id"]),
            int(row["movie_id"]),
            int(row["rating"]),
            int(row["timestamp"]),
        )
        for row in reader
    ]

    if not ratings:
        raise ValueError("The batch file is empty.")

    return ratings, file_hash


def apply_batch(db_path, batch_path):
    """Apply one batch atomically and return its processing result."""
    if not db_path.is_file():
        raise FileNotFoundError("Initialize the database before applying a batch.")

    ratings, file_hash = load_batch(batch_path)
    connection = sqlite3.connect(db_path)

    try:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_batches (
                    batch_name TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    row_count INTEGER NOT NULL CHECK (row_count > 0),
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            previous_batch = connection.execute(
                """
                SELECT file_hash
                FROM processed_batches
                WHERE batch_name = ?
                """,
                (batch_path.name,),
            ).fetchone()

            before_count = connection.execute(
                "SELECT COUNT(*) FROM ratings"
            ).fetchone()[0]

            if previous_batch is not None:
                if previous_batch[0] != file_hash:
                    raise ValueError(
                        "The batch name was already processed "
                        "with different file contents."
                    )

                status = "skipped"
                after_count = before_count

            else:
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

                after_count = connection.execute(
                    "SELECT COUNT(*) FROM ratings"
                ).fetchone()[0]

                if after_count != before_count + len(ratings):
                    raise ValueError("The rating count increased unexpectedly.")

                connection.execute(
                    """
                    INSERT INTO processed_batches (
                        batch_name,
                        file_hash,
                        row_count
                    )
                    VALUES (?, ?, ?)
                    """,
                    (batch_path.name, file_hash, len(ratings)),
                )

                status = "applied"

        # Return only after the transaction commits successfully.
        return {
            "batch_name": batch_path.name,
            "status": status,
            "batch_rows": len(ratings),
            "ratings_before": before_count,
            "ratings_after": after_count,
        }

    finally:
        connection.close()


def main(batch_date=None):
    """Select a batch, apply it, and display the result."""
    if batch_date is None:
        batch_path = BATCH_PATH
    else:
        batch_path = BATCH_DIR / f"ratings_{batch_date.isoformat()}.csv"

    result = apply_batch(DB_PATH, batch_path)

    print(f"Batch: {result['batch_name']}")
    print(f"Status: {result['status']}")
    print(f"Batch rows: {result['batch_rows']:,}")
    print(f"Ratings before: {result['ratings_before']:,}")
    print(f"Ratings after: {result['ratings_after']:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apply one daily MovieLens ratings batch."
    )
    parser.add_argument(
        "batch_date",
        type=date.fromisoformat,
        help="Batch date in YYYY-MM-DD format.",
    )
    args = parser.parse_args()
    main(args.batch_date)