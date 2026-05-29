import pytest
from slac_db.metadata import _flatten_area_metadata, get_wire_metadata


class TestFlattenAreaMetadata:
    def test_basic_inheritance(self):
        raw = {
            "schema_version": 2,
            "areas": {
                "LI21": {
                    "detectors": ["PMT_A", "PMT_B"],
                    "default_detector": "PMT_A",
                    "jitter_bpms": ["BPM1", "BPM2"],
                    "wires": {
                        "WS11": {"wire_type": "fast"},
                        "WS12": {"wire_type": "fast"},
                    },
                }
            },
        }
        result = _flatten_area_metadata(raw)
        assert result["WS11"]["detectors"] == ["PMT_A", "PMT_B"]
        assert result["WS11"]["jitter_bpms"] == ["BPM1", "BPM2"]
        assert result["WS11"]["default_detector"] == "PMT_A"
        assert result["WS11"]["wire_type"] == "fast"
        assert result["WS12"]["detectors"] == ["PMT_A", "PMT_B"]

    def test_per_wire_override(self):
        raw = {
            "schema_version": 2,
            "areas": {
                "IN20": {
                    "default_detector": "PMT_A",
                    "detectors": ["PMT_A", "PMT_B"],
                    "wires": {
                        "WS01": {"wire_type": "slow"},
                        "WS04": {"wire_type": "slow", "default_detector": "PMT_B"},
                    },
                }
            },
        }
        result = _flatten_area_metadata(raw)
        assert result["WS01"]["default_detector"] == "PMT_A"
        assert result["WS04"]["default_detector"] == "PMT_B"

    def test_override_does_not_mutate_other_wires(self):
        raw = {
            "schema_version": 2,
            "areas": {
                "TEST": {
                    "tmitloss": {"upstream": ["A"], "downstream": ["B"]},
                    "wires": {
                        "W1": {"tmitloss": {"upstream": ["X"], "downstream": ["Y"]}},
                        "W2": {},
                    },
                }
            },
        }
        result = _flatten_area_metadata(raw)
        assert result["W1"]["tmitloss"]["upstream"] == ["X"]
        assert result["W2"]["tmitloss"]["upstream"] == ["A"]

    def test_duplicate_wire_raises(self):
        raw = {
            "schema_version": 2,
            "areas": {
                "A": {"wires": {"WS01": {}}},
                "B": {"wires": {"WS01": {}}},
            },
        }
        with pytest.raises(ValueError, match="multiple areas"):
            _flatten_area_metadata(raw)

    def test_empty_wire_overrides(self):
        raw = {
            "schema_version": 2,
            "areas": {
                "TEST": {
                    "detectors": ["DET1"],
                    "wires": {
                        "W1": None,
                        "W2": {},
                    },
                }
            },
        }
        result = _flatten_area_metadata(raw)
        assert result["W1"]["detectors"] == ["DET1"]
        assert result["W2"]["detectors"] == ["DET1"]

    def test_jitter_bpms_propagated(self):
        raw = {
            "schema_version": 2,
            "areas": {
                "LTUS": {
                    "jitter_bpms": ["BPMEM4B", "BPME33B"],
                    "wires": {
                        "WS31B": {"wire_type": "fast"},
                        "WS32B": {"wire_type": "fast"},
                    },
                }
            },
        }
        result = _flatten_area_metadata(raw)
        assert result["WS31B"]["jitter_bpms"] == ["BPMEM4B", "BPME33B"]
        assert result["WS32B"]["jitter_bpms"] == ["BPMEM4B", "BPME33B"]

    def test_area_without_jitter_bpms(self):
        raw = {
            "schema_version": 2,
            "areas": {
                "HTR": {
                    "detectors": ["LBLM01A:HTR"],
                    "wires": {
                        "WS0H04": {"wire_type": "fast"},
                    },
                }
            },
        }
        result = _flatten_area_metadata(raw)
        assert "jitter_bpms" not in result["WS0H04"]


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

    def test_per_wire_override_wsbp1_tmitloss(self):
        result = get_wire_metadata()
        assert "BPMS:DOG:215" in result["WSBP1"]["tmitloss"]["upstream"]
        assert "BPMDOG7" in result["WSBP2"]["tmitloss"]["upstream"]
        assert "BPMS:DOG:215" not in result["WSBP2"]["tmitloss"]["upstream"]

    def test_filter_by_wire_names(self):
        result = get_wire_metadata(wire_names=["WS01", "WS02"])
        assert set(result.keys()) == {"WS01", "WS02"}

    def test_total_wire_count(self):
        result = get_wire_metadata()
        assert len(result) == 32
