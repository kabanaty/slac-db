from contextlib import contextmanager
import slac_db.config
import sqlalchemy
import pykern.sql_db

_ORACLE_TNS      = 'slacprod' # name/connection of Oracle DB on prod
_ORACLE_USERNAME = 'lcls_read'

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

@contextmanager
def get_connection():
    """Yield a connection to Oracle. Only works on production.
    Using as a context manager so the connection and engine are always cleaned up:
    with get_connection() as conn:
    """
    engine = sqlalchemy.create_engine(_get_remote_uri())
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()
        engine.dispose()


def _get_oracle_pw(username=_ORACLE_USERNAME):
    """Get Oracle password. This only works on production.
    """
    try:
        import subprocess
        cmd      = subprocess.run(['getPwd', username], capture_output=True, text=True, check=True)
        password = cmd.stdout.strip()
        return password
    except Exception as e:
        print(f"Could not get Oracle password: {e}")
        return None

def _get_remote_uri():
    """Get string needed to connect to Oracle remotely.
    """
    password  = _get_oracle_pw(_ORACLE_USERNAME)
    connection_string = f'oracle+cx_oracle://{_ORACLE_USERNAME}:{password}@{_ORACLE_TNS}'
    return connection_string


def _init_remote_db():
    """Assumes remote oracle DB. TODO: Make this more general?

       _meta: wrapper that holds sqlalchemy metadata.
    """
    global _meta
    #TODO: grab schema from Oracle?
    schema = None
    #TODO: is uri just the connection string?
    uri = _get_remote_uri()
    _meta = pykern.sql_db.Meta(
        uri=uri,
        schema=None
        )
    return

def _oracle_location():
    loc = (
        slac_db.config.package_data() / 'lcls_elements.sqlite3'
    )
    return str(loc)

def _session():
    if _meta is None:
        _init_remote_db()
    return _meta.session()
