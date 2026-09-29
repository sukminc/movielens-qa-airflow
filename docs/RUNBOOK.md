# Reproduce the local demo

Run commands from the project root. These instructions assume a fresh extracted
archive, Python 3.9+ for the standard-library scripts, and Docker with Compose for
Airflow. The original UI's dependency pins were tested on Python 3.9.6.

## 1. Tests first

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m unittest -v test_main
python -m unittest discover -s practice -p 'test_*.py' -v
```

No pip installation is required for these tests or extension scripts. Install
`requirements.txt` for Streamlit, or `requirements-analysis.txt` for the optional
pandas profile. Airflow dependencies are provided by the pinned Docker image.

## 2. Obtain the source data

Download [MovieLens 100K](https://files.grouplens.org/datasets/movielens/ml-100k.zip)
and extract it into `data/ml-100k`. The directory must contain `u.data`, `u.item`,
and `u.genre`. Keep the dataset's accompanying README and follow its usage terms.

## 3. Bootstrap through October 5, 1997

The replay checkpoint initializer assumes that October 5 is already published.
Run the entire sequence in order, before starting replay:

```bash
python practice/01_inspect_ratings.py
python practice/02_prepare_batches.py
python practice/03_initialize_database.py
python practice/04_apply_batch.py 1997-10-01
python practice/04_apply_batch.py 1997-10-02
python practice/04_apply_batch.py 1997-10-03
python practice/04_apply_batch.py 1997-10-04
python practice/04_apply_batch.py 1997-10-05
python practice/publish_rankings.py
python practice/prepare_replay_state.py
python practice/replay.py
```

Expected baseline: 9,409 stored ratings, 100 published movies, and next replay
batch `1997-10-06`. The plan contains 197 remaining dates. The first three setup
scripts/checkpoint initializer are not reset commands: they refuse to overwrite
existing initialized state. To repeat a clean bootstrap, use a separate fresh
extraction rather than deleting your existing work. Reapplying a processed batch
with identical contents is safe.

The published extension file is `practice/outputs/published/top_100_movies.csv`.
It contains rank, movie ID, rating count, rating total, and average rating.

## 4. Start Airflow

```bash
docker --version
docker compose version
docker compose -f practice/airflow/compose.yaml up -d
docker compose -f practice/airflow/compose.yaml logs --tail=80 airflow
```

Allow time for the image download and standalone initialization. Open
[the local UI](http://localhost:8080). The service binds only to the loopback
interface. Retrieve the generated password locally:

```bash
docker compose -f practice/airflow/compose.yaml exec airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

Username: `admin`. In `admin:admin` in Compose, the second value is a role, not
a password. Credentials and Airflow's metadata/logs live in the Docker volume;
the application's SQLite DB lives in the mounted `practice` directory.

## 5. Run QA and the data pipeline

In the full DAG list, enable and trigger `movielens_qa_regression`. Its three tasks
run 4, 4, and 5 tests respectively. All should succeed. This QA DAG is separate
from the data DAG and does not automatically gate its execution.

Enable `movielens_daily`, trigger it with `mode=replay`, and leave `batch_date`
unchanged (ignored in replay mode). All eight tasks should succeed. After the first
successful replay, the checkpoint should select October 7:

```bash
python practice/replay.py
```

`mode=manual` processes the explicitly entered date without updating replay
progress. Use already completed dates for repeat demonstrations; processing future
dates manually can make the DB run ahead of the replay checkpoint.

## 6. Optional one-minute scheduling

In `practice/airflow/dags/movielens_daily.py`, change `schedule=None` to
`schedule="* * * * *"`. Keep the default mode `replay`, `catchup=False`, and
`max_active_runs=1`. Once loaded and unpaused, each scheduled run selects the next
uncompleted data date. The scheduler's current date is independent of the historical
batch date. Revert to `schedule=None` or pause the DAG when finished. Pausing does
not cancel an already running task. Do not run CLI ingestion concurrently.

After all batches complete, selection skips further work; the schedule itself
continues to create runs until paused or removed.

## 7. Additional local check

After publishing a baseline:

```bash
python practice/check_publication_guard.py
```

This uses a temporary directory to verify that changed candidate content is rejected
and that the previous test publication remains unchanged.

## Troubleshooting and shutdown

For missing DAGs, check the full DAG list, allow discovery time, then run:

```bash
docker compose -f practice/airflow/compose.yaml exec airflow airflow dags list-import-errors
```

Compose config sets a 10-second discovery refresh interval, but parsing/UI updates
can take additional time. A Pylance import warning can occur because Airflow exists
only in Docker; the three container-only imports have narrowly scoped diagnostic
exceptions. Local Airflow autocomplete is not configured.

Stop the demo while preserving Docker volume data:

```bash
docker compose -f practice/airflow/compose.yaml down
```

Avoid adding `-v` unless you intend to remove Airflow's stored metadata. Application
data in `practice/` remains on the host. If port 8080 is occupied, change the host
port in Compose and use that port in your browser.
