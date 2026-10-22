import os

import pykern.sql_db
import sqlalchemy
import yaml
from pykern.pkcollections import PKDict

import slac_db.config

_meta = None


def get_areas(beampath=None):
    """Get all areas in a beampath.

    Args:
        beampath (str): Beampath name

    Out:
        list of areas (str) in alphabetical order.
    """
    with _session() as s:
        selection = (
            sqlalchemy.select(s.t.beampaths)
            .where(s.t.beampaths.c["beampath"] == beampath)
            .order_by(s.t.beampaths.c.area)
        )
        return [a["area"] for a in s.select(selection)]


def get_beampath(beampath=None, device_type=None, include_inactive=False):
    """Get all devices in a beampath, optionally by type.

    Args:
        beampath (str): Beampath name
        device_type (str) optional: Device type in Oracle
        include_inactive (bool) optional: If True, include inactive devices.
            Defaults to False (active devices only).

    Returns: List of devices in Z order.
    """
    with _session() as s:
        selection = (
            sqlalchemy.select(s.t.devices)
            .join(s.t.beampaths, s.t.beampaths.c.area == s.t.devices.c.area)
            .outerjoin(
                s.t.device_meta_float,
                (s.t.device_meta_float.c.device_name == s.t.devices.c.device_name)
                & (s.t.device_meta_float.c.device_meta_name == "sum_l_meters"),
            )
        )
        selection = selection.where(s.t.beampaths.c.beampath == beampath)
        if device_type is not None:
            selection = selection.where(s.t.devices.c.device_type == device_type)
        if not include_inactive:
            selection = selection.where(s.t.devices.c.is_active == True)
        selection.order_by(s.t.device_meta_float.c.meta_value)
        return [d["device_name"] for d in s.select(selection)]


def get_attribute(device_name, col_name):
    """Get a basic attribute for a given device.

    Args:
        device_name: MAD Device Name
        col_name: Device Database Column Name
    Returns:
        Attribute
    """
    with _session() as s:
        return s.select_one(
            sqlalchemy.select(s.t.devices).where(
                s.t.devices.c.device_name == device_name
            )
        )[col_name]


def get_devices(area=None, device_type=None, include_inactive=False):
    """Get all devices in an area of a type.

    Args:
        area (str) optional: Area name
        device_type (str) optional: Device type in Oracle
        include_inactive (bool) optional: If True, include inactive devices.
            Defaults to False (active devices only).

    Out:
        List of devices in alphabetical order.
    """
    with _session() as s:
        selection = sqlalchemy.select(s.t.devices).outerjoin(
            s.t.device_meta_float,
            (s.t.device_meta_float.c.device_name == s.t.devices.c.device_name)
            & (s.t.device_meta_float.c.device_meta_name == "sum_l_meters"),
        )
        if area is not None:
            selection = selection.where(s.t.devices.c["area"] == area)
        if device_type is not None:
            selection = selection.where(s.t.devices.c["device_type"] == device_type)
        if not include_inactive:
            selection = selection.where(s.t.devices.c["is_active"] == True)
        selection = selection.order_by(s.t.device_meta_float.c.meta_value)
        return [d["device_name"] for d in s.select(selection)]


def get_all_accessors(device):
    """Get all accessors from a device.
    An accessor is a developer friendly name for a PV
    associated with a single device.

    Args:
        device (str): MAD name for a device.
    """
    with _session() as s:
        return {
            r["accessor_name"]: r["cs_address"]
            for r in s.select(
                sqlalchemy.select(s.t.accessors)
                .where(s.t.accessors.c["device_name"] == device)
                .order_by(s.t.accessors.c.accessor_name)
            )
        }


def get_all_addresses(device):
    """Get all accessors from a device.
    An address is a PV.

    Args:
        device (str): MAD name for a device.
    """
    with _session() as s:
        return [
            r["cs_address"]
            for r in s.select(
                sqlalchemy.select(s.t.addresses)
                .where(s.t.addresses.c["device_name"] == device)
                .order_by(s.t.addresses.c.cs_address)
            )
        ]


def get_all_areas():
    """Gets all known areas.

    Returns:
        List of areas
    """
    with _session() as s:
        return [
            r["area"]
            for r in s.select(sqlalchemy.select(s.t.areas).order_by(s.t.areas.c.area))
        ]


def get_all_device_beampaths(device):
    """Gets all known beampaths.

    Returns:
        List of beampaths.
    """
    with _session() as s:
        return [
            r["beampath"]
            for r in s.select(
                sqlalchemy.select(s.t.beampaths)
                .join(s.t.devices, s.t.devices.c.area == s.t.beampaths.c.area)
                .where(s.t.devices.c.device_name == device)
                .order_by(s.t.devices.c.device_name)
            )
        ]


