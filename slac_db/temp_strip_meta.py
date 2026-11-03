import yaml

import slac_db.io
import slac_db.config


def strip_unit(meta):
    del meta["unit"]
    return meta


def fix_meta(entry):
    for cs_suffix, meta in entry.items():
        if isinstance(meta, str):
            meta = {"cs_address": meta, "py_type": "float"}
            yield cs_suffix, meta
        elif "name" not in meta:
            meta = dict(fix_meta(meta))
        elif "attributes" in meta:
            meta["attributes"] = dict(fix_meta(meta["attributes"]))
        else:
            meta = strip_unit(meta)
        yield cs_suffix, meta


d = {
    dtype: dict(fix_meta(accessors))
    for dtype, accessors in slac_db.io.read_dict("./accessor_meta.yaml").items()
}

with open("./accessor_names.yaml", "w") as w:
    w.write(yaml.dump(d))
