# MovieLens Explorer

A Python application that ranks movies from the MovieLens 100K dataset
and provides a Streamlit interface for exploring 10 movies.

## Requirements

- Tested with Python 3.9.6
- Streamlit 1.50.0
- Internet access to install dependencies and download the dataset

Run the commands below from the project folder.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, activate it with `.venv\Scripts\activate` instead.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Dataset

Download the MovieLens 100K archive:

https://files.grouplens.org/datasets/movielens/ml-100k.zip

Extract it and place the `ml-100k` folder inside `data`.

The application uses:

- `data/ml-100k/u.data`: user ratings
- `data/ml-100k/u.item`: movie titles and genre flags
- `data/ml-100k/u.genre`: genre IDs and names

Dataset documentation:
https://files.grouplens.org/datasets/movielens/ml-100k-README.txt

The full dataset and generated output are excluded from the submission.
Small synthetic test data is included in `tests/fixtures`.

## Generate the CSV

```bash
python main.py
```

Output: `target/top_100_movies.csv`

Columns: Rank, Movie Id, Title, Average Rating.

Movies are sorted by:

1. Average rating, descending.
2. Number of ratings, descending.
3. Movie ID, ascending.

No minimum rating count is applied. A movie with one five-star rating
can therefore outrank a widely rated movie with a lower average.
This follows the requested average-rating ranking.

Ranks are consecutive positions from 1 to 100, including tied averages.
Averages are not rounded before sorting or CSV export.

## Run the Interface

```bash
python -m streamlit run app.py
```

Open the local URL shown in the terminal.

The dropdown contains the first 10 movies from the same ranking.
Selecting a movie displays its rating count, average score, and genres.
The interface displays averages to two decimal places.

Data is cached in memory. After replacing dataset files, restart the
Streamlit server to reload them.

## Run Tests

```bash
python -m unittest -v
```

Tests use synthetic data and temporary files; the full dataset is not
required.

Coverage includes ranking order, tie-breakers, genre decoding, rating
aggregation, CSV fields and comma-containing titles, the 100-row limit,
invalid and empty ratings, missing movie titles, and incomplete movie rows.

## Project Structure

- `main.py`: data loading, validation, ranking, and CSV generation
- `app.py`: Streamlit interface
- `test_main.py`: automated tests
- `tests/fixtures/ratings.tsv`: synthetic ratings fixture
- `requirements.txt`: application dependency
- `.gitignore`: excludes local environments, data, and generated files
- `data/`: downloaded dataset, prepared separately
- `target/`: generated CSV output

 ## Production Approach

The current app reads a fixed dataset from local files. For a live
application, I would make the following changes:

### Storage and ingestion

Store movies, genres, and individual ratings in a database such as
PostgreSQL. Validate incoming ratings and enforce relationships between
ratings and movies.

Define whether users can update existing ratings. Make ingestion
idempotent so retrying an event does not count a rating twice.

### Aggregation and API

Maintain each movie's rating sum and count, and calculate its average
as sum divided by count. Handle rating updates and deletions as well
as new ratings.

Expose movie lists and statistics through an API. The interface would
request the selected movie's statistics instead of reading local files.

Preserve the documented tie-breaking rules across CSV exports and
API responses.

### Freshness and caching

Agree on a freshness requirement before choosing an update strategy.
For example, if a one-minute delay is acceptable, refresh aggregates
periodically and use a short-lived cache.

Show when statistics were last updated. Invalidate or refresh cached
results when the underlying aggregates change.

### Reliability and delivery

Use automated tests in CI, structured logs, and monitoring for failed
ingestion, stale aggregates, and API errors.

Keep credentials outside source code. Run the application in a
reproducible deployment environment and apply database migrations
through a controlled release process.