import unittest
import slac_db

class TestWrite(unittest.TestCase):
    def test_get_device(self):
        source_bpm = {
            "controls_information": {
                "PVs": {
                    "tmit": "BPMS:DIAG0:190:TMIT",
                    "x": "BPMS:DIAG0:190:X",
                    "y": "BPMS:DIAG0:190:Y",
                },
                "control_name": "BPMS:DIAG0:190",
            },
            "metadata": {
                "area": "DIAG0",
                "beam_path": ["SC_DIAG0"],
                "sum_l_meters": 46.232,
                "type": "BPM",
            },
        }
        test_bpm = slac_db.get_device("DIAG0", "bpms", "BPMDG001")
        self.assertEqual(test_bpm, source_bpm)
