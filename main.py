import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def load_rating_stats(data_path: Path) -> dict:
    """Read ratings, validate each row, and group totals by movie."""
    movie_stats = {}

    with data_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            values = line.rstrip("\r\n").split("\t")

            if len(values) != 4:
                raise ValueError(
                    f"{data_path.name}, line {line_number}: "
                    "expected 4 tab-separated fields."
                )

            try:
                user_id, movie_id, rating, timestamp = map(int, values)
            except ValueError as error:
                raise ValueError(
                    f"{data_path.name}, line {line_number}: "
                    "all fields must be integers."
                ) from error

            if user_id < 1 or movie_id < 1 or timestamp < 0:
                raise ValueError(
                    f"{data_path.name}, line {line_number}: "
                    "IDs must be positive and timestamp non-negative."
                )

            if not 1 <= rating <= 5:
                raise ValueError(
                    f"{data_path.name}, line {line_number}: "
                    "rating must be between 1 and 5."
                )

            if movie_id not in movie_stats:
                movie_stats[movie_id] = {"total": 0, "count": 0}

            movie_stats[movie_id]["total"] += rating
            movie_stats[movie_id]["count"] += 1

    if not movie_stats:
        raise ValueError(f"{data_path.name}: no ratings found.")

    return movie_stats


def validate_movie_row(values: list, line_number: int) -> None:
    """Validate movie details and the 19 genre flags."""
    if len(values) != 24:
        raise ValueError(
            f"u.item, line {line_number}: expected 24 fields."
        )

    try:
        movie_id = int(values[0])
    except ValueError as error:
        raise ValueError(
            f"u.item, line {line_number}: movie ID must be an integer."
        ) from error

    if movie_id < 1 or not values[1].strip():
        raise ValueError(
            f"u.item, line {line_number}: "
            "movie ID must be positive and title must not be empty."
        )

    if any(flag not in ("0", "1") for flag in values[5:]):
        raise ValueError(
            f"u.item, line {line_number}: genre flags must be 0 or 1."
        )


def load_movie_titles(movies_path: Path) -> dict:
    """Read movie details and map each movie ID to its title."""
    movie_titles = {}

    with movies_path.open(encoding="latin-1") as file:
        for line_number, line in enumerate(file, start=1):
            values = line.rstrip("\r\n").split("|")
            validate_movie_row(values, line_number)

            movie_id = int(values[0])
            movie_titles[movie_id] = values[1]

    return movie_titles


def rank_movies(movie_stats: dict) -> list:
    """Calculate averages in place and rank by average, count, then ID."""
    for stats in movie_stats.values():
        stats["average"] = stats["total"] / stats["count"]

    return sorted(
        movie_stats.items(),
        key=lambda item: (
            -item[1]["average"],
            -item[1]["count"],
            item[0],
        ),
    )


def write_rankings(
    ranked_movies: list,
    movie_titles: dict,
    output_path: Path,
) -> None:
    """Write up to 100 ranked movies to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Rank", "Movie Id", "Title", "Average Rating"])

        for rank, (movie_id, stats) in enumerate(ranked_movies[:100], start=1):
            writer.writerow([
                rank,
                movie_id,
                movie_titles[movie_id],
                stats["average"],
            ])


def load_genres(genres_path: Path) -> dict:
    """Map genre IDs to genre names."""
    genres = {}

    with genres_path.open(encoding="latin-1") as file:
        for line in file:
            if not line.strip():
                continue

            name, genre_id = line.strip().split("|")
            genres[int(genre_id)] = name

    return genres


def get_movie_genres(values: list, genres: dict) -> list:
    """Return genre names for a parsed movie row."""
    selected_genres = []

    for genre_id, genre_name in genres.items():
        if values[5 + genre_id] == "1":
            selected_genres.append(genre_name)

    return selected_genres


def load_movie_genres(movies_path: Path, genres: dict) -> dict:
    """Map each movie ID to its genre names."""
    movie_genres = {}

    with movies_path.open(encoding="latin-1") as file:
        for line_number, line in enumerate(file, start=1):
            values = line.rstrip("\r\n").split("|")
            validate_movie_row(values, line_number)

            movie_id = int(values[0])
            movie_genres[movie_id] = get_movie_genres(values, genres)

    return movie_genres


def validate_movie_ids(movie_stats: dict, movie_titles: dict) -> None:
    """Ensure every rated movie has a matching title."""
    missing_ids = set(movie_stats) - set(movie_titles)

    if missing_ids:
        raise ValueError(
            f"Missing movie titles for IDs: {sorted(missing_ids)}"
        )


def main() -> None:
    """Load movie ratings and titles, then generate the ranking CSV."""
    data_path = BASE_DIR / "data" / "ml-100k" / "u.data"
    movie_stats = load_rating_stats(data_path)
    ranked_movies = rank_movies(movie_stats)

    movies_path = BASE_DIR / "data" / "ml-100k" / "u.item"
    movie_titles = load_movie_titles(movies_path)
    validate_movie_ids(movie_stats, movie_titles)

    output_path = BASE_DIR / "target" / "top_100_movies.csv"
    write_rankings(ranked_movies, movie_titles, output_path)

    print("CSV saved to:", output_path)


if __name__ == "__main__":
    main()