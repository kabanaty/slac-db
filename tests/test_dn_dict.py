import unittest
import slac_db.create.combined
import pykern.pkio
from pathlib import Path


test_data_path = Path(__file__).parent / 'test_data'

class test_DNDict(unittest.TestCase):
    def test_add_get(self):
        p = slac_db.create.combined._Parser()
        value = p.address_map["OTRS:DIAG0:420"]
        expected = pykern.pkio.read_text(
            test_data_path / "OTRDG02_names.txt"
        ).splitlines()
        self.assertEqual(len(value), len(expected))
