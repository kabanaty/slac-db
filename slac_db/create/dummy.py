import slac_db.config
import slac_db.device
from pykern.pkcollections import PKDict

def to_dummy_db():
    """Recreate device db."""
    slac_db.device._db_path = slac_db.config.package_data().joinpath("dummy.sqlite3")
    p = _Parser()
    slac_db.device.recreate(p)

class _Parser(PKDict):
    """Add in DEV_CAMERA which is 13SIM1:cam1
    """


    def __init__(self):
        def _dev_camera_accessors(name, extra_accessors):
            for x in (
                ("acquire", "13SIM1:cam1:Acquire", 0),
                ("image", "13SIM1:image1:ArrayData", 0),
                ("n_bits", "13SIM1:cam1:N_OF_BITS", 0),
                ("n_col", "13SIM1:cam1:SizeX", 0),
                ("n_row", "13SIM1:cam1:SizeY", 0),
            ) + extra_accessors:
                yield PKDict(
                    zip(
                        (
                            "device_name",
                            "accessor_name",
                            "cs_address",
                        ),
                        ((name,) + x),
                    ),
                )

        name = "DEV_CAMERA"
        self.area_map = [PKDict(area="DEV_AREA", beampath="DEV_BEAM_PATH")]
        self.areas = [PKDict(area=m.area) for m in self.area_map]
        self.devices = [
            PKDict(
                device_name=name,
                area="DEV_AREA",
                device_type="PROF",
                cs_name="13SIM1",
                is_active=True,
            )
        ]
        self.device_meta_string = None
        self.device_meta_float = [
            PKDict(
                device_name=name,
                device_meta_name="sum_l_meters",
                meta_value="0.614",
            ),
        ]
        self.device_meta = [
            PKDict(
                device_name=name,
                device_meta_name="sum_l_meters",
                meta_type="float",
            )
        ]
        self.accessor_meta = list(_dev_camera_accessors(name, ()))
        self.address_meta = self.accessor_meta
