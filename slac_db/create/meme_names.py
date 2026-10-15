import slac_db.directory_service

def to_directory_service_db():
    """ Build  device DB with SQLAlchemy.
    """
    return slac_db.directory_service.recreate(_Parser())

class _Parser:
    """Container for DB row data.
    """
    def __init__(self):
        self.areas = set()
        self.types = set()
        self.headers = dict()
        self.addresses = list()
        self._get_from_meme()

    def _get_from_meme(self):
        import meme.names
        address_list = meme.names.list_pvs("%", timeout=600)
        for a in address_list:
            part = a.split(':')
            if len(part) < 4:
                continue
            head = ':'.join(part[0:3])
            entry = {
                'head': head,
                'type': part[0],
                'area': part[1],
                'unit': part[2],
            }
            self.types.add(entry['type'])
            self.areas.add(entry['area'])
            self.headers[head] = entry
            self.addresses.append(
                {'head': head,
                 'address': a}
            )

        self.types = [{'type': t} for t in sorted(self.types)]
        self.areas = [{'area': t} for t in sorted(self.areas)]
        self.headers = [i for h, i in sorted(self.headers.items())]
