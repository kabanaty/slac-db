import slac_db.aida
import slac_db.oracle
import slac_db.device

_DELIM = ":"

def to_accessor_device():
    return slac_db.device.recreate(_Parser())

class _Parser():
    def __init__(self):
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

        self.address_map = dict(_parse(sorted(slac_db.aida.get_all())))

        self.device_address_pairs = []
        rows = slac_db.oracle.get_all_rows()
        a = [
            (r["element"], r["control system name"])
            for r in rows
            if r["control system name"] is not None
        ]
        for d, h in a:
            if (tails := self.address_map.get(h, None)) is None:
                continue
            l = [(d, _DELIM.join([h, t])) for t in tails]
            self.device_address_pairs += l
