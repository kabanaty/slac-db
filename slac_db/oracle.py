import slac_db.config
import sqlalchemy
import pykern.sql_db
import os.path
import os


_meta = None

def get_address_header(device=None):
    """Get address header of a device.

    Args:
        device (str): MAD name of the device as found in Oracle.

    Returns:
        tuple: The address header.
    """
    with _session() as s:
        return s.select_one(
            sqlalchemy.select(
                s.t.elements.c["control system name"]
            ).where(
                s.t.elements.c["element"] == device
            )
        )["control system name"]

def get_devices(area=None, device_type=None):
    """Get devices of one type from an area.

    Args:
        area (str): Name of the accelerator area.
        device_type (str): Type of device as listed in Oracle.

    Returns:
        tuple: Device names in Z order.
    """
    if device_type is None:
        device_type = "%"
    with _session() as s:
        return tuple(
            r.element for r in s.select(
                sqlalchemy.select(
                    s.t.elements.c["element"]
                ).where(
                    s.t.elements.c["keyword"] == device_type
                ).where(
                    s.t.elements.c["area"] == area
                ).order_by(s.t.elements.c["suml (m)"])
            )
        )

def get_all_address_headers():
    with _session() as s:
        return [r["control system name"] for r in s.select(
            sqlalchemy.select(
                s.t.elements.c["control system name"]
            )
        )]

def get_all_rows():
    with _session() as s:
        return [r for r in s.select(
            sqlalchemy.select(
                s.t.elements
            )
        )]

def get_device_row(element=None):
    """Get the full row for an element.

    Args:
        element: name of the element to get.
    Returns:
        sql alchemy row: Row object with each column.
    """
    with _session() as s:
        return s.select_one(
            sqlalchemy.select(
                s.t.elements
            ).where(
                s.t.elements.c["element"] == element
            )
        )

def get_beampaths():
    """Get all beampaths from Oracle.

    Returns:
        List of beampaths sorted alphabetically.
    """
    beampaths = set()
    def parse_beampaths(beampath_csv):
        if beampath_csv is None:
            return
        c = beampath_csv.replace(' ', '').split(',')
        c = filter(None, c)
        beampaths.update(c)

    with _session() as s:
        query = sqlalchemy.select(s.t.elements.c.beampath).distinct()
        for r in s.select(query):
            parse_beampaths(r.beampath)
    return sorted(list(beampaths))


def get_areas():
    """Get all areas from Oracle.

    Returns:
        List of areas sorted alphabetically.
    """
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
    """Rebuilds the sqlite copy of Oracle.
    Fails if a connection has already been made.

    Args:
        Parser object with attribute 'rows' for row data.
    """
    if _meta:
        raise AssertionError(
            "Database connnection already initialized. "
            + "Restart Python interpreter."
        )
    if not hasattr(parser, "rows"):
        raise AssertionError(
            "Parser is missing attribute 'rows'. "
        )        
    if os.path.exists(_oracle_uri()):
        os.remove(_oracle_uri())
    _Inserter(parser)


class _Inserter:
    """Inserts rows into sqllite database.
    """
    def __init__(self, parser):
        with _session() as s:
            self._rows(parser.rows, s)
    def _rows(self, rows, session):
        for r in rows.values():
            ins = {}
            for c in session.t.elements.c:
                ins[c.name] = r[c.name]
            session.insert("elements", **ins)

def _db_type_prefix(uri):
    if not uri.startswith("sqlite"):
        uri = 'sqlite:///' + uri
    return uri

def _init_db(uri=None):
    """Initializes pykern sqlalchemy wrapper. Initialization
    occurs when a session is first created.

       _meta: wrapper that holds sqlalchemy metadata.
    """
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
