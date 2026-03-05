import unittest
import csv
from pathlib import Path
import slac_db.oracle
import slac_db.aida


test_data_path = Path(__file__).parent / 'test_data'

class TestExample(unittest.TestCase):

    def setUp(self):
        p = test_data_path / 'example.db'
        slac_db.oracle._init_db(str(p))

    def test_get_example_areas(self):
        expected_areas = ["AREA1", "AREA2", "AREA3"]
        areas = slac_db.oracle.get_areas()
        self.assertEqual(areas, expected_areas)

    def test_get_example_beampaths(self):
        expected_areas = ["LINE1", "LINE2", "LINE3"]
        areas = slac_db.oracle.get_beampaths()
        self.assertEqual(areas, expected_areas)

class TestOracle(unittest.TestCase):

    def setUp(self):
        slac_db.oracle._init_db()

    def test_get_oracle_areas(self):
        p = test_data_path / 'expected_areas.csv'
        with open(str(p), 'r', newline='') as f:
            reader = csv.reader(f)
            expected_areas = next(reader)
        areas = slac_db.oracle.get_areas()
        self.assertEqual(areas, expected_areas)

    def test_get_oracle_beampaths(self):
        p = test_data_path / 'expected_beampaths.csv'
        with open(str(p), 'r', newline='') as f:
            reader = csv.reader(f)
            expected_beampaths = next(reader)
        beampaths = slac_db.oracle.get_beampaths()
        self.assertEqual(beampaths, expected_beampaths)

    def test_get_profile_monitors(self):
        profile_monitors = slac_db.oracle.get_devices(
            area="DIAG0",
            device_type="PROF"
        )
        expected_devices = ["OTRDG02", "OTRDG04"]
        self.assertEqual(profile_monitors, expected_devices)
