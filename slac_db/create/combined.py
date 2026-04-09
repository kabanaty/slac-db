import slac_db.config
import slac_db.directory_service
import slac_db.io
import slac_db.oracle
import slac_db.device
from pykern.pkcollections import PKDict

_ACCESSOR_YAML = (
    slac_db.config.package_data() / "accessor_names.yaml"
)
_DELIM = ":"

def to_device_db():
    """ Build  device DB with SQLAlchemy
    """
    return slac_db.device.recreate(_Parser())

class _Parser():
    """Container for DB row data.
    """
    def __init__(self):
        self._address_map()
        self._address_meta()

    def _address_meta(self):
        """Create a dictionary that combines accessor names
        with device names and addresses.

        Sets:
            self.device_address_meta
        """
        accessor_map = slac_db.io.read_dict(_ACCESSOR_YAML)
        def get_accessor_name(d_type, tail):
            if dev_map := accessor_map.get(d_type, None):
                return dev_map.get(tail, None)
            return None
        def _build():
            for r in slac_db.oracle.get_all_rows():
                yield from _meta(
                    r["element"],
                    r["control system name"],
                    r["keyword"],
                )
        def _meta(device, head, d_type):
            for t in self.address_map.get(head, [None]):
                if t is None:
                    continue
                yield PKDict(
                    device_name=device,
                    cs_address=_DELIM.join([head, t]),
                    accessor_name=get_accessor_name(d_type, t)
                )

        self.device_address_meta = list(_build())

    def _address_map(self):
        """Create an address map where keys are PV heads
        and values are lists of associated address tails.

        Sets:
            self.address_map
        """
        def _parse(names):
            names = list(reversed(sorted(names)))
            while names:
                yield _parse_group(names)

        def _parse_group(names):
            m, n = _split_one(names.pop())
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

        self.address_map = dict(_parse(slac_db.directory_service.get_all()))
