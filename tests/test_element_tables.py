import unittest
from pathlib import Path
import slac_db.element_tables
import slac_db.generate


test_data_path = Path(__file__).parent / 'test_data'

class TestExample(unittest.TestCase):

    def setUp(self):
        p = test_data_path / 'example.db'
        slac_db.element_tables._init_db(str(p))

    def test_get_example_areas(self):
        expected_areas = ["AREA1", "AREA2", "AREA3"]
        areas = slac_db.element_tables.get_areas()
        self.assertEqual(areas, expected_areas)

    def test_get_example_beampaths(self):
        expected_areas = ["LINE1", "LINE2", "LINE3"]
        areas = slac_db.element_tables.get_beampaths()
        self.assertEqual(areas, expected_areas)

class TestOracle(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.generator = slac_db.generate.YAMLGenerator()
        slac_db.element_tables._init_db()

    def test_get_oracle_areas(self):
        expected_areas = sorted(self.generator.extract_areas())
        areas = sorted(slac_db.element_tables.get_areas())
        self.assertEqual(areas, expected_areas)

    def test_get_oracle_beampaths(self):
        expected_beampaths = sorted(self.generator.extract_beampaths())
        beampaths = sorted(slac_db.element_tables.get_beampaths())
        self.assertEqual(beampaths, expected_beampaths)

    def test_get_profile_monitors(self):
        profile_monitors = slac_db.element_tables.get_devices(
            area="DIAG0",
            device_type="PROF"
        )
        expected_devices = ("OTRDG02", "OTRDG04")
        self.assertEqual(profile_monitors, expected_devices)
