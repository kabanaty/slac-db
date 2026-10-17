import csv
from sqlalchemy import text
import slac_db.config
import slac_db.element_tables

_ORACLE_TO_YAML_TYPE_MAP = {
    "SOLE": "magnet",
    "QUAD": "magnet",
    "XCOR": "magnet",
    "YCOR": "magnet",
    "BEND": "magnet",
    "PROF": "screen",
    "WIRE": "wire",
    "LBLM": "lblm",
    "BPM": "bpm",
    "LCAV": "tcav",
    "INST": "pmt",
    "IMON": "toroid",
}


def get_lcls_elements_csv(csv_output="lcls_elements.csv"):
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
    """Build  oracle DB with SQLAlchemy.

    Args:
        csv_source: Location of Oracle CSV file
    """
    p = _Parser(csv_source=csv_source)
    return slac_db.element_tables.recreate(p)


class _Parser:
    """Container for DB row data."""

    def __init__(self, csv_source=None):
        if not csv_source:
            csv_source = slac_db.config.package_data().joinpath("lcls_elements.csv")
        self.rows = []
        with open(csv_source, "r") as c:
            reader = csv.reader(c)
            self._parse_csv(reader)

    def _parse_csv(self, reader):
        next(reader)  # skip group header row
        header = next(reader)
        index = {r.lower(): i for r, i in zip(header, range(0, len(header)))}
        wanted_cols = [
            k.lower()
            for k in slac_db.element_tables.schema["elements"].keys()
            if k != "yaml_type"
        ]

        def get_col(row, col):
            return row[index[col]]

        _klys_seen = set()
        for row in reader:
            d = {c: get_col(row, c) or None for c in wanted_cols}
            d["yaml_type"] = _ORACLE_TO_YAML_TYPE_MAP.get(d["keyword"], None)
            cs_name = d["control system name"] or ""
            element = d["element"] or ""
            keyword = d["keyword"] or ""
            # Deduplicate klystron sub-cavities (K21_5A/B/C/D -> K21_5).
            # A sub-cavity row is an LCAV whose element ends in A-D and whose
            # cs_name contains "KLYS" (handles both "KLYS:LI{s}:{n}1" and
            # legacy reversed form "LI{s}:KLYS:{n}1" used in sectors 12-19).
            # Dedup key is the station name (element minus trailing letter) so
            # that cs_name inconsistencies in the source data don't create
            # duplicate entries (e.g. K12_3A has cs LI12:KLYS:3 while
            # K12_3B/C/D have LI12:KLYS:31).
            if (
                d["keyword"] == "LCAV"
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
                _klys_seen.add(station)
            self.rows.append(d)
