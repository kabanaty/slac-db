import csv
from sqlalchemy import text
import slac_db.config
import slac_db.oracle
from slac_db.oracle_remote import get_connection

def get_lcls_elements_csv(csv_output='lcls_elements.csv'):
    """Get the lcls_elements.csv file from Oracle.
    This function only works on production.

    Args:
        csv_output: Name of the output csv file.
    """
    import pandas as pd
    sql_query = text("select * from lcls_infrastructure.V_LCLS_ELEMENTS_DIAG")
    try:
        with get_connection() as connection:
            df = pd.read_sql(sql_query, connection)
            df.to_csv(csv_output, index=False)
    except Exception as e:
        print(f"An error occurred {e}")


def to_oracle_db(csv_source=None):
    """ Build  oracle DB with SQLAlchemy.

    Args:
        csv_source: Location of Oracle CSV file
    """
    p = _Parser(csv_source=csv_source)
    return slac_db.oracle.recreate(p)

class _Parser():
    """Container for DB row data.
    """
    def __init__(self, csv_source=None):
        if not csv_source:
            csv_source = (
                slac_db.config.package_data() / "lcls_elements.csv"
            )
        self.rows = {}
        with open(csv_source, "r") as c:
            reader = csv.reader(c)
            self._parse_csv(reader)

    def _parse_csv(self, reader):
        next(reader)  # skip group header row
        names = [r.lower() for r in next(reader)]
        i = 0
        # Track station names already recorded for KLYS sub-cavity dedup.
        # Maps station_name -> index in self.rows for the canonical row.
        # Keyed on the stripped element name (e.g. "K21_5") so that dirty
        # cs_name data (truncated or transposed digits in sectors 12-19)
        # cannot produce duplicate station entries.
        _klys_seen = {}
        for row in reader:
            values = [None if v == '' else v for v in row]
            d = dict(zip(names, values))
            element = d.get("element") or ""
            cs_name = d.get("control system name") or ""
            keyword = d.get("keyword") or ""
            # Deduplicate klystron sub-cavities (K21_5A/B/C/D -> K21_5).
            # A sub-cavity row is an LCAV whose element ends in A-D and whose
            # cs_name contains "KLYS" (handles both "KLYS:LI{s}:{n}1" and
            # legacy reversed form "LI{s}:KLYS:{n}1" used in sectors 12-19).
            # Dedup key is the station name (element minus trailing letter) so
            # that cs_name inconsistencies in the source data don't create
            # duplicate entries (e.g. K12_3A has cs LI12:KLYS:3 while
            # K12_3B/C/D have LI12:KLYS:31).
            if (
                keyword == "LCAV"
                and "KLYS" in cs_name
                and len(element) > 1
                and element[-1] in "ABCD"
            ):
                station = element[:-1]  # e.g. "K21_5A" -> "K21_5"
                if station in _klys_seen:
                    # Already have a row for this station; skip this sub-cavity.
                    continue
                # First time seeing this station: record it and rename element.
                d["element"] = station
                _klys_seen[station] = i
            self.rows[i] = d
            i += 1
