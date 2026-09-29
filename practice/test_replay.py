import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from replay import get_next_batch, record_completed_batch


class TestReplay(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.state_path = Path(self.temp_dir.name) / "replay_state.json"
        self.state_path.write_text(
            json.dumps(
                {
                    "last_completed_batch_date": "1997-10-05",
                    "batch_dates": ["1997-10-06", "1997-10-07"],
                }
            ),
            encoding="utf-8",
        )

    def test_selection_does_not_advance_progress(self):
        original = self.state_path.read_bytes()

        self.assertEqual(get_next_batch(self.state_path), "1997-10-06")
        self.assertEqual(get_next_batch(self.state_path), "1997-10-06")
        self.assertEqual(self.state_path.read_bytes(), original)

    def test_completion_advances_to_next_batch(self):
        result = record_completed_batch(self.state_path, "1997-10-06")

        self.assertEqual(result["status"], "recorded")
        self.assertEqual(get_next_batch(self.state_path), "1997-10-07")

    def test_repeated_completion_is_safe(self):
        record_completed_batch(self.state_path, "1997-10-06")
        original = self.state_path.read_bytes()

        result = record_completed_batch(self.state_path, "1997-10-06")

        self.assertEqual(result["status"], "already_recorded")
        self.assertEqual(self.state_path.read_bytes(), original)
        self.assertEqual(get_next_batch(self.state_path), "1997-10-07")

    def test_out_of_order_completion_is_rejected(self):
        original = self.state_path.read_bytes()

        with self.assertRaisesRegex(ValueError, "Cannot advance replay"):
            record_completed_batch(self.state_path, "1997-10-07")

        self.assertEqual(self.state_path.read_bytes(), original)

    def test_no_next_batch_after_completion(self):
        record_completed_batch(self.state_path, "1997-10-06")
        record_completed_batch(self.state_path, "1997-10-07")

        self.assertIsNone(get_next_batch(self.state_path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
    