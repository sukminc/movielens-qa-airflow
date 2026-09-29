from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


# Locate the project directory relative to this script.
PROJECT_DIR = Path(__file__).resolve().parent.parent
RATINGS_PATH = PROJECT_DIR / "data" / "ml-100k" / "u.data"


def load_ratings(path):
    """Read each rating row into a dictionary."""
    ratings = []

    with path.open(encoding="utf-8") as file:
        for line in file:
            user_id, movie_id, rating, timestamp = line.strip().split("\t")

            ratings.append(
                {
                    "user_id": int(user_id),
                    "movie_id": int(movie_id),
                    "rating": int(rating),
                    "event_time": datetime.fromtimestamp(
                        int(timestamp),
                        tz=timezone.utc,
                    ),
                }
            )

    return ratings


def main():
    ratings = load_ratings(RATINGS_PATH)

    if not ratings:
        raise ValueError("The ratings file is empty.")

    # Sort explicitly because the source file may not be chronological.
    ratings.sort(key=lambda row: row["event_time"])

    print(f"Total ratings: {len(ratings):,}")
    print(f"Earliest rating: {ratings[0]['event_time']}")
    print(f"Latest rating: {ratings[-1]['event_time']}")

    print("\nFirst 5 ratings in chronological order:")
    for row in ratings[:5]:
        print(row)

    # Count ratings by UTC calendar date.
    daily_counts = Counter(
        row["event_time"].date()
        for row in ratings
    )

    print(f"\nNumber of dates with ratings: {len(daily_counts)}")

    print("\nRating counts for the first 5 dates:")
    for day, count in sorted(daily_counts.items())[:5]:
        print(f"{day}: {count:,} ratings")

    # Verify that grouping by date preserves the total rating count.
    counted_ratings = sum(daily_counts.values())

    if counted_ratings != len(ratings):
        raise ValueError("Daily counts do not match the source rating count.")

    print("\nValidation passed: daily counts match the source rating count.")


if __name__ == "__main__":
    main()