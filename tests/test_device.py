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

    def test_accessor_db(self):
        value = sorted([
            v.accessor_name
            for v in slac_db.device.get_all_accessors("BKRDG0")
        ])
        expected = ["BACT", "BCON", "BCTRL", "BDES", "BMAX", "BMIN", "CTRL"]
        self.assertEqual(value, expected)
