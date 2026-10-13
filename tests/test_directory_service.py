import unittest
import slac_db.directory_service

class TestDirectoryService(unittest.TestCase):
    def test_get_otrdg02_pvs(self):
        all_pvs = slac_db.directory_service.get_addresses(
            device="OTRDG02",
        )
        for a in all_pvs:
            assert a.startswith('OTRS:DIAG0:420')
        assert 'OTRS:DIAG0:420:RESOLUTION' in all_pvs
