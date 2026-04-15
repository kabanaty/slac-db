import unittest
import slac_db.device
import pykern.pkio
from pathlib import Path


test_data_path = Path(__file__).parent / 'test_data'

class test_device(unittest.TestCase):
    def test_address_db(self):
        value = slac_db.device.get_all_addresses("OTRDG02")
        expected = pykern.pkio.read_text(
            test_data_path / "OTRDG02_names.txt"
        ).splitlines()
        self.assertEqual(len(value), len(expected))

    def test_get_device(self):
        value = slac_db.device.get_device(area="DIAG0", device_type="PROF")
        expected = ["OTRDG02", "OTRDG04"]
        self.assertEqual(value, expected)
