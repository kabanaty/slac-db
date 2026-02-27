import os
import slac_db.config
import sqlalchemy
import pykern.sql_db
import slac_db.oracle

_meta = None

def exists_address(device=None, address=None):
    head = slac_db.oracle.get_address_header(device=device)
    with _session() as s:
        return set(
            r["address"] for r in s.select(
                sqlalchemy.select(
                    s.t.addresses.c["address"]
                ).where(
                    s.t.addresses.c["address"] == address
                )
            )
        )

def get_addresses(device=None):
    head = slac_db.oracle.get_address_header(device=device)
    with _session() as s:
        cs_address = s.t.addresses.c["address"]
        return set(
            r["address"] for r in s.select(
                sqlalchemy.select(
                    cs_address
                ).where(
                    cs_address.like(f"{head}%")
                )
            )
        )

def recreate(parser):
    assert not _meta
    assert parser.addresses
    if os.path.exists(_aida_uri()):
        os.remove(_aida_uri())
    _Inserter(parser)


def search_addresses(device=None, query=None):
    head = slac_db.oracle.get_address_header(device=device)
    with _session() as s:
        cs_address = s.t.addresses.c["address"]
        return set(
            r["address"] for r in s.select(
                sqlalchemy.select(
                    cs_address
                ).where(
                    cs_address.like(f"{head}:{query}")
                )
            )
        )

class _Inserter:
    def __init__(self, parser):
        self.counts = {"addresses": 0}
        with _session() as s:
            self._addresses(parser.addresses, s)

    def _addresses(self, addresses, session):
        i = 0
        for a in addresses:
            print(f"\r{i} / {len(addresses)}", end="")
            session.insert("addresses", address=a)
            i = i + 1

def _db_type_prefix(uri):
    if not uri.startswith("sqlite"):
        uri = 'sqlite:///' + uri
    return uri

def _init_db(uri=None):
    global _meta
    if uri is None:
        uri = _aida_uri()
    uri = _db_type_prefix(uri)
    schema = {
        "addresses": {
            "address": "str 64 primary_key",
        }
    }
    _meta = pykern.sql_db.Meta(
        uri=uri,
        schema=schema
    )

def _aida_uri():
    uri = (
        slac_db.config.root_directory()
        / 'slac_db' / 'package_data' / 'aida_pvs.db'
    )
    return str(uri)

def _session():
    if _meta is None:
        _init_db()
    return _meta.session()
