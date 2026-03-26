import csv
import slac_db.config
import slac_db.oracle

def to_oracle_db(csv_source=None):
    p = _Parser(csv_source=csv_source)
    return slac_db.oracle.recreate(p)

class _Parser():
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
