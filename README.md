# MovieLens QA & Airflow

A personal learning project that extends a small MovieLens ranking application
with batch ingestion, data-quality checks, regression tests, and Apache Airflow
orchestration. The initial ranking application originated as a take-home exercise;
the Airflow and QA extension was developed afterward as independent practice.

## What to review

- [Extension overview](docs/PROJECT_OVERVIEW.md): architecture, added behavior,
  validation evidence, and current limitations.
- [Reproduce the demo](docs/RUNBOOK.md): clean setup, Airflow login, and replay.
- [Interview walkthrough](docs/INTERVIEW_GUIDE.md): a short explanation, demo flow,
  and design tradeoffs to discuss.
- [Original application documentation](docs/ORIGINAL_README.md): the initial
  CSV generator and Streamlit explorer, preserved as a reference.

The extension models incoming data by replaying historical ratings in UTC daily
batches. It is a local demonstration, not a live service or production deployment.

## Original application versus extension

| Area | Initial application | Personal extension |
| --- | --- | --- |
| Input | Full MovieLens files | Initial snapshot plus daily replay batches |
| Storage | In-memory dictionaries | SQLite ratings and processed-batch ledger |
| Ranking | Python aggregation | SQL aggregation checked independently in Python |
| Output | CSV with movie titles | Validated top-100 CSV with IDs, counts, totals, averages |
| Execution | CLI and Streamlit | Eight-task Airflow pipeline, manual or scheduled replay |
| Testing | 11 unit tests | 13 additional unit tests and a three-task QA DAG |
| Recovery | Rerun the script | Duplicate-batch protection and post-publication checkpoint |

The original Streamlit app still reads the full source dataset. It has not been
connected to the extension's published CSV.

## Dependencies

| Component | Requirement |
| --- | --- |
| Original UI | `python -m pip install -r requirements.txt` (Streamlit 1.50.0) |
| Extension scripts and tests | Python standard library; no additional pip packages |
| Airflow | Docker and Docker Compose; image pinned to `apache/airflow:3.2.2` |
| Optional pandas profiling | `python -m pip install -r requirements-analysis.txt` |

Local scripts were exercised with Python 3.9.6 on Apple Silicon macOS. Airflow
uses its container's Python, independently of the local virtual environment.
`requirements.txt` intentionally does not install Airflow into the local environment.

## Run tests without downloading data or starting Docker

From the project root:

```bash
python3 -m unittest -v test_main
python3 -m unittest discover -s practice -p 'test_*.py' -v
```

Expected: 11 original tests and 13 extension tests. Fixtures and temporary databases
make these tests independent of the full dataset and current replay progress.
GitHub Actions runs these same 24 tests on pushes and pull requests using Python
3.11. The workflow also checks Python syntax; it does not launch Docker or test
Airflow scheduling.

## Original app quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Download [MovieLens 100K](https://files.grouplens.org/datasets/movielens/ml-100k.zip)
and extract it to `data/ml-100k`. Then:

```bash
python main.py
python -m streamlit run app.py
```

For the extension, follow the [runbook](docs/RUNBOOK.md), including the initial
five-batch bootstrap before creating replay state.

## Package contents

Source code, tests, synthetic fixtures, documentation, dependency files, and Docker
Compose configuration are included. Downloaded data, local virtual environments,
SQLite files, replay state, generated CSVs, Docker logs, and credentials are excluded.

Rebuild the shareable archive with:

```bash
python3 scripts/package_project.py
```
