"""Profile MovieLens 100K and validate a pandas ranking workflow.

Purpose
-------
Post-submission analysis for interview preparation. This script demonstrates
the DataFrame-based profiling and validation approach discussed during review;
it does not claim that this analysis preceded the original submission.

Walkthrough
-----------
1. Understand the ratings table: grain, shape, types, and missing values.
2. Check uniqueness, allowed values, IDs, and timestamps.
3. Profile rating distributions and small-sample movies.
4. Validate movie metadata, genre flags, and genre definitions.
5. Aggregate, rank, and join titles using explicit relationship rules.
6. Reconcile counts and totals, then spot-check one movie's average.

Run from the project folder
---------------------------
    .venv/bin/python profiling.py

Requires pandas, available in the existing project environment. Source files
are read only: no cleaning, data replacement, or CSV export is performed.

Scope
-----
This is an exploratory script for the supplied MovieLens files, not a general
ingestion validator. Inferred numeric types are inspected before arithmetic.
Malformed schemas or nonnumeric IDs need additional handling for arbitrary
uploads. A clean result means the checks performed passed, not that every
value is factually correct. Timestamp bounds are reported, not independently
validated against the documented collection period.
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "ml-100k"
RATINGS_PATH = DATA_DIR / "u.data"
MOVIES_PATH = DATA_DIR / "u.item"
GENRES_PATH = DATA_DIR / "u.genre"

EXPECTED_GENRE_IDS = set(range(19))
ALLOWED_RATINGS = [1, 2, 3, 4, 5]


def print_section(title: str) -> None:
    """Separate report sections without changing pandas' global settings."""
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def main() -> None:
    """Run the profiling walkthrough and print evidence for each check."""

    # 01 | Understand the table before defining quality rules.
    # Grain: one user's rating of one movie at a recorded timestamp.
    # Repeated movie IDs are expected; repeated user/movie pairs need review.
    print_section("01 | RATINGS: STRUCTURE AND COMPLETENESS")
    print(f"Source: {RATINGS_PATH}")

    ratings = pd.read_csv(
        RATINGS_PATH,
        sep="\t",
        header=None,
        names=["user_id", "movie_id", "rating", "timestamp"],
    )

    print(f"\nRows: {len(ratings):,} | Columns: {len(ratings.columns)}")
    print("\nFirst five rows:")
    print(ratings.head().to_string(index=False))
    print("\nInferred column types:")
    print(ratings.dtypes.to_string())
    print("\nMissing values per column:")
    print(ratings.isna().sum().to_string())

    # 02 | Uniqueness and validity are different quality dimensions.
    # Counts describe findings; printing zero is not a permanent guarantee.
    print_section("02 | RATINGS: UNIQUENESS AND VALIDITY")

    # duplicated() excludes the first occurrence of each repeated key.
    # The pair check ignores rating/timestamp differences. A repeated pair
    # could be update history rather than an erroneous duplicate: clarify
    # the product's policy before dropping rows or choosing the latest one.
    repeated_pairs = ratings.duplicated(subset=["user_id", "movie_id"])
    invalid_ratings = ~ratings["rating"].isin(ALLOWED_RATINGS)

    print(f"Extra exact duplicate rows: {ratings.duplicated().sum():,}")
    print(f"Extra rows with a repeated user/movie pair: {repeated_pairs.sum():,}")
    print(f"Ratings outside {{1, 2, 3, 4, 5}}: {invalid_ratings.sum():,}")
    print(f"Non-positive user IDs: {(ratings['user_id'] <= 0).sum():,}")
    print(f"Non-positive movie IDs: {(ratings['movie_id'] <= 0).sum():,}")
    print(f"Negative timestamps: {(ratings['timestamp'] < 0).sum():,}")

    # A valid integer is not necessarily a valid business value.
    # Date conversion checks representability, not historical accuracy.
    rating_dates = pd.to_datetime(
        ratings["timestamp"],
        unit="s",
        origin="unix",
        utc=True,
        errors="coerce",
    )

    print(f"Missing or unconvertible timestamps: {rating_dates.isna().sum():,}")
    print(f"Earliest rating (UTC): {rating_dates.min()}")
    print(f"Latest rating (UTC):   {rating_dates.max()}")

    # 03 | Profiling also reveals interpretation risks in otherwise valid data.
    # These statistics describe rating COUNTS, not average rating SCORES.
    print_section("03 | DISTRIBUTIONS AND SMALL-SAMPLE RISK")

    print("Rating distribution:")
    print(ratings["rating"].value_counts(dropna=False).sort_index().to_string())

    rating_counts = ratings.groupby("movie_id").size()
    print("\nRating counts per movie - first five movie IDs:")
    print(rating_counts.head().to_string())
    print("\nSummary of rating counts per movie:")
    print(rating_counts.describe().to_string())
    print(f"\nMovies with exactly one rating: {(rating_counts == 1).sum():,}")
    print(f"Movies with fewer than five ratings: {(rating_counts < 5).sum():,}")
    print("Interpretation: a high average may be supported by very few ratings.")
    print("This is a ranking-policy consideration, not necessarily a data error.")

    # 04 | Validate the lookup table BEFORE joining it to aggregate results.
    # Unique movie IDs prevent one movie from matching multiple metadata rows.
    print_section("04 | MOVIE METADATA AND REFERENTIAL INTEGRITY")

    movies = pd.read_csv(
        MOVIES_PATH,
        sep="|",
        header=None,
        encoding="latin-1",
    )

    print(f"Movie metadata rows: {len(movies):,} | Columns: {len(movies.columns)}")
    if movies.shape[1] != 24:
        raise ValueError("Expected 24 movie columns: 5 metadata + 19 genre flags.")

    movie_details = movies.iloc[:, :2].copy()
    movie_details.columns = ["movie_id", "title"]
    print("\nFirst five movies:")
    print(movie_details.head().to_string(index=False))

    titles = movie_details["title"].astype("string")
    invalid_titles = titles.isna() | titles.str.strip().eq("").fillna(False)

    print(f"\nDuplicate movie IDs: {movie_details['movie_id'].duplicated().sum():,}")
    print(f"Missing movie IDs: {movie_details['movie_id'].isna().sum():,}")
    print(f"Non-positive movie IDs: {(movie_details['movie_id'] <= 0).sum():,}")
    print(f"Missing or blank titles: {invalid_titles.sum():,}")

    # A positive ID is not proof that its referenced record exists.
    # Set difference finds rated IDs without a matching metadata record.
    rated_movie_ids = set(ratings["movie_id"])
    metadata_movie_ids = set(movie_details["movie_id"])
    missing_movie_ids = rated_movie_ids - metadata_movie_ids

    print(f"Rated movie IDs missing from metadata: {sorted(missing_movie_ids)}")

    # 05 | Positional genre decoding depends on both files agreeing.
    # u.item flag position = 5 + genre_id; allowed IDs are exactly 0..18.
    print_section("05 | GENRE FLAGS AND DEFINITIONS")

    genre_flags = movies.iloc[:, 5:]
    invalid_genre_flags = ~genre_flags.isin([0, 1])

    print(f"Genre column count: {genre_flags.shape[1]}")
    # Two sums count invalid CELLS across all columns, not affected movies.
    print(f"Invalid genre flag cells: {invalid_genre_flags.sum().sum():,}")

    genres = pd.read_csv(
        GENRES_PATH,
        sep="|",
        header=None,
        names=["genre_name", "genre_id"],
        encoding="latin-1",
    )

    print("\nGenre definitions:")
    print(genres.to_string(index=False))

    # Sets remove duplicates, so uniqueness must be checked separately.
    actual_genre_ids = set(genres["genre_id"])
    genre_names = genres["genre_name"].astype("string")
    invalid_genre_names = (
        genre_names.isna() | genre_names.str.strip().eq("").fillna(False)
    )

    print(f"\nDuplicate genre IDs: {genres['genre_id'].duplicated().sum():,}")
    print(f"Missing genre IDs: {sorted(EXPECTED_GENRE_IDS - actual_genre_ids)}")
    print(f"Unexpected genre IDs: {sorted(actual_genre_ids - EXPECTED_GENRE_IDS)}")
    print(f"Missing or blank genre names: {invalid_genre_names.sum():,}")

    # 06 | Apply the same ordering as the submitted dictionary-based code.
    # No minimum count or Bayesian adjustment is introduced here.
    print_section("06 | AGGREGATION, RANKING, AND TITLE JOIN")

    movie_summary = ratings.groupby("movie_id").agg(
        average_rating=("rating", "mean"),
        rating_count=("rating", "size"),
        rating_total=("rating", "sum"),
    )

    ranked_movies = movie_summary.reset_index().sort_values(
        by=["average_rating", "rating_count", "movie_id"],
        ascending=[False, False, True],
    )

    # Left join preserves ranked movies even when metadata is missing.
    # one_to_one checks key uniqueness on both sides, NOT title accuracy.
    # The indicator distinguishes unmatched IDs from matched-but-empty titles.
    ranked_with_titles = ranked_movies.merge(
        movie_details,
        on="movie_id",
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    print("Top 10 movies - averages are formatted only for this display:")
    print(
        ranked_with_titles[
            ["movie_id", "title", "average_rating", "rating_count"]
        ].head(10).to_string(index=False, float_format=lambda value: f"{value:.6f}")
    )

    print("\nJoin match status:")
    print(ranked_with_titles["_merge"].value_counts().to_string())
    print("A left join never includes right-only rows; their count here is not")
    print("evidence that every metadata movie received a rating.")

    # 07 | Reconcile transformation results with the source.
    # Matching counts/totals can miss offsetting errors or swapped titles.
    # Therefore these checks complement, rather than replace, value checks.
    print_section("07 | RECONCILIATION AND AVERAGE SPOT CHECK")

    print(f"Rows before join: {len(ranked_movies):,}")
    print(f"Rows after join:  {len(ranked_with_titles):,}")

    # An explicit exception remains active even when Python runs with -O.
    # Most other checks in this exploratory report are diagnostic counts.
    if len(ranked_with_titles) != len(ranked_movies):
        raise ValueError("Movie row count changed after joining titles.")
    print("PASS: Movie row count preserved after join.")

    print(f"Missing titles after join: {ranked_with_titles['title'].isna().sum():,}")
    print(
        "Rating count preserved:",
        ranked_with_titles["rating_count"].sum() == len(ratings),
    )

    # Retain totals in the aggregate so both aggregation and join results
    # can be reconciled, instead of repeating a separate groupby calculation.
    original_rating_total = ratings["rating"].sum()
    grouped_rating_total = movie_summary["rating_total"].sum()
    joined_rating_total = ranked_with_titles["rating_total"].sum()

    print(f"\nOriginal rating total: {original_rating_total:,}")
    print(f"Grouped rating total:  {grouped_rating_total:,}")
    print(f"Joined rating total:   {joined_rating_total:,}")
    print(
        "Rating total preserved through aggregation and join:",
        original_rating_total == grouped_rating_total == joined_rating_total,
    )

    # Independently express the average as source sum / source count.
    # This spot-checks ONE movie, not every movie or source rating accuracy.
    movie_id_to_check = 1
    source_ratings = ratings.loc[
        ratings["movie_id"] == movie_id_to_check,
        "rating",
    ]

    if source_ratings.empty:
        raise ValueError(f"No source ratings for spot-check movie {movie_id_to_check}.")

    expected_average = source_ratings.sum() / source_ratings.count()
    actual_average = movie_summary.loc[movie_id_to_check, "average_rating"]

    print(f"\nAverage spot check - movie ID {movie_id_to_check}:")
    print(f"Expected average: {expected_average}")
    print(f"Actual average:   {actual_average}")
    print("Average matches:", abs(expected_average - actual_average) < 1e-10)

    print_section("INTERVIEW TAKEAWAY")
    print("Explain the checks as: completeness, uniqueness, validity,")
    print("referential integrity, and transformation reconciliation.")
    print("Separate data defects from product choices such as low-count ranking.")
    print("This is a scoped profile, not a blanket certification of data quality.")


if __name__ == "__main__":
    main()
