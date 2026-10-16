import pytest

import slac_db.db_to_yaml
import slac_db.write

_WRITER = slac_db.write.YAMLWriter(use_meme=False, suppress_warnings=True)
_DB_AREAS = slac_db.db_to_yaml.yaml_areas()


def _example(area):
    if area not in _WRITER.areas:
        return {}
    return _WRITER._construct_yaml_contents(area)


def _test(area):
    if area not in _DB_AREAS:
        return {}
    return dict(slac_db.db_to_yaml._build_types(area))


def _compare_devices(note, test_devices, example_devices):
    assert {note: sorted(test_devices.keys())} == {note: sorted(example_devices.keys())}
    for name in test_devices.keys():
        assert test_devices[name] == example_devices[name], f"Mismatch at {note + (name,)}"


@pytest.mark.parametrize("area", sorted(set(_WRITER.areas) | set(_DB_AREAS)))
def test_compare_yaml(area):
    test = _test(area)
    example = _example(area)
    assert {area: sorted(test.keys())} == {area: sorted(example.keys())}
    for device_type in test.keys():
        _compare_devices(
            (area, device_type),
            test[device_type],
            example[device_type],
        )
