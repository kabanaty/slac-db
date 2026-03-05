import unittest
import csv
from pathlib import Path
import slac_db.aida

class TestAida(unittest.TestCase):
    def test_get_otrdg02_pvs(self):
        all_pvs = slac_db.aida.get_addresses(
            device="OTRDG04",
        )
        num_pvs = 2838
        self.assertEqual(len(all_pvs), num_pvs)
