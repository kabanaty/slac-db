import slac_db.aida

def to_aida_db():
    return slac_db.aida.recreate(_Parser())

class _Parser:
    def __init__(self):
        self.addresses = set()
        self._get_from_meme()

    def _get_from_meme(self):
        import meme.names
        address_list = meme.names.list_pvs("%", timeout=600)
        for a in address_list:
            self.addresses.add(a)