def get_all_meta(device_name):
    """Get a dictionary of all known metadata.

    Args:
        device_name: MAD Device Name

    Returns:
        (dict): Dict of all device meta.
    """

    def _fixup_string(val):
        if type(val) is str:
            val = yaml.safe_load(val)
        return val

    with _session() as s:
        meta = s.t.device_meta
        meta_float = s.t.device_meta_float
        meta_string = s.t.device_meta_string

        def _on(t):
            return sqlalchemy.and_(
                t.c.device_name == meta.c.device_name,
                t.c.device_meta_name == meta.c.device_meta_name,
            )

        return {
            r["device_meta_name"]: _fixup_string(r["meta_value"])
            for r in s.select(
                sqlalchemy.select(
                    meta.c.device_meta_name,
                    sqlalchemy.func.coalesce(
                        meta_float.c.meta_value, meta_string.c.meta_value
                    ).label("meta_value"),
                )
                .join(meta_float, _on(meta_float), isouter=True)
                .join(meta_string, _on(meta_string), isouter=True)
                .where(meta.c.device_name == device_name)
                .order_by(meta.c.device_meta_name)
            )
        }


def recreate(parser):
    """Rebuilds the device database.
    Fails if a connection has already been made.

    Args:
        Parser object with attribute 'device_address_meta' for row data.
    """
    if _meta:
        raise AssertionError(
            "Database connnection already initialized. " + "Restart Python interpreter."
        )
    if not hasattr(parser, "address_meta"):
        raise AssertionError("Parser is missing attribute 'device_address_meta'. ")
    if os.path.exists(_device_db_location()):
        os.remove(_device_db_location())
    _Inserter(parser)


class _Inserter:
    """Inserts rows into sqllite database."""

    def __init__(self, parser):
        with _session() as s:
            self._bulk_insert(
                s,
                PKDict(
                    areas=parser.areas,
                    beampaths=parser.area_map,
                    devices=parser.devices,
                    device_meta=parser.device_meta,
                    device_meta_float=parser.device_meta_float,
                    device_meta_string=parser.device_meta_string,
                    addresses=parser.address_meta,
                    accessors=parser.accessor_meta,
                ),
            )

    def _bulk_insert(self, s, table_map):
        s.execute(sqlalchemy.text("SELECT 1"))
        for name, rows in table_map.items():
            tab = s.t[name]
            s._conn.execute(tab.insert(), rows)


def _db_type_prefix(uri):
    if not uri.startswith("sqlite"):
        uri = "sqlite:///" + uri
    return uri


def _init_db(location=None):
    """Initializes pykern sqlalchemy wrapper. Initialization
    occurs when a session is first created.

       _meta: wrapper that holds sqlalchemy metadata.
    """
    global _meta
    if location is None:
        location = _device_db_location()
    uri = _db_type_prefix(location)
    schema = PKDict(
        areas=PKDict(
            area="str 64 primary_key",
        ),
        beampaths=PKDict(
            area="str 64 primary_key foreign",
            beampath="str 64 primary_key",
        ),
        devices=PKDict(
            device_name="str 64 primary_key",
            area="str 64 foreign",
            device_type="str 64",
            cs_name="str 64",
            is_active="bool nullable",
        ),
        device_meta=PKDict(
            device_name="str 64 primary_key foreign",
            device_meta_name="str 64 primary_key",
            meta_type="str 64",
        ),
        device_meta_float=PKDict(
            device_name="str 64 primary_key foreign",
            device_meta_name="str 64 primary_key",
            meta_value="float 64",
        ),
        device_meta_string=PKDict(
            device_name="str 64 primary_key foreign",
            device_meta_name="str 64 primary_key",
            meta_value="str 64",
        ),
        addresses=PKDict(
            device_name="str 64 primary_key foreign",
            cs_address="str 64 primary_key",
        ),
        accessors=PKDict(
            device_name="str 64 primary_key foreign",
            accessor_name="str 64 primary_key",
            cs_address="str 64",
        ),
    )
    _meta = pykern.sql_db.Meta(uri=uri, schema=schema)


def _device_db_location():
    db_location = slac_db.config.package_data().joinpath("device.sqlite3")
    return str(db_location)


def _session():
    if _meta is None:
        _init_db()
    return _meta.session()


# Device types considered when discovering modeled MAD elements.
_MODELED_DEVICE_TYPES = ["BEND", "BTRM", "QUAD", "XCOR", "YCOR", "LCAV"]

# cs_name prefixes whose DES values are amplitude + phase, not BDES.
_CAVITY_CS_PREFIXES = {"KLYS", "ACCL", "LCAV"}

# cs_name prefixes intentionally excluded from PV generation.
_EXCLUDED_DEVICE_TYPES = {"TCAV"}

# Mapping from beam path name to klystron beamcode.
_BEAM_PATH_BEAMCODE = {
    "CU_HXR": 1,
    "CU_SXR": 2,
}


