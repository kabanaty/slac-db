import slac_db.config
import slac_db.write
import yaml
import os
from pathlib import Path
import unittest

class TestCompareToLCLSTools(unittest.TestCase):
    def setUp(self):
        self.data_location = (
            Path(__file__).parent / "test_data"
        )
        self.maxDiff = None

    def test_against_lcls_tools(self):
        def get_files(p):
            return [f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f))]
        def compare_files(test, original):
            with open(test, "r") as t, open(original, "r") as o:
                test_dict = yaml.safe_load(t)
                original_dict = yaml.safe_load(o)
            self.assertEqual(test_dict, original_dict)

        slac_db_yaml_loc = slac_db.config.yaml()
        lcls_tools_yaml_loc = (
            Path(__file__).parent / "test_data" / "lcls-tools-yaml"
        )
        slac_yamls = get_files(slac_db_yaml_loc)
        lcls_yamls = get_files(lcls_tools_yaml_loc)
        for s in slac_yamls:
            compare_files(slac_db_yaml_loc / s, lcls_tools_yaml_loc / s)
