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
    Pulls from copies of oracle and directory service.
    Expects EPICS Addresses to be 3 units long, e.g. (AAA:BBB:CCC)
    """
    def __init__(self):
        print("Parsing Area")
        self._area_map()
        print("Parsing Device")
        self._device_meta()
        print("Parsing Address")
        self._address_map()
        print("Parsing Accessor")
        self._address_meta()

    def _address_meta(self):
        """Create a dictionary that combines accessor names
        with device names and addresses.

        Sets:
            self.device_address_meta
        """
        def _build():
            for r in slac_db.oracle.get_all_rows():
                if r["element"] not in self.devices:
                    continue
                yield from _meta(
                    r["element"],
                    r["control system name"],
                    r["keyword"],
                )

        def _get_accessor(d_type, pv_tail):
            if (m := self.accessor_map.get(d_type, None)) is not None:
                return m.get(pv_tail, None)
            return m

        def _meta(device, pv_head, d_type):
            for pv_tail in self.address_map.get(pv_head, [None]):
                if pv_tail is None:
                    continue
                yield PKDict(
                    device_name=device,
                    cs_address=_DELIM.join([pv_head, pv_tail]),
                    accessor_name=_get_accessor(d_type, pv_tail)
                )

        self.accessor_map = slac_db.io.read_dict(_ACCESSOR_YAML)
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
            h, t = _split_one(names.pop())
            rv = [t]
            while names:
                next_h, next_t = _split_one(names[-1])
                if next_h != h:
                    break
                names.pop()
                rv.append(next_t)
            return h, rv

        def _split_one(name):
            p = name.split(_DELIM)
            return _DELIM.join(p[:3]), _DELIM.join(p[3:])

        self.address_map = dict(
            _parse(
                slac_db.directory_service.get_all_addresses()
            )
        )

    def _area_map(self):
        def parse_beampaths(beampath_csv):
            if beampath_csv is None:
                return []
            beampaths = beampath_csv.replace(' ', '').split(',')
            beampaths = filter(None, beampaths)
            yield from beampaths

        self.areas = set()
        rv = set()
        for r in slac_db.oracle.get_all_rows():
            beampath_csv = r["beampath"]
            area = r["area"]
            rv = rv.union(set((area, b) for b in parse_beampaths(beampath_csv)))
            self.areas.add(area)
        self.area_map = list(rv)

    def _device_meta(self):
        def _parse_device():
            for r in slac_db.oracle.get_all_rows():
                yv = {
                    "device_name": r["element"],
                    "area": r["area"],
                    "device_type": r["keyword"],
                    "cs_name": r["control system name"]                    
                }
                if None in yv.values() or ":" in r["element"]:
                    continue
                self.devices.add(r["element"])
                yield yv
        self.devices = set()
        self.device_meta = [device for device in _parse_device()]
