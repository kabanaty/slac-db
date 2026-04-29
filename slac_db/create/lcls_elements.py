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
        names = [r.lower() for r in next(reader)]
        i = 0
        for row in reader:
            values = [None if v == '' else v for v in row]
            self.rows[i] =  dict(zip(names, values))
            i += 1
