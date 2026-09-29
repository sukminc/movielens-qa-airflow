import hashlib
import json
import os
import tempfile
from pathlib import Path

from rankings import DB_PATH, OUTPUT_DIR, build_rankings
from validate_rankings import validate_rankings


PUBLISHED_PATH = OUTPUT_DIR / "published" / "top_100_movies.csv"


def publish_rankings(validation, published_path):
    """Publish the exact bytes that passed validation."""
    if validation["status"] != "validated":
        raise ValueError("Only validated candidates can be published.")

    candidate_path = Path(validation["candidate_path"])
    published_path = Path(published_path)

    contents = candidate_path.read_bytes()
    actual_hash = hashlib.sha256(contents).hexdigest()

    if actual_hash != validation["file_hash"]:
        raise ValueError("The candidate file changed after validation.")

    published_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None

    try:
        # Create the temporary file beside the final file.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=published_path.parent,
            prefix=".rankings-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            file.write(contents)

        # Replace the final file only after writing and closing the new file.
        os.replace(temporary_path, published_path)

    finally:
        # Remove any temporary file left behind by a failed publication.
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return {
        "status": "published",
        "published_path": str(published_path),
        "file_hash": actual_hash,
        "published_movie_count": validation["verified_movie_count"],
        "source_rating_count": validation["source_rating_count"],
    }


def main():
    candidate = build_rankings(DB_PATH, OUTPUT_DIR)

    validation = validate_rankings(
        DB_PATH,
        candidate["candidate_path"],
    )

    result = publish_rankings(validation, PUBLISHED_PATH)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()