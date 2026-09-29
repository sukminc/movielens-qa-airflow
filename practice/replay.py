import json
import os
import tempfile
from datetime import date
from pathlib import Path


STATE_PATH = Path(__file__).resolve().parent / "replay_state.json"


def load_state(state_path):
    """Load the replay plan and validate its date ordering."""
    with Path(state_path).open(encoding="utf-8") as file:
        state = json.load(file)

    completed = date.fromisoformat(state["last_completed_batch_date"])
    batch_dates = [
        date.fromisoformat(value)
        for value in state["batch_dates"]
    ]

    if batch_dates != sorted(set(batch_dates)):
        raise ValueError("Batch dates must be unique and sorted.")

    return state, completed, batch_dates


def get_next_batch(state_path):
    """Select the next batch without changing replay progress."""
    _, completed, batch_dates = load_state(state_path)

    for batch_date in batch_dates:
        if batch_date > completed:
            return batch_date.isoformat()

    return None


def record_completed_batch(state_path, batch_date):
    """Advance progress after successful publication."""
    state_path = Path(state_path)
    state, completed, batch_dates = load_state(state_path)
    requested = date.fromisoformat(batch_date)

    # Allow a retry after the checkpoint was already saved.
    if requested == completed:
        return {
            "status": "already_recorded",
            "last_completed_batch_date": completed.isoformat(),
        }

    expected = next(
        (value for value in batch_dates if value > completed),
        None,
    )

    if requested != expected:
        raise ValueError(
            f"Cannot advance replay: expected={expected}, requested={requested}"
        )

    state["last_completed_batch_date"] = requested.isoformat()
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=state_path.parent,
            prefix=".replay-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(state, file, indent=2)
            file.write("\n")

        os.replace(temporary_path, state_path)

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return {
        "status": "recorded",
        "last_completed_batch_date": requested.isoformat(),
    }


if __name__ == "__main__":
    next_batch = get_next_batch(STATE_PATH)
    print(f"Next batch: {next_batch}")
    print("Replay progress was not changed.")