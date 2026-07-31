import slac_db.device
import slac_db.oracle
import slac_db.create.combined

_ORACLE_TO_YAML_TYPE_MAP = {
    "SOLE": "magnets",
    "QUAD": "magnets",
    "XCOR": "magnets",
    "YCOR": "magnets",
    "BEND": "magnets",
    "PROF": "screens",
    "WIRE": "wires",
    "LBLM": "lblms",
    "BPM": "bpms",
    "LCAV": "tcavs",
    "INST": "pmts",
    "IMON": "toroids",
}


def _build_metadata(device_name):
    """Generate Metadata field for a YAML device.

    Args:
        device_name (str): MAD Name of Device

    Returns:
        rv (dict): Device Metadata
    """

    def parse_beampaths(beampath_csv):
        if beampath_csv is None:
            return []
        beampaths = beampath_csv.replace(" ", "").split(",")
        beampaths = filter(None, beampaths)
        yield from beampaths

    def _round_values(meta):
        for i, v in meta.items():
            if type(v) is float:
                meta[i] = round(v, 3)
        return meta

    beampath_csv = slac_db.oracle.get_device_row(device_name)["beampath"]
    rv = {
        "area": slac_db.device.get_attribute(device_name, "area"),
        "beam_path": list(parse_beampaths(beampath_csv)),
        "type": slac_db.device.get_attribute(device_name, "device_type"),
    }
    rv.update(_round_values(slac_db.device.get_all_meta(device_name)))
    expected_meta = slac_db.create.combined._DEVICE_META_MAP.get(
        slac_db.device.get_attribute(device_name, "device_type"), []
    )
    for m in expected_meta + slac_db.create.combined._DEFAULT_DEVICE_META:
        if m[1] not in rv:
            if m[1] == "l_eff" or m[1] == "rf_freq":
                rv.update({m[1]: 0.0})
            else:
                rv.update({m[1]: None})
    return rv


def _build_controls_information(device_name):
    """Returns controls information in YAML Device Format.

    Args:
        device_name (str): MAD Device Name
    """
    return {
        "PVs": slac_db.device.get_all_accessors(device_name),
        "control_name": slac_db.device.get_attribute(device_name, "cs_name"),
    }


def _build_devices(area, device_type):
    """Generator for all devices of a given type in a given area.

    Args:
        area (str): Area Name
        device_type (str): Oracle Device Type
    """
    devices = slac_db.device.get_devices(area=area, device_type=device_type)
    for d in devices:
        if device_type == "INST" and not d.startswith("PMT"):
            continue
        if device_type == "LCAV":
            r = slac_db.oracle.get_device_row(d)
            if r["engineering name"] != "TRANS_DEFL":
                continue
        cs = _build_controls_information(d)
        meta = _build_metadata(d)
        yield (
            d,
            {
                "controls_information": cs,
                "metadata": meta,
            },
        )


def _build_types(area):
    """Generator for all devices in an area sorted by type.

    Args:
        area (str): Area Name
    """
    all_types = {}
    for oracle, yaml in _ORACLE_TO_YAML_TYPE_MAP.items():
        d = {name: data for name, data in _build_devices(area, oracle)}
        if not d:
            continue
        if yaml not in all_types:
            all_types[yaml] = d
        else:
            all_types[yaml].update(d)
        yield yaml, all_types[yaml]


def _build_areas(areas):
    """Generator for all devices in a given area

    Args:
        area (list): List of Area Names
    """
    for a in areas:
        yv = {t: d for t, d in _build_types(a)}
        if not yv:
            continue
        yield a, yv


def get_device(device_name):
    """Returns the expected device dict for a given device.

    Args:
        device_name (str): MAD Device Name

    Returns:
        (dict): YAML Device Dictionary
    """
    device_dict = {
        "name": device_name,
        "controls_information": _build_controls_information(device_name),
        "metadata": _build_metadata(device_name),
    }
    device_dict["yaml_type"] = _ORACLE_TO_YAML_TYPE_MAP.get(
        device_dict["metadata"]["type"], None
    )
    if device_dict["yaml_type"] is None:
        return None
    return device_dict


def build():
    """Returns the expected device dict for a given device.

    Args:
        device_name (str): MAD Device Name

    Returns:
        (dict): YAML Device Dictionary
    """

    def _parse_areas():
        areas = slac_db.device.get_all_areas()
        for a in areas:
            if " " in a or "*" in a:
                continue
            yield a

    areas = list(_parse_areas())
    out = {a: d for a, d in _build_areas(areas)}
    return out
