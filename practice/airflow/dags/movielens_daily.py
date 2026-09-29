import importlib.util
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

# Airflow is installed in the Docker runtime, not the local editor environment.
from airflow.sdk import Param, dag, get_current_context, task  # pyright: ignore[reportMissingImports]


PRACTICE_DIR = Path("/opt/project/practice")
DB_PATH = PRACTICE_DIR / "movielens.db"


def load_batch_module():
    """Load the existing batch processing code."""
    script_path = PRACTICE_DIR / "04_apply_batch.py"
    spec = importlib.util.spec_from_file_location(
        "movielens_batch",
        script_path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module: {script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dag(
    dag_id="movielens_daily",
    description="Validate, apply, and verify a daily ratings batch.",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    params={
        "mode": Param(
            "replay",
            type="string",
            enum=["manual", "replay"],
            description="Choose a date manually or process the next replay batch.",
        ),
        "batch_date": Param(
            "1997-10-06",
            type="string",
            format="date",
            description="Used only in manual mode.",
        ),
    },
    tags=["practice", "movielens"],
)
def movielens_daily():
    @task(retries=0)
    def select_batch():
        """Choose a manual date or the next pending replay batch."""
        import sys

        from airflow.exceptions import AirflowSkipException  # pyright: ignore[reportMissingImports]

        practice_path = str(PRACTICE_DIR)
        if practice_path not in sys.path:
            sys.path.insert(0, practice_path)

        from replay import get_next_batch

        context = get_current_context()
        mode = context["params"]["mode"]

        if mode == "replay":
            batch_date = get_next_batch(PRACTICE_DIR / "replay_state.json")
            if batch_date is None:
                raise AirflowSkipException("All replay batches are complete.")
        elif mode == "manual":
            batch_date = date.fromisoformat(
                context["params"]["batch_date"]
            ).isoformat()
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        selection = {"mode": mode, "batch_date": batch_date}
        print(json.dumps(selection, indent=2))
        return selection

    @task(retries=0)
    def validate_input(selection):
        """Validate the selected batch before any database writes."""
        batch_date = date.fromisoformat(selection["batch_date"])
        batch_path = (
            PRACTICE_DIR
            / "replay"
            / "daily_batches"
            / f"ratings_{batch_date.isoformat()}.csv"
        )

        module = load_batch_module()
        ratings, file_hash = module.load_batch(batch_path)
        seen_keys = set()

        for line_number, row in enumerate(ratings, start=2):
            user_id, movie_id, rating, timestamp = row

            if user_id <= 0 or movie_id <= 0:
                raise ValueError(f"Line {line_number}: IDs must be positive.")

            if not 1 <= rating <= 5:
                raise ValueError(f"Line {line_number}: rating must be 1 to 5.")

            if timestamp < 0:
                raise ValueError(f"Line {line_number}: negative timestamp.")

            event_date = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            ).date()

            if event_date != batch_date:
                raise ValueError(
                    f"Line {line_number}: event date does not match batch date."
                )

            key = (user_id, movie_id)

            if key in seen_keys:
                raise ValueError(f"Line {line_number}: duplicate user/movie pair.")

            seen_keys.add(key)

        print(f"Input validation passed: {len(ratings):,} ratings.")

        return {
            "batch_path": str(batch_path),
            "file_hash": file_hash,
            "row_count": len(ratings),
        }

    @task(retries=0)
    def apply_daily_batch(batch_info):
        """Apply the validated batch using the existing transaction logic."""
        module = load_batch_module()
        batch_path = Path(batch_info["batch_path"])

        result = module.apply_batch(DB_PATH, batch_path)

        print(json.dumps(result, indent=2))
        return result

    @task(retries=0)
    def validate_output(batch_info, result):
        """Compare the input batch with the committed database records."""
        module = load_batch_module()
        batch_path = Path(batch_info["batch_path"])
        ratings, file_hash = module.load_batch(batch_path)

        if file_hash != batch_info["file_hash"]:
            raise ValueError("The batch file changed after input validation.")

        if not DB_PATH.is_file():
            raise FileNotFoundError("The ratings database is missing.")

        connection = sqlite3.connect(DB_PATH)

        try:
            history = connection.execute(
                """
                SELECT file_hash, row_count
                FROM processed_batches
                WHERE batch_name = ?
                """,
                (batch_path.name,),
            ).fetchone()

            if history != (file_hash, batch_info["row_count"]):
                raise ValueError("Batch history does not match the input.")

            for user_id, movie_id, rating, timestamp in ratings:
                stored = connection.execute(
                    """
                    SELECT rating, timestamp
                    FROM ratings
                    WHERE user_id = ? AND movie_id = ?
                    """,
                    (user_id, movie_id),
                ).fetchone()

                if stored != (rating, timestamp):
                    raise ValueError(
                        f"Stored rating mismatch: user={user_id}, movie={movie_id}"
                    )

            stored_count = connection.execute(
                "SELECT COUNT(*) FROM ratings"
            ).fetchone()[0]

            if stored_count != result["ratings_after"]:
                raise ValueError("Database count changed after batch processing.")

        finally:
            connection.close()

        print(f"Output validation passed: {len(ratings):,} ratings verified.")
        print(f"Total stored ratings: {stored_count:,}")

    @task(retries=0)
    def build_rankings_candidate():
        """Build a ranking candidate from the current ratings database."""
        import sys

        practice_path = str(PRACTICE_DIR)
        if practice_path not in sys.path:
            sys.path.insert(0, practice_path)

        from rankings import build_rankings

        candidate = build_rankings(
            DB_PATH,
            PRACTICE_DIR / "outputs",
        )

        print(json.dumps(candidate, indent=2))
        return candidate

    @task(retries=0)
    def validate_rankings_csv(candidate):
        """Validate the candidate against independently calculated rankings."""
        import sys

        practice_path = str(PRACTICE_DIR)
        if practice_path not in sys.path:
            sys.path.insert(0, practice_path)

        from validate_rankings import validate_rankings

        validation = validate_rankings(
            DB_PATH,
            candidate["candidate_path"],
        )

        print(json.dumps(validation, indent=2))
        return validation

    @task(retries=0)
    def publish_rankings_csv(validation):
        """Publish the candidate only after successful validation."""
        import sys

        practice_path = str(PRACTICE_DIR)
        if practice_path not in sys.path:
            sys.path.insert(0, practice_path)

        from publish_rankings import publish_rankings

        published_path = (
            PRACTICE_DIR
            / "outputs"
            / "published"
            / "top_100_movies.csv"
        )

        result = publish_rankings(validation, published_path)

        print(json.dumps(result, indent=2))
        return result
    
    @task(retries=0)
    def record_replay_completion(selection, publication):
        """Advance replay progress only after successful publication."""
        import sys

        if publication["status"] != "published":
            raise ValueError("Publication must succeed before recording progress.")

        if selection["mode"] == "manual":
            result = {
                "status": "not_applicable",
                "reason": "Manual runs do not advance replay progress.",
            }
        else:
            practice_path = str(PRACTICE_DIR)
            if practice_path not in sys.path:
                sys.path.insert(0, practice_path)

            from replay import record_completed_batch

            result = record_completed_batch(
                PRACTICE_DIR / "replay_state.json",
                selection["batch_date"],
            )

        print(json.dumps(result, indent=2))
        return result

    selection = select_batch()
    batch_info = validate_input(selection)
    result = apply_daily_batch(batch_info)
    output_check = validate_output(batch_info, result)

    candidate = build_rankings_candidate()
    output_check >> candidate

    validation = validate_rankings_csv(candidate)
    publication = publish_rankings_csv(validation)
    record_replay_completion(selection, publication)


movielens_daily()
