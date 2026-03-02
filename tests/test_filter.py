from pathlib import Path
import unittest
import slac_db.generate


class TestFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.data_location = (
            Path(__file__).parent / "test_data"
        )
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_filter_bad_prefix(self):
        csv_location = self.data_location / "DIAG0_only_good_element.csv"
        filter_location = self.data_location / "filter_stars.yaml"
        generator = slac_db.generate.YAMLGenerator(
            csv_location=csv_location, filter_location=filter_location
        )
        required_fields = ["Area", "Element"]
        elements = generator._filter_elements_by_fields(required_fields=required_fields)
        self.assertEqual(elements, [{"Area": "DIAG0", "Element": "GOOD"}])