def _klys_pvs(mad_name, beamcode):
    """Return (amplitude_pv, phase_pv) for a KLYS/ACCL device.

    Looks up the beamcode-specific DES accessors on the device,
    falling back to the plain amplitude/phase_desired entries if the
    beamcode-specific keys are absent. Either return slot may be None.

    Args:
        mad_name (str): MAD device name.
        beamcode (int): Klystron beamcode (e.g. 1 for CU_HXR).

    Returns:
        tuple[str | None, str | None]: (amplitude_pv, phase_pv)
    """
    acc = get_all_accessors(mad_name) or {}
    ampl_pv = (
        acc.get(f"amplitude_des_beamcode{beamcode}")
        or acc.get("amplitude")
    )
    phase_pv = (
        acc.get(f"phase_desired_beamcode{beamcode}")
        or acc.get("phase_desired")
    )
    return ampl_pv, phase_pv


def get_model_devices(
    device_types=None, beampath=None, regions=None, first=None, last=None
):
    """Return modeled MAD elements keyed by MAD name with DB attributes.

    Queries the device database for MAD model elements matching
    device_types in the areas implied by regions or beampath, sorts by
    longitudinal position (sum_l_meters), and returns a dict keyed by
    MAD element name. Each value carries cs_name and device_type;
    cavity-shaped entries (cs_name prefix in _CAVITY_CS_PREFIXES:
    KLYS, ACCL, LCAV) additionally carry amplitude_pv and phase_pv
    resolved against the beamcode implied by beampath. Elements whose
    cs_name prefix is in _EXCLUDED_DEVICE_TYPES (e.g. TCAV) are
    omitted.

    Args:
        device_types (list[str]) optional: Device type codes to
            include. Defaults to _MODELED_DEVICE_TYPES.
        beampath (str) optional: Beam path name (e.g. "CU_HXR") used
            both to look up areas when regions is not supplied and to
            resolve the klystron beamcode (CU_HXR -> 1, CU_SXR -> 2).
            Required if any cavity-shaped device is in the selection.
        regions (list[str]) optional: Area names to search; overrides
            beampath for area lookup.
        first (str) optional: MAD element bounding the slice start
            (inclusive).
        last (str) optional: MAD element bounding the slice end
            (inclusive).

    Returns:
        dict: mad_name -> {"cs_name", "device_type", ...}
            insertion-ordered by sum_l_meters. Cavity-shaped entries
            also carry "amplitude_pv" and "phase_pv".

    Raises:
        ValueError: If first/last are not found in the sorted list,
            or if a cavity-shaped device is selected without a
            beampath beamcode mapping.
    """
    if device_types is None:
        device_types = _MODELED_DEVICE_TYPES
    beamcode = (
        _BEAM_PATH_BEAMCODE.get(beampath.upper()) if beampath else None
    )
    areas = regions if regions else get_areas(beampath=beampath)
    mad_elements = []
    for area in areas:
        for dtype in device_types:
            found = get_devices(area=area, device_type=dtype)
            if found:
                mad_elements.extend(found)
    sorted_elements = sorted(
        mad_elements,
        key=lambda e: get_all_meta(e).get("sum_l_meters", 0),
    )

    if first is not None:
        try:
            first_idx = sorted_elements.index(first)
        except ValueError:
            raise ValueError(
                f"first={first!r} not found in modeled elements for "
                f"beampath={beampath!r}"
            )
    else:
        first_idx = 0

    if last is not None:
        try:
            last_idx = sorted_elements.index(last)
        except ValueError:
            raise ValueError(
                f"last={last!r} not found in modeled elements for "
                f"beampath={beampath!r}"
            )
    else:
        last_idx = len(sorted_elements) - 1

    if first_idx > last_idx:
        raise ValueError(
            f"first={first!r} appears after last={last!r} in modeled "
            f"elements for beampath={beampath!r}"
        )

    sliced = sorted_elements[first_idx:last_idx + 1]

    result = {}
    for e in sliced:
        cs_name = get_attribute(e, "cs_name")
        cs_prefix = cs_name.split(":")[0] if cs_name else ""
        if cs_prefix in _EXCLUDED_DEVICE_TYPES:
            continue
        entry = {
            "cs_name": cs_name,
            "device_type": get_attribute(e, "device_type"),
        }
        if cs_prefix in _CAVITY_CS_PREFIXES:
            if beamcode is None:
                raise ValueError(
                    f"beampath {beampath!r} is required / not supported "
                    f"for beamcode resolution on cavity-shaped device "
                    f"{e!r}. Supported: {list(_BEAM_PATH_BEAMCODE)}."
                )
            entry["amplitude_pv"], entry["phase_pv"] = _klys_pvs(e, beamcode)
        result[e] = entry
    return result
