import os
import slac_db
import slac_db.config
import slac_db.db_to_yaml
import unittest
import unittest.util
import yaml


class test_db_to_yaml(unittest.TestCase):
    def test_compare_yaml(self):
        unittest.util._MAX_LENGTH = 2000
        self.maxDiff = None

        def compare_devices(area, test_devices, example_devices):
            self.assertEqual(
                {area: sorted(test_devices.keys())},
                {area: sorted(example_devices.keys())},
            )
            for device_type, device in example_devices.items():
                for name, meta in device.items():
                    if "pv_cache" in meta["controls_information"]:
                        del meta["controls_information"]["pv_cache"]
                    if "hardware" in meta["metadata"]:
                        del meta["metadata"]["hardware"]
                    if "tmitloss" in meta["metadata"]:
                        del meta["metadata"]["tmitloss"]
                    if "detectors" in meta["metadata"]:
                        meta["metadata"]["detectors"] = [
                            d
                            for d in meta["metadata"]["detectors"]
                            if not d.startswith("TMITLOSS")
                        ]
                    test_entry = test_devices[device_type][name]
                    if "detectors" in test_entry.get("metadata", {}):
                        test_entry["metadata"]["detectors"] = [
                            d
                            for d in test_entry["metadata"]["detectors"]
                            if not d.startswith("TMITLOSS")
                        ]
                    self.assertEqual(
                        {(area, name): meta},
                        {(area, name): test_entry},
                    )

        def get_yaml_area(location):
            with open(location, "r") as area_file:
                return yaml.safe_load(area_file)

        test = slac_db.db_to_yaml.build()
        yaml_areas = sorted([area[:-5] for area in os.listdir(slac_db.config.yaml())])
        db_areas = sorted([k for k in test.keys()])
        self.assertEqual(yaml_areas, db_areas)

        for area in db_areas:
            compare_devices(
                area,
                test[area],
                get_yaml_area(slac_db.get_yaml(area=area)),
            )
