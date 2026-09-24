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
        value = slac_db.device.get_devices(area="DIAG0", device_type="PROF")
        expected = ["OTRDG02", "OTRDG04"]
        self.assertEqual(value, expected)

    def test_is_active_attribute(self):
        """Active devices have is_active=True, inactive have is_active=False."""
        # OTRDG02 is an active screen in DIAG0
        self.assertTrue(slac_db.device.get_attribute("OTRDG02", "is_active"))
        # BLRDG0T is an inactive TRIM in DIAG0
        self.assertFalse(slac_db.device.get_attribute("BLRDG0T", "is_active"))

    def test_get_devices_exclude_inactive(self):
        """By default inactive devices are excluded."""
        all_devices = slac_db.device.get_devices(area="DIAG0", device_type="TRIM", include_inactive=True)
        active_devices = slac_db.device.get_devices(area="DIAG0", device_type="TRIM")
        self.assertIn("BLRDG0T", all_devices)
        self.assertNotIn("BLRDG0T", active_devices)
        self.assertTrue(len(active_devices) < len(all_devices))

    def test_get_beampath_exclude_inactive(self):
        """By default inactive devices are excluded; include_inactive=True brings them back."""
        active_lcav = slac_db.device.get_beampath(beampath="CU_HXR", device_type="LCAV")
        all_lcav = slac_db.device.get_beampath(beampath="CU_HXR", device_type="LCAV", include_inactive=True)
        # active results must be a strict subset
        self.assertTrue(set(active_lcav).issubset(set(all_lcav)))
        # L0A___ is the known inactive element — excluded by default, present with flag
        self.assertNotIn("L0A___", active_lcav)
        self.assertIn("L0A___", all_lcav)
