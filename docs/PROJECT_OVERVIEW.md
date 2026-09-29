# Personal extension: QA and Airflow

## Motivation and provenance

The starting point was a small take-home MovieLens exercise: parse ratings, rank
movies, export a CSV, and display selected movie statistics in Streamlit.
Afterward, I used it as a personal practice project to revisit ideas from my
previous QA regression work at theScore. The implementation was developed through
an AI-assisted, step-by-step learning workflow, with local execution and tests.
This is an independent learning implementation, not a copy of an employer's system.

## Added functionality

1. **Historical data replay.** Split the 100,000 source ratings by UTC date.
   The snapshot before 1997-10-01 contains 6,704 ratings; the remaining 93,296
   ratings form 202 daily batches. These are simulated arrivals, not live updates.
2. **SQLite ingestion.** Store one current rating per user/movie pair. A transaction
   applies a batch and records its filename, content hash, row count, and completion
   timestamp together. Replaying the same named file does not duplicate ratings;
   changed contents under an already processed name are rejected.
3. **Input and persistence checks.** Validate IDs, rating range, dates and duplicate
   keys, then compare each batch's rating and timestamp with committed DB values.
4. **Independent ranking validation.** Generate aggregates in SQL, reconcile totals,
   and compare the exported top 100 with a separate Python calculation.
5. **Publication protection.** Verify the candidate's content hash after validation,
   write those bytes to a temporary file, and atomically replace the published CSV.
6. **Replay progress.** Record the last completed replay date only after publication.
   Selection does not advance progress; completion recording is idempotent and
   rejects out-of-order dates.
7. **Separate QA orchestration.** Run batch, ranking, and replay tests as three
   independent Airflow tasks.

## DAGs

```text
movielens_daily
  select_batch
    -> validate_input
    -> apply_daily_batch
    -> validate_output
    -> build_rankings_candidate
    -> validate_rankings_csv
    -> publish_rankings_csv
    -> record_replay_completion

movielens_qa_regression
  test_batch_processing (4 tests)
  test_movie_rankings   (4 tests)
  test_replay_progress  (5 tests)
```

The QA DAG is independent: its success does not automatically authorize or block
the data DAG. Within the data DAG, validation tasks gate downstream processing
and publication. Both DAGs ship without a schedule. The data DAG supports opt-in
one-minute replay using `schedule="* * * * *"` and the default `mode="replay"`.

## Evidence and scope

- Automated tests exercise ingestion, duplicate replay, changed-file rejection,
  transaction rollback, known ranking answers, incorrect averages/order, and replay
  progress behavior (13 extension tests, plus 11 original tests).
- Local Airflow runs demonstrated successful batch processing, duplicate handling,
  input-failure propagation, full CSV publication, and scheduled replay.
- `check_publication_guard.py` demonstrates that modifying a validated candidate
  blocks publication while preserving the previous published file in a temporary
  test directory. It requires a prepared DB and an existing published CSV.
- A full Airflow fault-injection exercise between DB commit and publication was
  discussed but not completed; it is not claimed as demonstrated recovery coverage.

## Current boundaries

- This is a single-machine Docker/SQLite learning demo. Files are shared through
  bind mounts. The JSON replay checkpoint assumes one writer; `max_active_runs=1`
  limits this DAG, not unrelated CLI writers or other DAGs.
- Ingestion currently accepts new user/movie pairs. Rating updates, deletions,
  and late-arrival policies are not implemented. Batch date must equal event date.
- Input validation, DB commit, publication, and checkpointing are separate steps,
  not one distributed transaction. A downstream failure cannot undo a committed
  batch. A replay can skip that batch and attempt downstream work again.
- Candidate validation reads the current DB; concurrent external writes are outside
  this demo's consistency assumptions. Input files should remain unchanged during
  a run; the workflow does not lock them across tasks.
- Ranking uses raw mean, count descending, then movie ID ascending. Small-sample
  bias remains. The extension export does not include titles or genres.
- The initial replay checkpoint is fixed at 1997-10-05; the documented bootstrap
  must process and publish through that date before creating it.
- GitHub Actions runs the 24 unit tests and syntax checks. Docker/Airflow execution
  is demonstrated locally rather than in CI. No cloud deployment, external alerts,
  or production authentication is configured. Airflow Simple Auth is used for local
  development.
- `profiling.py` is optional exploratory data profiling, not runtime performance
  profiling or a comprehensive validator.

## File map

| Files | Purpose |
| --- | --- |
| `main.py`, `app.py`, `test_main.py` | Initial ranking application and tests |
| `practice/01_inspect_ratings.py`, `02_prepare_batches.py` | Inspect and split source ratings |
| `practice/03_initialize_database.py`, `04_apply_batch.py` | Bootstrap and transactional ingestion |
| `practice/rankings.py`, `validate_rankings.py`, `publish_rankings.py` | Candidate, validation, publication |
| `practice/replay.py`, `prepare_replay_state.py` | Replay selection and progress |
| `practice/test_*.py` | Isolated extension regression tests |
| `practice/airflow/` | Docker setup and DAG definitions |
