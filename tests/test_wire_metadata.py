from slac_db.metadata import get_wire_metadata


class TestGetWireMetadata:
    def test_loads_real_yaml(self):
        result = get_wire_metadata()
        assert "WS01" in result
        assert "WS31B" in result
        assert result["WS01"]["wire_type"] == "slow"
        assert result["WS01"]["detectors"] == [
            "PMTINJ03:DL1",
            "PMTINJ05:DL1",
            "PMT21350:LI21",
        ]

    def test_jitter_bpms_present(self):
        result = get_wire_metadata()
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

    def test_per_wire_override_ws04(self):
        result = get_wire_metadata()
        assert result["WS04"]["default_detector"] == "PMTINJ05:DL1"
        assert result["WS01"]["default_detector"] == "PMTINJ03:DL1"

    def test_area_tmitloss_inherited(self):
        result = get_wire_metadata()
        assert result["WSBP1"]["tmitloss"] == result["WSBP2"]["tmitloss"]

    def test_filter_by_wire_names(self):
        result = get_wire_metadata(wire_names=["WS01", "WS02"])
        assert set(result.keys()) == {"WS01", "WS02"}

    def test_total_wire_count(self):
        result = get_wire_metadata()
        assert len(result) == 32
