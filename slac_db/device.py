import os
from pykern.pkdebug import pkdlog
import pykern.sql_db
from pykern.pkcollections import PKDict
import slac_db.config
import sqlalchemy
import yaml

_meta = None

def get_areas(beampath=None):
    """ Get all areas in a beampath.

    Args:
        beampath (str): Beampath name

    Out:
        list of areas (str) in alphabetical order.
    """
    with _session() as s:
        selection = (
            sqlalchemy.select(
                s.t.beampaths
            ).where(
                s.t.beampaths.c["beampath"] == beampath
            ).order_by(
                s.t.beampaths.c.area
            )
        )
        return [a["area"] for a in s.select(selection)]

def get_beampath(beampath=None, device_type=None, include_inactive=False):
    """ Get all devices in a beampath, optionally by type.

    Args:
        beampath (str): Beampath name
        device_type (str) optional: Device type in Oracle
        include_inactive (bool) optional: If True, include inactive devices.
            Defaults to False (active devices only).

    Returns: List of devices in Z order.
    """
    with _session() as s:
        selection = sqlalchemy.select(
            s.t.devices
        ).join(
            s.t.beampaths,
            s.t.beampaths.c.area == s.t.devices.c.area
        ).join(
            s.t.device_meta_float,
            s.t.device_meta_float.c.device_name == s.t.devices.c.device_name
        )
        selection = selection.where(s.t.beampaths.c.beampath == beampath)
        if device_type is not None:
            selection = selection.where(s.t.devices.c.device_type == device_type)
        if not include_inactive:
            selection = selection.where(s.t.devices.c.is_active == True)
        selection = selection.where(s.t.device_meta_float.c.device_meta_name == 'sum_l_meters')
        selection.order_by(s.t.device_meta_float.c.meta_value)
        selection.where(s.t.device_meta_float.c.device_meta_name == 'sum_l_meters')
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
            sqlalchemy.select(
                s.t.devices
            ).where(
                s.t.devices.c.device_name == device_name
            )
        )[col_name]

def get_devices(area=None, device_type=None, include_inactive=False):
    """ Get all devices in an area of a type.

    Args:
        area (str) optional: Area name
        device_type (str) optional: Device type in Oracle
        include_inactive (bool) optional: If True, include inactive devices.
            Defaults to False (active devices only).

    Out:
        List of devices in alphabetical order.
    """
    with _session() as s:
        selection = sqlalchemy.select(
            s.t.devices
        ).outerjoin(
            s.t.device_meta_float,
            (s.t.device_meta_float.c.device_name == s.t.devices.c.device_name)
          & (s.t.device_meta_float.c.device_meta_name == 'sum_l_meters')
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
                sqlalchemy.select(
                    s.t.accessors
                ).where(
                    s.t.accessors.c["device_name"] == device
                ).order_by(
                    s.t.accessors.c.accessor_name
                )
            )
        }

def get_all_addresses(device):
    """Get all accessors from a device.
    An address is a PV.

    Args:
        device (str): MAD name for a device.
    """
    with _session() as s:
        return [r["cs_address"] for r in s.select(
            sqlalchemy.select(
                s.t.addresses
            ).where(
                s.t.addresses.c["device_name"] == device
            ).order_by(
                s.t.address.c.cs_address
            )
        )]

def get_all_areas():
    """Gets all known areas.

    Returns:
        List of areas
    """
    with _session() as s:
        return [
            r["area"] for r in s.select(
                sqlalchemy.select(
                    s.t.areas
                ).order_by(
                    s.t.areas.c.area
                )
            )
        ]

