_DELIM = ":"

class DNDict():
    def __init__(self):
        self._dn_map = {}
        self._i = 0

    def add(self, address):
        def recur(table, parts):
            if len(parts) == 0:
                self._i += 1
                return {'': None}
            a = recur(
                table.get(parts[0], {}),
                parts[1:]
            )
            table.update({parts[0]: a})
            return(table)
        p = address.split(_DELIM)
        recur(self._dn_map, p)

    def get(self, address):
        tails = self._rebuild(address)
        return [self._cat(address, t) for t in tails]

    def _cat(self, head, tail):
        return _DELIM.join([head, tail])

    def _submap(self, address):
        parts = address.split(_DELIM)
        t = self._dn_map
        for p in parts:
            if p not in t:
                return None
            t = t[p]
        return t

    def _rebuild(self, address):
        def recur(table):
            o = []
            for key, value in table.items():
                if value is None:
                    return [key]
                else:
                    a = recur(value)
                    o.extend([self._cat(a, end) for end in a])
            return o
        s = self._submap(address)
        return recur(s)
