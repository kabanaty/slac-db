import pytest
from slac_db.metadata import get_wire_metadata

WIRE_AREAS = {
    "WS01": "IN20",
    "WS02": "IN20",
    "WS03": "IN20",
    "WS04": "IN20",
    "WS11": "LI21",
    "WS12": "LI21",
    "WS13": "LI21",
    "WS24": "LI24",
    "WS27644": "LI28",
    "WS28144": "LI28",
    "WS28444": "LI28",
    "WS28744": "LI28",
    "WS0H04": "HTR",
    "WSDG01": "DIAG0",
    "WSC104": "COL1",
    "WSC106": "COL1",
    "WSC108": "COL1",
    "WSC110": "COL1",
    "WSEMIT2": "EMIT2",
    "WSBP1": "BYP",
    "WSBP2": "BYP",
    "WSBP3": "BYP",
    "WSBP4": "BYP",
    "WSSP1D": "SPS",
    "WS31": "LTUH",
    "WS32": "LTUH",
    "WS33": "LTUH",
    "WS34": "LTUH",
    "WS31B": "LTUS",
    "WS32B": "LTUS",
    "WS33B": "LTUS",
    "WS34B": "LTUS",
}


@pytest.fixture
def basic_wire_data():
    return {name: {"metadata": {"area": area}} for name, area in WIRE_AREAS.items()}


class TestGetWireMetadata:
    def test_loads_real_yaml(self, basic_wire_data):
        result = get_wire_metadata(basic_wire_data)
        assert "WS01" in result
        assert "WS31B" in result
        assert result["WS01"]["wire_type"] == "slow"
        assert result["WS01"]["detectors"] == [
            "PMTINJ03:DL1",
            "PMTINJ05:DL1",
            "PMT21350:LI21",
        ]

    def test_jitter_bpms_present(self, basic_wire_data):
        result = get_wire_metadata(basic_wire_data)
        assert result["WS01"]["jitter_bpms"] == [
            "BPM9",
            "BPM10",
            "BPM11",
            "BPM13",
            "BPM14",
        ]
        assert result["WS31B"]["jitter_bpms"] == [
            "BPMEM4B",
            "BPME33B",
            "BPME34B",
            "BPMUM1B",
        ]

    def test_per_wire_override_ws04(self, basic_wire_data):
        result = get_wire_metadata(basic_wire_data)
        assert result["WS04"]["default_detector"] == "PMTINJ05:DL1"
        assert result["WS01"]["default_detector"] == "PMTINJ03:DL1"

    def test_area_tmitloss_inherited(self, basic_wire_data):
        result = get_wire_metadata(basic_wire_data)
        assert result["WSBP1"]["tmitloss"] == result["WSBP2"]["tmitloss"]

    def test_filter_by_basic_wire_data(self):
        subset = {
            "WS01": {"metadata": {"area": "IN20"}},
            "WS02": {"metadata": {"area": "IN20"}},
        }
        result = get_wire_metadata(subset)
        assert set(result.keys()) == {"WS01", "WS02"}

    def test_total_wire_count(self, basic_wire_data):
        result = get_wire_metadata(basic_wire_data)
        assert len(result) == 32
