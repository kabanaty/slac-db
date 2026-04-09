import os
import os.path
import slac_db.config
import sqlalchemy
import pykern.sql_db
import slac_db.oracle

_meta = None

def get_addresses(device=None):
    """Get all addresses per device.

    Args:
        device (str): MAD name of the device as found in Oracle.

    Returns:
        tuple: Sorted address values.
    """
    head = slac_db.oracle.get_address_header(device=device)
    with _session() as s:
        cs_address = s.t.addresses.c["address"]
        return tuple(sorted(
            r["address"] for r in s.select(
                sqlalchemy.select(
                    cs_address
                ).where(
                    cs_address.like(f"{head}%")
                )
            )
        ))

def get_all_addresses():
    """Get all addresses in a generator.

    Returns:
        tuple: Yields address values.
    """
    with _session() as s:
        cs_address = s.t.addresses.c["address"]
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
            self._addresses(parser.addresses, s)

    def _addresses(self, addresses, session):
        # We have to do it this way unfortunately.
        # Bulk insert is not faster.
        n = len(addresses)
        i = 0
        for a in addresses:
            session.insert("addresses", address=a)
            i += 1
            print("{i} / {n}", end='\r')

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
        "addresses": {
            "address": "str 64 primary_key",
        }
    }
    _meta = pykern.sql_db.Meta(
        uri=uri,
        schema=schema
    )

def _directory_service_location():
    loc = (
        slac_db.config.package_data() / 'directory_service_pvs.sqlite3'
    )
    return str(loc)

def _session():
    if _meta is None:
        _init_db()
    return _meta.session()
