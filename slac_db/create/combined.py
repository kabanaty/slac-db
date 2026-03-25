import slac_db.aida
import slac_db.oracle
import slac_db.device
from pykern.pkcollections import PKDict

_DELIM = ":"

def to_accessor_device():
    return slac_db.device.recreate(_Parser())

class _Parser():        
    def __init__(self):
        self._build_address_map()
        self._build_address_pairs()

    def _build_address_pairs(self):
        def _pairs(device, head):
            for t in self.address_map.get(head, [None]):
                if t is None:
                    continue
                yield PKDict(
                    device_name=device,
                    cs_address=_DELIM.join([head, t])
                )
        def _build():
            for r in slac_db.oracle.get_all_rows():
                yield from _pairs(
                    r["element"],
                    r["control system name"]
                )

        self.device_address_pairs = list(_build())

    def _build_address_map(self):
        def _parse(names):
            while names:
                yield _parse_group(names)

        def _parse_group(names):
            m, n = _split_one(names.pop())
            rv = []
            rv = [n]
            while names:
                x = _split_one(names[-1])
                if x[0] != m:
                    break
                names.pop()
                rv.append(x[1])
            return m, rv
        def _split_one(name):
            p = name.split(_DELIM)
            return _DELIM.join(p[:3]), _DELIM.join(p[3:])

        self.address_map = dict(
            _parse(
                sorted(
                    slac_db.aida.get_all()
                )
            )
        )
