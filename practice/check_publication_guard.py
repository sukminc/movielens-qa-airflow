from pathlib import Path
from tempfile import TemporaryDirectory

from rankings import DB_PATH, OUTPUT_DIR, build_rankings
from validate_rankings import validate_rankings
from publish_rankings import publish_rankings


def main():
    current_published_path = (
        OUTPUT_DIR / "published" / "top_100_movies.csv"
    )
    previous_contents = current_published_path.read_bytes()

    with TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)

        # Create and validate a candidate in an isolated directory.
        candidate = build_rankings(DB_PATH, test_dir)
        validation = validate_rankings(
            DB_PATH,
            candidate["candidate_path"],
        )

        # Simulate an existing published file.
        test_published_path = test_dir / "published" / "top_100_movies.csv"
        test_published_path.parent.mkdir(parents=True)
        test_published_path.write_bytes(previous_contents)

        # Change the candidate after validation.
        candidate_path = Path(candidate["candidate_path"])
        contents = candidate_path.read_text(encoding="utf-8")
        candidate_path.write_text(
            contents.replace("average_rating", "incorrect_column", 1),
            encoding="utf-8",
        )

        try:
            publish_rankings(validation, test_published_path)
        except ValueError as error:
            if str(error) != "The candidate file changed after validation.":
                raise

            print(f"Publication blocked: {error}")
        else:
            raise AssertionError("The modified candidate was published.")

        if test_published_path.read_bytes() != previous_contents:
            raise AssertionError("The previous published file was changed.")

        print("PASS: the previous published file is unchanged.")
        print("PASS: the modified candidate was not published.")


if __name__ == "__main__":
    main()