def get_all_device_beampaths(device):
    """Gets all known beampaths.

    Returns:
        List of beampaths.
    """
    with _session() as s:
        return [r["beampath"] for r in s.select(
            sqlalchemy.select(
                s.t.beampaths
            ).join(
                s.t.devices,
                s.t.devices.c.area == s.t.beampaths.c.area
            ).where(
                s.t.devices.c.device_name == device
            ).order_by(
                s.t.devices.c.device_name
            )
        )]

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
                ).join(
                    meta_float, _on(meta_float), isouter=True
                ).join(
                    meta_string, _on(meta_string), isouter=True
                ).where(
                    meta.c.device_name == device_name
                ).order_by(
                    meta.c.device_meta_name
                )
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
            "Database connnection already initialized. "
            + "Restart Python interpreter."
        )
    if not hasattr(parser, "address_meta"):
        raise AssertionError(
            "Parser is missing attribute 'device_address_meta'. "
        )
    if os.path.exists(_device_db_location()):
        os.remove(_device_db_location())
    _Inserter(parser)

class _Inserter():
    """Inserts rows into sqllite database.
    """
    def __init__(self, parser):
        self.parser = parser
        with _session() as s:
            s.execute(sqlalchemy.text('SELECT 1'))
            pkdlog("Creating Areas")
            self.create_areas_db(s)
            pkdlog("Creating Beampaths")
            self.create_beampaths_db(s)
            pkdlog("Creating device")
            self.create_device_db(s)
            pkdlog("Creating device meta")
            self.create_device_meta_db(s)
            pkdlog("Creating device meta float")
            self.create_device_meta_float_db(s)
            pkdlog("Creating device meta string")
            self.create_device_meta_string_db(s)
            pkdlog("Creating Address")
            self.create_address_db(s)
            pkdlog("Creating Accessor")
            self.create_accessor_db(s)

    def create_address_db(self, s):
        s._conn.execute(s.t.addresses.insert(), self.parser.address_meta)

    def create_accessor_db(self, s):
        s._conn.execute(s.t.accessors.insert(), self.parser.accessor_meta)

    def create_areas_db(self, s):
        s._conn.execute(s.t.areas.insert(), ins)

    def create_beampaths_db(self, s):
        s._conn.execute(s.t.beampaths.insert(), self.parser.area_map)

    def create_device_db(self, s):
        s._conn.execute(s.t.devices.insert(), self.parser.devices)

    def create_device_meta_db(self, s):
        s._conn.execute(s.t.device_meta.insert(), self.parser.device_meta)

    def create_device_meta_float_db(self, s):
        s._conn.execute(s.t.device_meta_float.insert(), self.parser.device_meta_float)

    def create_device_meta_string_db(self, s):
        s._conn.execute(s.t.device_meta_string.insert(), self.parser.device_meta_string)

def _db_type_prefix(uri):
    if not uri.startswith("sqlite"):
        uri = 'sqlite:///' + uri
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
    schema = {
        "areas": {
            "area": "str 64 primary_key",
        },
        "beampaths": {
            "area": "str 64 primary_key foreign",
            "beampath": "str 64 primary_key"
        },
        "devices": {
            "device_name": "str 64 primary_key",
            "area": "str 64 foreign",
            "device_type": "str 64",
            "cs_name": "str 64",
            "is_active": "bool nullable",
        },
        "device_meta": {
            "device_name": "str 64 primary_key foreign",
            "device_meta_name": "str 64 primary_key",
            "meta_type": "str 64"
        },
        "device_meta_float": {
            "device_name": "str 64 primary_key foreign",
            "device_meta_name": "str 64 primary_key",
            "meta_value": "float 64"
        },
        "device_meta_string": {
            "device_name": "str 64 primary_key foreign",
            "device_meta_name": "str 64 primary_key",
            "meta_value": "str 64"
        },
        "addresses": {
            "device_name": "str 64 primary_key foreign",
            "cs_address": "str 64 primary_key",
        },
        "accessors": {
            "device_name": "str 64 primary_key foreign",
            "accessor_name": "str 64 primary_key",
            "cs_address": "str 64",
        },
    }
    _meta = pykern.sql_db.Meta(
        uri=uri,
        schema=schema
    )

def _device_db_location():
    db_location = (
        slac_db.config.package_data().joinpath('device.sqlite3')
    )
    return str(db_location)

def _session():
    if _meta is None:
        _init_db()
    return _meta.session()
