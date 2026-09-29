from datetime import datetime, timezone
from pathlib import Path

# Airflow is installed in the Docker runtime, not the local editor environment.
from airflow.sdk import dag, task  # pyright: ignore[reportMissingImports]


PRACTICE_DIR = Path("/opt/project/practice")


@dag(
    dag_id="movielens_qa_regression",
    description="Run regression tests for batch processing and movie rankings.",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    tags=["practice", "movielens", "qa"],
)
def movielens_qa_regression():
    @task(retries=0)
    def run_test_suite(test_filename):
        """Run a test suite and fail the task if any test fails."""
        import subprocess
        import sys

        test_path = PRACTICE_DIR / test_filename

        if not test_path.is_file():
            raise FileNotFoundError(f"Test file not found: {test_path}")

        result = subprocess.run(
            [sys.executable, str(test_path)],
            cwd=str(PRACTICE_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            raise RuntimeError(
                f"Regression suite failed: {test_filename}, "
                f"exit code={result.returncode}"
            )

        return {
            "suite": test_filename,
            "status": "passed",
            "exit_code": result.returncode,
        }

    run_test_suite.override(
        task_id="test_batch_processing"
    )("test_apply_batch.py")

    run_test_suite.override(
        task_id="test_movie_rankings"
    )("test_rankings.py")

    run_test_suite.override(
        task_id="test_replay_progress"
    )("test_replay.py")


movielens_qa_regression()
