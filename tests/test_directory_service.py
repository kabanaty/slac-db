import unittest
import slac_db.config
import slac_db.directory_service
import slac_db.io

class TestDirectoyrService(unittest.TestCase):
    def test_get_otrdg02_pvs(self):
        all_pvs = slac_db.directory_service.get_addresses(
            device="OTRDG02",
        )
        for a in all_pvs:
            assert a.startswith('OTRS:DIAG0:420')

    def test_pvs_exit(self):
        d = slac_db.io.read_dict(
            slac_db.config.yaml().joinpath('DIAG0.yaml')
        )

        otrdg02 = d['screens']['OTRDG02']['controls_information']['PVs']
        wsdg01 = d['wires']['WSDG01']['controls_information']['PVs']
        
        for p in otrdg02.values():
            slac_db.directory_service.verify_address(p)

        for p in wsdg01.values():
            slac_db.directory_service.verify_address(p)
