import slac_db.db_to_yaml
import slac_db.write
import yaml


def test_compare_yaml():

    def build_example():
        w = slac_db.write.YAMLWriter(use_meme=False, suppress_warnings=True)
        for area in w.areas:
            c = w._construct_yaml_contents(area)
            if c == {}:
                continue
            yield (area, c)

    def compare_devices(note, test_devices, example_devices):
        assert {note: sorted(test_devices.keys())} == {note: sorted(example_devices.keys())}
        for name in test_devices.keys():
            assert test_devices[name] == example_devices[name], f"Mismatch at {note + (name,)}"
    
    def compare_types(area, test_devices, example_devices):
        assert {area: sorted(test_devices.keys())} == {area: sorted(example_devices.keys())}
        for device_type in test_devices.keys():
            compare_devices(
                (area, device_type),
                test_devices[device_type],
                example_devices[device_type],
            )

    example = dict(build_example())
    test = slac_db.db_to_yaml.build()
    yaml_areas = sorted([k for k in example.keys()])
    db_areas = sorted([k for k in test.keys()])
    assert yaml_areas == db_areas
    for area in db_areas:
        compare_types(
            area,
            test[area],
            example[area]
        )
