import unittest
import slac_db.io
from pathlib import Path

test_data_path = Path(__file__).parent / 'test_data'

class test_io(unittest.TestCase):
    def test_read_dict(self):
        value = slac_db.io.read_dict(test_data_path / "test_io.yaml")
        expected = {
            "a": 1,
            "b": {"foo": 2},
            "c": {"foo": 2}
        }
        self.assertEqual(value, expected)
