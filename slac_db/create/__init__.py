import slac_db.create.meme_names
import slac_db.create.lcls_elements_csv

def oracle_db(csv_source=None):
    slac_db.create.lcls_elements_csv.to_oracle_db(csv_source)

def aida_db():
    slac_db.create.meme_names.to_aida_db()
