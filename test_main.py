import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from main import (
    get_movie_genres,
    load_movie_titles,
    load_rating_stats,
    rank_movies,
    validate_movie_ids,
    write_rankings,
)


class TestMovieLens(unittest.TestCase):
    def test_higher_average_ranks_first(self):
        movie_stats = {
            10: {"total": 8, "count": 2},
            20: {"total": 5, "count": 1},
        }

        result = rank_movies(movie_stats)

        self.assertEqual(result[0][0], 20)
        self.assertEqual(result[0][1]["average"], 5.0)

    def test_more_ratings_wins_when_averages_match(self):
        movie_stats = {
            10: {"total": 5, "count": 1},
            20: {"total": 15, "count": 3},
        }

        result = rank_movies(movie_stats)
        ranked_ids = [movie_id for movie_id, stats in result]

        self.assertEqual(ranked_ids, [20, 10])

    def test_lower_movie_id_wins_when_average_and_count_match(self):
        movie_stats = {
            20: {"total": 15, "count": 3},
            10: {"total": 15, "count": 3},
        }

        result = rank_movies(movie_stats)
        ranked_ids = [movie_id for movie_id, stats in result]

        self.assertEqual(ranked_ids, [10, 20])

    def test_only_enabled_genres_are_returned(self):
        genres = {0: "unknown", 1: "Action", 2: "Comedy"}
        movie_row = ["42", "Example Movie", "", "", "", "0", "1", "1"]

        result = get_movie_genres(movie_row, genres)

        self.assertEqual(result, ["Action", "Comedy"])

    def test_ratings_are_grouped_by_movie_id(self):
        fixture_path = (
            Path(__file__).parent / "tests" / "fixtures" / "ratings.tsv"
        )

        result = load_rating_stats(fixture_path)

        self.assertEqual(
            result,
            {
                10: {"total": 6, "count": 2},
                20: {"total": 5, "count": 1},
            },
        )

    def test_csv_preserves_title_and_writes_expected_fields(self):
        ranked_movies = [
            (42, {"total": 9, "count": 2, "average": 4.5}),
        ]
        movie_titles = {42: "Example Movie, The"}

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "target" / "rankings.csv"
            write_rankings(ranked_movies, movie_titles, output_path)

            with output_path.open(newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                rows = list(reader)
                fieldnames = reader.fieldnames

        self.assertEqual(
            fieldnames,
            ["Rank", "Movie Id", "Title", "Average Rating"],
        )
        self.assertEqual(
            rows,
            [
                {
                    "Rank": "1",
                    "Movie Id": "42",
                    "Title": "Example Movie, The",
                    "Average Rating": "4.5",
                }
            ],
        )

    def test_csv_limits_output_to_100_movies(self):
        ranked_movies = [
            (movie_id, {"average": 4.0})
            for movie_id in range(1, 106)
        ]
        movie_titles = {
            movie_id: f"Movie {movie_id}"
            for movie_id in range(1, 106)
        }

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "rankings.csv"
            write_rankings(ranked_movies, movie_titles, output_path)

            with output_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 100)
        self.assertEqual(
            [int(row["Rank"]) for row in rows],
            list(range(1, 101)),
        )
        self.assertEqual(rows[-1]["Movie Id"], "100")

    def test_rating_above_five_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "invalid_ratings.tsv"
            data_path.write_text(
                "1\t10\t6\t1000000000\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "line 1: rating must be between 1 and 5",
            ):
                load_rating_stats(data_path)

    def test_empty_ratings_file_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "empty.tsv"
            data_path.write_text("", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "no ratings found"):
                load_rating_stats(data_path)

    def test_missing_movie_title_is_rejected(self):
        movie_stats = {
            10: {"total": 8, "count": 2},
            20: {"total": 5, "count": 1},
        }
        movie_titles = {10: "Example Movie"}

        with self.assertRaisesRegex(
            ValueError,
            r"Missing movie titles for IDs: \[20\]",
        ):
            validate_movie_ids(movie_stats, movie_titles)

    def test_incomplete_movie_row_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            movies_path = Path(temp_dir) / "u.item"
            movies_path.write_text(
                "42|Example Movie\n",
                encoding="latin-1",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"u\.item, line 1: expected 24 fields",
            ):
                load_movie_titles(movies_path)


if __name__ == "__main__":
    unittest.main()