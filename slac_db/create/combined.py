from numpy import isdtype
import slac_db.config
import slac_db.directory_service
import slac_db.io
import slac_db.oracle
import slac_db.device
from pykern.pkcollections import PKDict
import yaml

_ACCESSOR_YAML = (
    slac_db.config.package_data() / "accessor_names.yaml"
)
_DELIM = ":"
_DEFAULT_DEVICE_META = [("suml (m)", "sum_l_meters")]
_MAGNET_META = [("effective length (m)", "l_eff")]
_DEVICE_META_MAP = {
    "SOLE": _MAGNET_META,
    "QUAD": _MAGNET_META,
    "XCOR": _MAGNET_META,
    "YCOR": _MAGNET_META,
    "BEND": _MAGNET_META,
    "LCAV": [
        ("effective length (m)", "l_eff"),
        ("rf frequency (mhz)", "rf_freq")
    ]
}
_STRING_META_LOC = slac_db.config.package_data() / "wire_metadata.yaml"

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
        self._devices()
        print("Parsing Device Meta")
        self._device_meta()
        print("Parsing Address")
        self._address_map()
        self._address_meta()
        print("Parsing Accessor")
        self._accessor_meta()

    def _address_meta(self):
        """ Create a list of tuples connecting device names
        to device addresses.

        Sets:
            self.address_meta
        """
        def _build():
            for r in slac_db.oracle.get_all_rows():
                if r["element"] not in self.device_names:
                    continue
                if r["control system name"] not in self.address_map:
                    continue
                yield from [
                    PKDict(
                        device_name=r["element"],
                        cs_address=c
                    )
                    for c in self.address_map[r["control system name"]]
                ]
        self.address_meta = list(_build())
        

    def _accessor_meta(self):
        """Create a dictionary that combines accessor names
        with device names and addresses.

        Sets:
            self.accessor_meta
            self.accessor_map
        """
        def _build():
            for r in slac_db.oracle.get_all_rows():
                if r["element"] not in self.device_names:
                    continue
                yield from _meta(
                    r["element"],
                    r["control system name"],
                    r["keyword"],
                )

        def _get_accessors(d_type, address):
            if not (device_map := self.accessor_map.get(d_type, None)):
                return
            if not (accessor := device_map.get(address, None)):
                return
            if f"_{address}_attributes" in device_map:
                attribute_map = device_map[f"_{address}_attributes"]
                yield from [
                    (".".join([address, attr]), a)
                    for attr, a in attribute_map.items()
                ]
            if accessor is not None:
                yield (address, accessor)

        def _meta(device, pv_head, d_type):
            for pv_tail in self.address_map.get(pv_head, [None]):
                if pv_tail is None:
                    continue
                accessor_names = _get_accessors(d_type, pv_tail)
                yield from [PKDict(
                        device_name=device,
                        cs_address=_DELIM.join([pv_head, address]),
                        accessor_name=accessor
                ) for address, accessor in accessor_names]

        self.accessor_map = slac_db.io.read_dict(_ACCESSOR_YAML)
        self.accessor_meta = list(_build())

    def _address_map(self):
        """Create an address map where keys are PV heads
        and values are lists of associated address tails.

        Sets:
            self.address_map
        """
        def _parse(names, addr_length):
            names = list(reversed(sorted(names)))
            while names:
                yield _parse_group(names, addr_length)
            

        def _parse_group(names, addr_length):
            h, t = _split_one(names.pop(), addr_length)
            rv = [t]
            while names:
                next_h, next_t = _split_one(names[-1], addr_length)
                if next_h != h:
                    break
                names.pop()
                rv.append(next_t)
            return h, rv

        def _split_one(name, addr_length):
            p = name.split(_DELIM)
            return _DELIM.join(p[:addr_length]), _DELIM.join(p[addr_length:])

        # Addresses with 3 units (AAA:BBB:CCC:)
        self.address_map = dict(
            _parse(
                slac_db.directory_service.get_all_addresses(), 3
            )
        )

        # Addresses with 4 units (AAA:BBB:CCC:DDD)
        self.address_map.update(
            dict(
                _parse(
                    slac_db.directory_service.get_all_addresses(), 4
                )
            )
        )

    def _area_map(self):
        """Creates a list of tuples with beampaths and their member areas.

        Sets:
            self.area_map
        """
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

    def _devices(self):
        """Creates a list of devices and their basic meta.

        Sets:
            self.devices
            self.device_name
        """
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
                yield yv

        self.devices = [device for device in _parse_device()]
        self.device_names = {d["device_name"] for d in self.devices}

    def _device_meta(self):
        """Indexes all device meta by type, and stores their values.

        Sets:
            self.device_meta
            self.device_meta_float
            self.device_meta_string        
        """
        def _get_meta_float(device_name, device_type, row):
            meta = _DEVICE_META_MAP.get(device_type, []) + _DEFAULT_DEVICE_META
            for column, meta_name in meta:
                yv = {
                    "device_name": device_name,
                    "device_meta_name": meta_name,
                    "meta_value": row[column],
                }
                if None in yv.values():
                    continue
                yield yv
        
        def _parse_meta_float():
            for r in slac_db.oracle.get_all_rows():
                if r["element"] not in self.device_names:
                    continue
                yield from _get_meta_float(r["element"], r["keyword"], r)

        def _fixup_string(value):
            return yaml.safe_dump(value)

        def _parse_meta_string(device_name, meta):
            for meta_name, value in meta.items():
                yv = {
                    "device_name": device_name,
                    "device_meta_name": meta_name,
                    "meta_value": _fixup_string(value)
                }
                if None in yv.values():
                    continue
                yield yv

        def _parse_yaml():
            string_meta = slac_db.io.read_dict(_STRING_META_LOC)
            for device_name, meta in string_meta.items():
                if device_name in self.device_names:
                    yield from _parse_meta_string(device_name, meta)

        self.device_meta_float = [m for m in _parse_meta_float()]
        self.device_meta = [
            {
                "device_name": m["device_name"],
                "device_meta_name": m["device_meta_name"],
                "meta_type": "float"
            } for m in self.device_meta_float
        ]
        self.device_meta_string = [m for m in _parse_yaml()]
        self.device_meta = self.device_meta + [
            {
                "device_name": m["device_name"],
                "device_meta_name": m["device_meta_name"],
                "meta_type": "string"
            } for m in self.device_meta_string            
        ]
