import os
import yaml
from typing import Union, Optional, Any, Dict
import slac_db.config

def get_beampath_areas(beampath):
    def flatten(nested_list):
        if nested_list == []:
            return nested_list
        if isinstance(nested_list[0], list):
            return _flatten(nested_list[0]) + _flatten(nested_list[1:])
        return nested_list[:1] + _flatten(nested_list[1:])
    beampath_definition_file = os.path.join(
        slac_db.package_data(), "beampaths.yaml"
    )
    beampath_definitions = {}
    areas = {}
    with open(beampath_definition_file, "r") as file:
        beampath_definitions = yaml.safe_load(file)
    try:
        areas_to_create = _flatten(beampath_definitions[beampath])
    except KeyError:
        raise KeyError(f"Beampath: {beampath} does not exist.")
    return areas

def get_yaml(
    area: str = None,
    beampath: Optional[str] = None,
) -> str:
    if area:
        filename = area + ".yaml"
    if beampath:
        filename = "beampaths.yaml"

    path = os.path.join(slac_db.config.yaml(), filename)
    if os.path.isfile(path):
        return os.path.abspath(path)
    else:
        raise FileNotFoundError(
            f"No such file {path}, please choose another area.",
        )

def get_device(
    area: str = None,
    device_type: str = None,
    name: str = None,
) -> Union[None, Dict[str, Any]]:
    if area:
        try:
            location = get_yaml(
                area=area,
            )
            with open(location, "r") as device_file:
                device_data = yaml.safe_load(device_file)
                if device_type:
                    if name:
                        return device_data[device_type][name]
                    return {device_type: device_data[device_type]}
                return device_data
        except FileNotFoundError:
            print(f"Could not find yaml file for area: {area}")
            return None
        except KeyError as ke:
            if ke.args[0] == device_type:
                print(f"Device type {device_type} not supported in {area}.")
                return None
            if ke.args[0] == name:
                print(
                    "No device of type: ",
                    device_type,
                    " with name ",
                    name,
                    " not in definition for ",
                    area,
                )
                return None

    else:
        print("Please provide a machine area to create a ", device_type, " from.")
        return None
