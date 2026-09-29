import csv
import hashlib
import io
import json
import math
import sqlite3
from pathlib import Path

from rankings import DB_PATH, OUTPUT_DIR, build_rankings


EXPECTED_FIELDS = [
    "rank",
    "movie_id",
    "rating_count",
    "rating_total",
    "average_rating",
]


def calculate_expected_rankings(db_path):
    """Calculate expected rankings directly from individual ratings."""
    db_path = Path(db_path).resolve()
    connection = sqlite3.connect(
        db_path.as_uri() + "?mode=ro",
        uri=True,
    )

    try:
        source_rows = connection.execute(
            "SELECT movie_id, rating FROM ratings"
        ).fetchall()
    finally:
        connection.close()

    if not source_rows:
        raise ValueError("The ratings table is empty.")

    movie_stats = {}

    for movie_id, rating in source_rows:
        if movie_id not in movie_stats:
            movie_stats[movie_id] = {"count": 0, "total": 0}

        movie_stats[movie_id]["count"] += 1
        movie_stats[movie_id]["total"] += rating

    expected = []

    for movie_id, stats in movie_stats.items():
        expected.append(
            {
                "movie_id": movie_id,
                "rating_count": stats["count"],
                "rating_total": stats["total"],
                "average_rating": stats["total"] / stats["count"],
            }
        )

    expected.sort(
        key=lambda row: (
            -row["average_rating"],
            -row["rating_count"],
            row["movie_id"],
        )
    )

    return expected[:100], len(source_rows)


def validate_rankings(db_path, candidate_path):
    """Compare a candidate CSV with independently calculated results."""
    candidate_path = Path(candidate_path)
    expected, source_count = calculate_expected_rankings(db_path)

    # Validate and fingerprint the same file contents.
    contents = candidate_path.read_bytes()
    reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))

    if reader.fieldnames != EXPECTED_FIELDS:
        raise ValueError("CSV columns do not match the expected schema.")

    actual = list(reader)

    if len(actual) != len(expected):
        raise ValueError(
            f"Row count mismatch: expected={len(expected)}, actual={len(actual)}"
        )

    integer_fields = [
        "movie_id",
        "rating_count",
        "rating_total",
    ]

    for rank, (actual_row, expected_row) in enumerate(
        zip(actual, expected),
        start=1,
    ):
        if set(actual_row) != set(EXPECTED_FIELDS):
            raise ValueError(f"Rank {rank}: unexpected CSV fields.")

        if any(value is None for value in actual_row.values()):
            raise ValueError(f"Rank {rank}: missing CSV fields.")

        if int(actual_row["rank"]) != rank:
            raise ValueError(f"Rank {rank}: incorrect rank number.")

        for field in integer_fields:
            if int(actual_row[field]) != expected_row[field]:
                raise ValueError(
                    f"Rank {rank}: {field} mismatch. "
                    f"Expected {expected_row[field]}, got {actual_row[field]}."
                )

        actual_average = float(actual_row["average_rating"])
        expected_average = expected_row["average_rating"]

        if not math.isclose(
            actual_average,
            expected_average,
            rel_tol=0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"Rank {rank}: average rating mismatch.")

    return {
        "status": "validated",
        "candidate_path": str(candidate_path),
        "file_hash": hashlib.sha256(contents).hexdigest(),
        "verified_movie_count": len(actual),
        "source_rating_count": source_count,
    }


def main():
    # Build a fresh candidate, then validate it against the current database.
    candidate = build_rankings(DB_PATH, OUTPUT_DIR)

    result = validate_rankings(
        DB_PATH,
        candidate["candidate_path"],
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()