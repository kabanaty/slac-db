import deepdiff
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


@pytest.mark.parametrize("area", sorted(set(_WRITER.areas) | set(_DB_AREAS)))
def test_compare_yaml(area):
    # "added" means present in db_to_yaml but not YAMLWriter; "removed" the reverse.
    diff = deepdiff.DeepDiff(_example(area), _test(area))
    if diff:
        pytest.fail(f"{area}: YAMLWriter -> db_to_yaml\n{diff.pretty()}", pytrace=False)
