import os
import shutil
import unittest
import slac_db.write
from pathlib import Path
from unittest.mock import patch, PropertyMock
import yaml


class TestWrite(unittest.TestCase):
    def setUp(self):
        self.data_location = (
            Path(__file__).parent / "test_data"
        )
        assert os.path.exists(self.data_location)
        area_location = self.data_location / "AREA.yaml"
        with open(area_location, "r") as file:
            self.area = yaml.safe_load(file)
        self.generate_patcher = patch(
            "slac_db.write.YAMLGenerator"
        )
        self.mock_generate = self.generate_patcher.start()
        instance = self.mock_generate.return_value
        instance.extract_magnets.return_value = {}
        instance.extract_screens.return_value = self.area["screens"]
        instance.extract_wires.return_value = self.area["wires"]
        instance.extract_lblms.return_value = {}
        instance.extract_bpms.return_value = {}
        instance.extract_tcavs.return_value = {}
        instance.extract_pmts.return_value = {}
        type(instance).areas = PropertyMock(return_value=["AREA"])
        testbed = self.data_location / "testbed/"
        if not os.path.exists(testbed):
            os.makedirs(testbed)
        self.testbed = testbed

    def tearDown(self):
        shutil.rmtree(self.testbed)
        self.generate_patcher.stop()

    def test_overwrite_yaml(self):
        result_location = self.testbed
        partial_area = self.data_location / "PARTIALAREA.yaml"
        shutil.copyfile(partial_area, result_location / "AREA.yaml")
        slac_db.write.write(location=result_location)
        result_location /= "AREA.yaml"
        with open(result_location, "r") as file:
            res = yaml.safe_load(file)
        self.assertEqual(self.area, res)
        os.remove(result_location)

    def test_greedy_write_yaml(self):
        result_location = self.testbed
        partial_area = self.data_location / "PARTIALAREA.yaml"
        shutil.copyfile(partial_area, result_location / "AREA.yaml")
        slac_db.write.write(
            location=result_location, mode="greedy"
        )
        result_location /= "AREA.yaml"
        with open(result_location, "r") as file:
            res = yaml.safe_load(file)
        self.assertIn("wires", res)
        self.assertIn("magnets", res)
        self.assertIn("bar", res["screens"]["FAKESCREEN"])
        self.assertEqual(res["screens"]["FAKESCREEN"]["foo"], 1)
        os.remove(result_location)

    def test_lazy_write_yaml(self):
        result_location = self.testbed
        partial_area = self.data_location / "PARTIALAREA.yaml"
        shutil.copyfile(partial_area, result_location / "AREA.yaml")
        slac_db.write.write(
            location=result_location, mode="lazy"
        )
        result_location /= "AREA.yaml"
        with open(result_location, "r") as file:
            res = yaml.safe_load(file)
        self.assertIn("wires", res)
        self.assertIn("magnets", res)
        self.assertIn("bar", res["screens"]["FAKESCREEN"])
        self.assertEqual(res["screens"]["FAKESCREEN"]["foo"], 2)
        os.remove(result_location)
