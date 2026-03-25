import os
import pykern.sql_db
import slac_db.config

_meta = None

def recreate(parser):
    assert not _meta
    assert parser.device_address_pairs
    if os.path.exists(_device_db_uri()):
        os.remove(_device_db_uri())
    _Inserter(parser)

class _Inserter():
    def __init__(self, parser):
        with _session() as s:
            for p in parser.device_address_pairs:
                ins = {}
                ins["device_name"] = p.device_name
                ins["cs_address"] = p.cs_address
                s.insert("addresses", **ins)

def _db_type_prefix(uri):
    if not uri.startswith("sqlite"):
        uri = 'sqlite:///' + uri
    return uri

def _init_db(uri=None):
    global _meta
    if uri is None:
        uri = _device_db_uri()
    uri = _db_type_prefix(uri)
    schema = {
        "addresses": {
            "device_name": "str 64 primary_key",
            "cs_address": "str 64 primary_key",            
        },
    }
    _meta = pykern.sql_db.Meta(
        uri=uri,
        schema=schema
    )

def _device_db_uri():
    uri = (
        slac_db.config.package_data() / 'device.sqlite3'
    )
    return str(uri)

def _session():
    if _meta is None:
        _init_db()
    return _meta.session()
