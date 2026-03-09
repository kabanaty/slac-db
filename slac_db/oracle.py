import slac_db.config
import sqlalchemy
import pykern.sql_db
import os


_meta = None

def get_address_header(device=None):
    with _session() as s:
        return s.select_one(
            sqlalchemy.select(
                s.t.elements.c["control system name"]
            ).where(
                s.t.elements.c["element"] == device
            )
        )["control system name"]

def get_devices(area=None, device_type=None):
    if device_type is None:
        device_type = "%"
    with _session() as s:
        return list(
            r.element for r in s.select(
                sqlalchemy.select(
                    s.t.elements.c["element"]
                ).where(
                    s.t.elements.c["keyword"].like(device_type)
                ).where(
                    s.t.elements.c["area"] == area
                )
            )
        )

def get_device_row(element=None):
    with _session() as s:
        return s.select_one(
            sqlalchemy.select(
                s.t.elements
            ).where(
                s.t.elements.c["element"] == element
            )
        )

def get_beampaths():
    def parse_beampaths(beampath_csv_row):
        row = beampath_csv_row.replace(' ', '').split(',')
        row = filter(None, row)
        return row

    beampaths = set()
    with _session() as s:
        query = sqlalchemy.select(s.t.elements.c.beampath).distinct()
        for r in s.select(query):
            if r.beampath is None:
                continue
            beampaths.update(parse_beampaths(r.beampath))
    return sorted(list(beampaths))


def get_areas():
    def exclude_bad_patterns(column):
        bad_patterns = ['\t- NO AREA -', '*%']
        filters = [None] * len(bad_patterns)
        for i in range(0, len(bad_patterns)):
            filters[i] = column.not_like(bad_patterns[i])
        return sqlalchemy.and_(*filters)

    with _session() as s:
        return list(
            r.area for r in s.select(
                sqlalchemy.select(
                    s.t.elements.c.area
                ).where(
                    exclude_bad_patterns(s.t.elements.c.area)
                ).distinct()
            )
        )

def recreate(parser):
    assert not _meta
    assert parser.rows
    if os.path.exists(_oracle_uri()):
        os.remove(_oracle_uri())
    _Inserter(parser)


class _Inserter():
    def __init__(self, parser):
        with _session() as s:
            self._rows(parser.rows, s)

    def _rows(self, rows, session):
        i = 0
        for r in rows.values():
            ins = {}
            for c in session.t.elements.c:
                ins[c.name] = r[c.name]
            session.insert("elements", **ins)
            i = i + 1


def _db_type_prefix(uri):
    if not uri.startswith("sqlite"):
        uri = 'sqlite:///' + uri
    return uri

def _init_db(uri=None):
    global _meta
    if uri is None:
        uri = _oracle_uri()
    uri = _db_type_prefix(uri)
    schema = {
        "elements": {
            "Area": "str 64 nullable",
            "Element": "str 64 primary_key",
            "Control System Name": "str 64 nullable",
            "Keyword": "str 64 nullable",
            "Beampath": "str 64 nullable",
            "SumL (m)": "float 64 nullable",
            "Effective Length (m)": "float 64 nullable",
            "Rf Frequency (MHz)": "float 64 nullable"
        }
    }
    _meta = pykern.sql_db.Meta(
        uri=uri,
        schema=schema
    )

def _oracle_uri():
    uri = (
        slac_db.config.package_data() / 'lcls_elements.sqlite3'
    )
    return str(uri)

def _session():
    if _meta is None:
        _init_db()
    return _meta.session()
