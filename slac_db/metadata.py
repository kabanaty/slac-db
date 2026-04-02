import re
from typing import List, Union, Any
from epics import caget
import os
import slac_db.config
import yaml


def _flatten(nested_list: List[Any]) -> List[Any]:
    if nested_list == []:
        return nested_list
    if isinstance(nested_list[0], list):
        return _flatten(nested_list[0]) + _flatten(nested_list[1:])
    return nested_list[:1] + _flatten(nested_list[1:])


def _get_area_to_beampaths() -> dict:
    here = slac_db.config.package_data()
    yaml_path = os.path.join(here, "beampaths.yaml")

    with open(yaml_path, "r") as f:
        beampath_definitions = yaml.safe_load(f)

    area_to_beampaths = {}
    for beampath, areas in beampath_definitions.items():
        flat_areas = _flatten(areas)
        for area in flat_areas:
            area_to_beampaths.setdefault(area, []).append(beampath)

    return area_to_beampaths


def _get_beampaths_from_area(area: Union[str, List[str], None]) -> List[str]:
    if area is None:
        return []

    areas = [area] if isinstance(area, str) else area
    area_to_beampaths = _get_area_to_beampaths()

    beampaths = []
    for item in areas:
        for beampath in area_to_beampaths.get(item, []):
            if beampath not in beampaths:
                beampaths.append(beampath)

    return beampaths


def get_magnet_metadata(
    magnet_names: List[str] = [], method: callable = None, **kwargs
):
    # return a data structure of the form:
    # {z
    #  mag-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  mag-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if magnet_names and method:
        # Add any additional metadata fields here
        additional_fields = ["Element", "Effective Length (m)"]
        device_elements = method(magnet_names, additional_fields)
        # change field names and values to be in different format
        # if needed
        for magnet in device_elements:
            if "Effective Length (m)" in device_elements[magnet]:
                if device_elements[magnet]["Effective Length (m)"] == "":
                    device_elements[magnet]["Effective Length (m)"] = 0.0
                device_elements[magnet]["l_eff"] = round(
                    float(device_elements[magnet]["Effective Length (m)"]), 3
                )
                del device_elements[magnet]["Effective Length (m)"]
        return device_elements
    else:
        return {}


def get_screen_metadata(basic_screen_data: dict):
    # return a data structure of the form:
    # {
    #  scr-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  scr-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    from meme.names import list_pvs

    metadata = {}
    for mad_name, info in basic_screen_data.items():
        metadata[mad_name] = {}
        ctrl_name = info["controls_information"]["control_name"]
        flags = list_pvs(ctrl_name + "%INSTALLED")
        hardware = {}
        for i in flags:
            name = re.search("(?<=^" + ctrl_name + ":).*(?=INSTALLED)", i)
            if name is None:
                continue
            name = name.group(0)
            status = caget(i)
            if status is not None:
                hardware[name] = status

        metadata[mad_name]["hardware"] = hardware
    return metadata


def get_wire_metadata(
    wire_names: List[str] = [], area: Union[str, List[str], None] = None
):
    # return a data structure of the form:
    # {
    #  wire-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  wire-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    wire_metadata = {}

    here = slac_db.config.package_data()
    yaml_path = os.path.join(here, "wire_metadata.yaml")

    with open(yaml_path, "r") as f:
        wire_metadata = yaml.safe_load(f)

    if not wire_names:
        return wire_metadata

    beampath_metadata = _get_beampaths_from_area(area)
    result = {}
    for wire_name in wire_names:
        result[wire_name] = dict(wire_metadata.get(wire_name, {}))
        result[wire_name]["beampath"] = beampath_metadata

    return result


def get_lblm_metadata(
    lblm_names: List[str] = [], area: Union[str, List[str], None] = None
):
    # return a data structure of the form:
    # {
    #  lblm-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  lblm-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    metadata = {}
    beampath_metadata = _get_beampaths_from_area(area)
    for lblm_name in lblm_names:
        metadata[lblm_name] = {"beampath": beampath_metadata}
    return metadata


def get_bpm_metadata(
    bpm_names: List[str] = [], area: Union[str, List[str], None] = None
):
    # return a data structure of the form:
    # {
    #  bpm-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  bpm-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    metadata = {}
    beampath_metadata = _get_beampaths_from_area(area)
    for bpm_name in bpm_names:
        metadata[bpm_name] = {"beampath": beampath_metadata}
    return metadata


def get_tcav_metadata(tcav_names: List[str] = [], method: callable = None, **kwargs):
    # return a data structure of the form:
    # {
    #  tcav-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  tcav-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if tcav_names and method:
        # Add any additional metadata fields here
        additional_fields = [
            "Element",
            "Effective Length (m)",
            "Rf Frequency (MHz)",
        ]
        device_elements = method(tcav_names, additional_fields)
        # change field names and values to be in different format
        # if needed
        for tcav in device_elements:
            if "Effective Length (m)" in device_elements[tcav]:
                if device_elements[tcav]["Effective Length (m)"] == "":
                    device_elements[tcav]["Effective Length (m)"] = 0.0
                device_elements[tcav]["l_eff"] = round(
                    float(device_elements[tcav]["Effective Length (m)"]), 3
                )
                del device_elements[tcav]["Effective Length (m)"]

            if "Rf Frequency (MHz)" in device_elements[tcav]:
                if device_elements[tcav]["Rf Frequency (MHz)"] == "":
                    device_elements[tcav]["Rf Frequency (MHz)"] = 0.0
                device_elements[tcav]["rf_freq"] = float(
                    device_elements[tcav]["Rf Frequency (MHz)"]
                )
                del device_elements[tcav]["Rf Frequency (MHz)"]

        return device_elements
    else:
        return {}


def get_pmt_metadata(
    pmt_names: List[str] = [], area: Union[str, List[str], None] = None
):
    # return a data structure of the form:
    # {
    #  bpm-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  bpm-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    metadata = {}
    beampath_metadata = _get_beampaths_from_area(area)
    for pmt_name in pmt_names:
        metadata[pmt_name] = {"beampath": beampath_metadata}
    return metadata
