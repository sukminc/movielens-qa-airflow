import json
from datetime import date, datetime, timezone
from pathlib import Path


PRACTICE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PRACTICE_DIR.parent

SOURCE_PATH = PROJECT_DIR / "data" / "ml-100k" / "u.data"
BATCH_DIR = PRACTICE_DIR / "replay" / "daily_batches"
STATE_PATH = PRACTICE_DIR / "replay_state.json"

LAST_COMPLETED_DATE = date(1997, 10, 5)


def main():
    if STATE_PATH.exists():
        raise FileExistsError(
            "Replay state already exists. Do not reset existing progress."
        )

    source_dates = set()

    with SOURCE_PATH.open(encoding="utf-8") as file:
        for line in file:
            _, _, _, timestamp = line.strip().split("\t")

            event_date = datetime.fromtimestamp(
                int(timestamp),
                tz=timezone.utc,
            ).date()

            if event_date > LAST_COMPLETED_DATE:
                source_dates.add(event_date)

    batch_dates = sorted(source_dates)

    if not batch_dates:
        raise ValueError("No remaining source dates were found.")

    for batch_date in batch_dates:
        batch_path = BATCH_DIR / f"ratings_{batch_date.isoformat()}.csv"

        if not batch_path.is_file():
            raise FileNotFoundError(f"Missing batch file: {batch_path}")

    state = {
        "last_completed_batch_date": LAST_COMPLETED_DATE.isoformat(),
        "batch_dates": [
            batch_date.isoformat()
            for batch_date in batch_dates
        ],
    }

    with STATE_PATH.open("x", encoding="utf-8") as file:
        json.dump(state, file, indent=2)
        file.write("\n")

    print(f"Replay state: {STATE_PATH}")
    print(f"Last completed batch: {state['last_completed_batch_date']}")
    print(f"Remaining batches: {len(batch_dates)}")
    print(f"Next batch: {batch_dates[0].isoformat()}")
    print(f"Last planned batch: {batch_dates[-1].isoformat()}")
    print("Replay state created. No ratings were changed.")


if __name__ == "__main__":
    main()