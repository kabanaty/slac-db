import itertools

import yaml
from pykern.pkcollections import PKDict

import slac_db.config
import slac_db.device
import slac_db.directory_service
import slac_db.element_tables
import slac_db.io

_ACCESSOR_YAML = slac_db.config.package_data().joinpath("accessor_names.yaml")
_DELIM = ":"
_MAGNET_META = (("effective length (m)", "l_eff"),)
DEFAULT_DEVICE_META = (("suml (m)", "sum_l_meters"),)
DEVICE_META_MAP = PKDict(
    SOLE=_MAGNET_META,
    QUAD=_MAGNET_META,
    XCOR=_MAGNET_META,
    YCOR=_MAGNET_META,
    BEND=_MAGNET_META,
    LCAV=(
        ("effective length (m)", "l_eff"),
        ("rf frequency (mhz)", "rf_freq"),
    ),
)


def to_device_db():
    """Recreate device db."""
    slac_db.device.recreate(_Parser())


class _Parser:
    """Builds the rows for each device db table.

    Each table is assigned once, from all included element rows.
    """

    def __init__(self):
        area_yaml, device_yaml = _read_metadata_yaml()
        self.accessor_map = PKDict(slac_db.io.read_dict(_ACCESSOR_YAML))
        self.accessor_overrides = self.accessor_map.pop("_overrides", PKDict())
        rows = [
            (r, d) for r in slac_db.element_tables.get_all_rows() if (d := _device(r))
        ]

        self.devices = [d for _, d in rows]
        self.areas = [PKDict(area=a) for a in sorted({r["area"] for r, _ in rows})]
        self.area_map = [
            PKDict(area=a, beampath=b)
            for a, b in sorted({(r["area"], b) for r, _ in rows for b in _beampaths(r)})
        ]
        self.device_meta_float = _flatten(_device_meta_float(r) for r, _ in rows)
        self.device_meta_string = _flatten(
            _device_meta_string(r, area_yaml, device_yaml) for r, _ in rows
        )
        self.device_meta = _meta_entries(
            self.device_meta_float, "float"
        ) + _meta_entries(self.device_meta_string, "string")
        _assert_unique_meta(self.device_meta)
        # Directory service lookups dominate parse time; do them once per device.
        addresses = [
            (r, a)
            for r, _ in rows
            if (a := slac_db.directory_service.get_addresses(r["element"])) is not None
        ]
        self.address_meta = _flatten(_address_meta(r, a) for r, a in addresses)
        self.accessor_meta = _flatten(self._accessor_meta(r, a) for r, a in addresses)

    def _accessor_meta(self, row, addresses):
        """Combine accessor names with device names and addresses.

        Overrides replace the address of a matching accessor; overrides
        without a match are added as accessors of their own.
        """

        def _get_accessors(d_type, address):
            if not (device_map := self.accessor_map.get(d_type, None)):
                return
            if not (accessor := device_map.get(address, None)):
                return
            if f"_{address}_attributes" in device_map:
                attribute_map = device_map[f"_{address}_attributes"]
                yield from [
                    (".".join([address, attr]), a) for attr, a in attribute_map.items()
                ]
            if accessor is not None:
                yield (address, accessor)

        def _build_accessors(device, d_type, pv_head, override):
            for pv in addresses:
                pv_tail = pv[len(pv_head) + 1 :]
                for address, accessor in _get_accessors(d_type, pv_tail):
                    yield PKDict(
                        device_name=device,
                        cs_address=override.get(
                            accessor, _DELIM.join([pv_head, address])
                        ),
                        accessor_name=accessor,
                    )

        def _build_overrides(device, override, matched):
            for accessor_name, cs_address in override.items():
                if cs_address and accessor_name not in matched:
                    yield PKDict(
                        device_name=device,
                        cs_address=cs_address,
                        accessor_name=accessor_name,
                    )

        device = row["element"]
        cs_name = row["control system name"] or ""
        # Klystron stations share keyword=LCAV with TCAVs but need
        # their own keyword.
        d_type = "KLYS" if "KLYS" in cs_name else row["keyword"]
        override = self.accessor_overrides.get(device, PKDict())
        rv = list(_build_accessors(device, d_type, cs_name, override))
        matched = {a.accessor_name for a in rv}
        return rv + list(_build_overrides(device, override, matched))


def _address_meta(row, addresses):
    """Rows connecting a device name to each of its addresses."""
    return [PKDict(device_name=row["element"], cs_address=c) for c in addresses]


def _assert_unique_meta(device_meta):
    seen = set()
    for m in device_meta:
        e = (m.device_name, m.device_meta_name)
        if e in seen:
            raise ValueError(f"Conflicting Meta name entries {e}")
        seen.add(e)


def _beampaths(row):
    """Beampaths an element row belongs to."""
    if row["beampath"] is None:
        return []
    return list(filter(None, row["beampath"].replace(" ", "").split(",")))


def _device(row):
    """The devices row for an element row, or None if it is excluded."""
    entry = PKDict(
        device_name=row["element"],
        area=row["area"],
        device_type=row["keyword"],
        cs_name=row["control system name"],
    )
    if not all(entry.values()):
        return None
    if ":" in row["element"]:
        return None
    entry.is_active = row["active"] == "A" if row["active"] is not None else None
    return entry


def _device_meta_float(row):
    meta = DEVICE_META_MAP.get(row["keyword"], ()) + DEFAULT_DEVICE_META
    for column, meta_name in meta:
        entry = PKDict(
            device_name=row["element"],
            device_meta_name=meta_name,
            meta_value=row[column],
        )
        if None in entry.values():
            continue
        yield entry


def _device_meta_string(row, area_yaml, device_yaml):
    name = row["element"]
    area_meta = area_yaml.get(row["yaml_type"], PKDict())
    meta = area_meta.get(row["area"], PKDict()) | device_yaml.get(name, PKDict())
    for meta_name, value in meta.items():
        entry = PKDict(
            device_name=name,
            device_meta_name=meta_name,
            meta_value=yaml.safe_dump(value),
        )
        if None in entry.values():
            continue
        yield entry


def _flatten(iterables):
    return list(itertools.chain.from_iterable(iterables))


def _meta_entries(meta, meta_type):
    """device_meta rows recording the type of each meta value."""
    return [
        PKDict(
            device_name=m.device_name,
            device_meta_name=m.device_meta_name,
            meta_type=meta_type,
        )
        for m in meta
    ]


def _read_metadata_yaml():
    """Returns (area_yaml, device_yaml) from the package metadata files."""
    area_yaml = PKDict()
    device_yaml = PKDict()
    for f in slac_db.config.package_data().glob("*_metadata.yaml"):
        if f.name.endswith("_area_metadata.yaml"):
            area_yaml[f.name[: -len("_area_metadata.yaml")]] = slac_db.io.read_dict(f)
        else:
            device_yaml.update(slac_db.io.read_dict(f))
    return area_yaml, device_yaml
