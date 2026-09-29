import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
RATINGS_PATH = PROJECT_DIR / "data" / "ml-100k" / "u.data"

REPLAY_DIR = PROJECT_DIR / "practice" / "replay"
BATCH_DIR = REPLAY_DIR / "daily_batches"

CUTOFF = datetime(1997, 10, 1, tzinfo=timezone.utc)
FIELDNAMES = ["user_id", "movie_id", "rating", "timestamp"]


def load_ratings(path):
    """Read source ratings and sort them chronologically."""
    ratings = []

    with path.open(encoding="utf-8") as file:
        for line in file:
            user_id, movie_id, rating, timestamp = line.strip().split("\t")

            ratings.append(
                {
                    "user_id": int(user_id),
                    "movie_id": int(movie_id),
                    "rating": int(rating),
                    "timestamp": int(timestamp),
                }
            )

    ratings.sort(key=lambda row: row["timestamp"])
    return ratings


def write_csv(path, rows):
    """Write ratings with an explicit header."""
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def count_csv_rows(path):
    """Count data rows in an exported CSV file."""
    with path.open(newline="", encoding="utf-8") as file:
        return sum(1 for _ in csv.DictReader(file))


def main():
    ratings = load_ratings(RATINGS_PATH)

    if not ratings:
        raise ValueError("The ratings file is empty.")

    initial_ratings = []
    daily_batches = defaultdict(list)

    for row in ratings:
        event_time = datetime.fromtimestamp(
            row["timestamp"],
            tz=timezone.utc,
        )

        if event_time < CUTOFF:
            initial_ratings.append(row)
        else:
            batch_date = event_time.date().isoformat()
            daily_batches[batch_date].append(row)

    if not initial_ratings or not daily_batches:
        raise ValueError("The cutoff must produce both initial and batch data.")

    # Refuse to mix new output with files from an earlier run.
    if REPLAY_DIR.exists():
        raise FileExistsError(
            f"Output directory already exists: {REPLAY_DIR}. "
            "Choose a new output directory before running again."
        )

    BATCH_DIR.mkdir(parents=True)

    initial_path = REPLAY_DIR / "initial_ratings.csv"
    write_csv(initial_path, initial_ratings)

    batch_paths = []

    for batch_date, rows in sorted(daily_batches.items()):
        batch_path = BATCH_DIR / f"ratings_{batch_date}.csv"
        write_csv(batch_path, rows)
        batch_paths.append(batch_path)

    # Read the exported files to check that the total row count is preserved.
    initial_count = count_csv_rows(initial_path)
    batch_count = sum(count_csv_rows(path) for path in batch_paths)
    exported_count = initial_count + batch_count

    if exported_count != len(ratings):
        raise ValueError(
            f"Row count mismatch: source={len(ratings)}, "
            f"exported={exported_count}"
        )

    print(f"Cutoff: {CUTOFF.isoformat()}")
    print(f"Source ratings: {len(ratings):,}")
    print(f"Initial ratings: {initial_count:,}")
    print(f"Batch ratings: {batch_count:,}")
    print(f"Daily batch files: {len(batch_paths)}")

    print("\nFirst 5 batches:")
    for batch_date, rows in sorted(daily_batches.items())[:5]:
        print(f"{batch_date}: {len(rows):,} ratings")

    print(f"\nOutput directory: {REPLAY_DIR}")
    print("Validation passed: exported row count matches the source.")


if __name__ == "__main__":
    main()