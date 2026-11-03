import slac_db.create.device
import slac_db.create.lcls_elements
import slac_db.create.meme_names
import slac_db.create.dummy


def device_db():
    slac_db.create.device.to_device_db()


def oracle_db(csv_source=None):
    slac_db.create.lcls_elements.to_oracle_db(csv_source)


def directory_service_db():
    slac_db.create.meme_names.to_directory_service_db()

def dummy_db():
    slac_db.create.dummy.to_dummy_db()
