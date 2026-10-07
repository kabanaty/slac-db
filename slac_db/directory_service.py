import os
import os.path
import slac_db.config
import sqlalchemy
import pykern.sql_db
import slac_db.element_tables

_meta = None

def verify_address(address):
    """Verify that an address exists.

    Args:
        address (str): EPICS PV address

    Returns:
        Address if address exists.
        None if it does not.
    """
    with _session() as s:
        return list(
            r["address"] for r in s.select(
                sqlalchemy.select(
                    s.t.addresses.c.address
                ).where(
                    s.t.addresses.c.address == address
                ).order_by(
                    s.t.addresses.c.address
                )
            )
        )

def verify_head(head, instance=None):
    """Verify that an address header exists.
    PVs are written as 'type:area:unit:instance'.
    Our db index by 'type:area:unit'.

    Args:
        address (str): EPICS PV address
        instance (str): 

    Returns:
        All addresses under head.
        None if none are found.
    """
    with _session() as s:
        selection = sqlalchemy.select(
            s.t.addresses.c.head
        ).where(
            s.t.addresses.c.head == head
        )

        if instance:
            selection.where(
                s.t.addresses.c.head.op('GLOB')(
                    head + ':' + instance + ':*'
                )
            )
        
        return set(
            r["address"] for r in s.select(selection)
        )

def get_addresses(device=None, cs_name=''):
    """Get all addresses per device.

    Args:
        device (str): MAD name of the device as found in Oracle.

    Returns:
        tuple: Sorted address values.
    """
    if not device and not cs_name:
        raise ValueError("Must include only one keyword device=device_name or cs_name=pv as argument.")
    if device and cs_name:
        raise ValueError("Must include only one keyword device=device_name or cs_name=pv as argument.")
    if device:
        cs_name = slac_db.element_tables.get_address_header(device=device)
    pv_codes = cs_name.split(':')
    instance = None
    if len(pv_codes) == 4:
        instance = pv_codes[3]
        cs_name = ':'.join(pv_codes[:3])
    with _session() as s:
        selection = sqlalchemy.select(
            s.t.addresses.c.address
        ).where(
            s.t.addresses.c.head == cs_name
        )
        if instance:
            selection = selection.where(
                s.t.addresses.c.address.op('GLOB')(
                    cs_name + ':' + instance + ':*'
                )
            )
        return list(
            r["address"] for r in s.select(selection)
        )

def get_all_addresses():
    """Get all addresses in a generator.

    Returns:
        tuple: Yields address values.
    """
    with _session() as s:
        cs_address = s.t.addresses.c.address
        for r in s.select(
            sqlalchemy.select(cs_address)
        ):
            yield r["address"]

def recreate(parser):
    """Rebuild the local directory_service sqlite3 database
    only if it is not already loaded.

    Args:
        parser: Container for column data.
    """
    assert not _meta
    assert parser.addresses
    if os.path.exists(_directory_service_location()):
        os.remove(_directory_service_location())
    _Inserter(parser)

class _Inserter:
    """Creates a session and commits rows to the db.

    Functions:
        _addresses: Inserts all addresses in parser.addresses.
    """
    def __init__(self, parser):
        self.counts = {"addresses": 0}
        with _session() as s:
            self._types(parser.types, s)
            self._areas(parser.areas, s)
            self._headers(parser.headers, s)
            self._addresses(parser.addresses, s)

    def _types(self, types, session):
        for t in types:
            session.insert("types", type=t)

    def _areas(self, areas, session):
        for a in areas:
            session.insert("areas", area=a)

    def _headers(self, headers, session):
        for h in headers.values():
            session.insert("headers", **h)

    def _addresses(self, addresses, session):
        # We have to do it this way unfortunately.
        # Bulk insert is not faster.
        for entry in addresses:
            session.insert("addresses", **entry)

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
        location = _directory_service_location()
    uri = _db_type_prefix(location)
    schema = {
        "areas": {
            "area": "str 64 primary_key",
        },
        "types": {
            "type": "str 64 primary_key",
        },
        "headers": {
            "area": "str 64 foreign",
            "type": "str 64 foreign",
            "unit": "str 64",
            "head": "str 64 primary_key",
        },
        "addresses": {
            "head": "str 64 foreign",
            "address": "str 64 primary_key",
        }
    }
    _meta = pykern.sql_db.Meta(
        uri=uri,
        schema=schema
    )

def _directory_service_location():
    loc = (
        slac_db.config.package_data().joinpath('directory_service_pvs.sqlite3')
    )
    return str(loc)

def _session():
    if _meta is None:
        _init_db()
    return _meta.session()
