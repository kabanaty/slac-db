import re

import slac_db.element_tables

# FACET names live in their own directory service, separate from LCLS.
DS_ADDR = "mccas0:6078"

# COMMON is deferred for now.
AREAS = (
    "INJ",
    "L0F",
    "DL10",
    "L1F",
    "BC11_1",
    "BC11_2",
    "L2F",
    "BC14_1",
    "BC14E",
    "BC14P",
    "BC14_2",
    "L3F_1",
    "L3F_2",
    "SCAV",
    "BC20",
    "FF20",
    "EXPT20",
    "SPECT2",
    "ELECTR",
    "POSITR",
    "PAX BY",
    "PAX CH",
    "LI20",
    "S10-EL",
    "S10-PO",
)

_SECTOR = re.compile(r"[A-Z]{2}\d\d")
_ctx = None


def control_system_names():
    """Control system names of devices in FACET areas.

    Rows are filtered the same way as slac_db.create.device builds devices.

    Returns:
        list of str: Sorted, unique control system names.
    """
    return sorted(
        {
            r["control system name"]
            for r in slac_db.element_tables.get_all_rows()
            if r["area"] in AREAS
            and r["element"]
            and r["keyword"]
            and r["control system name"]
            and ":" not in r["element"]
        }
    )


def query_target(cs_name):
    """Name to search for in the FACET directory service.

    The FACET directory service only knows type-first names
    ('QUAD:LI13:701'), but Oracle stores many FACET devices
    area-first ('LI13:QUAD:701'). Area-first names have their first
    two fields swapped; type-first names are unchanged.

    Args:
        cs_name (str): Oracle control system name.
    Returns:
        str: Type-first control system name.
    """
    if not _is_area_first(cs_name):
        return cs_name
    return _swap(cs_name)


def list_pvs(pattern, timeout=60):
    """Get PVs matching pattern from the FACET directory service.

    Uses its own PVA context so the environment's address list
    does not matter.

    Args:
        pattern (str): Directory service pattern, e.g. 'QUAD:LI13:701:%'.
        timeout (float): RPC timeout in seconds.
    Returns:
        list of str: Matching PV names.
    """
    from p4p.client.thread import Context
    from p4p.nt import NTURI

    global _ctx
    if _ctx is None:
        _ctx = Context(
            "pva",
            useenv=False,
            conf={"EPICS_PVA_ADDR_LIST": DS_ADDR, "EPICS_PVA_AUTO_ADDR_LIST": "NO"},
        )
    request = NTURI([("name", "s")]).wrap("ds", scheme="pva", kws={"name": pattern})
    return list(_ctx.rpc("ds", request, timeout=timeout).value.name)


def find_pvs(pattern):
    """Get PVs matching an Oracle-style pattern from the FACET directory service.

    Area-first patterns are searched type-first and each result is
    renamed back, so 'LI13:QUAD:701:BACT' finds 'QUAD:LI13:701:BACT'
    and returns 'LI13:QUAD:701:BACT'.

    Args:
        pattern (str): Name or pattern in Oracle form.
    Returns:
        list of str: Matching PV names in Oracle form.
    """
    if not _is_area_first(pattern):
        return list_pvs(pattern)
    return [_swap(pv) for pv in list_pvs(_swap(pattern))]


def device_pvs(cs_name):
    """Get all PVs for a device under its Oracle control system name.

    Args:
        cs_name (str): Oracle control system name.
    Returns:
        list of str: PV names that start with cs_name.
    """
    return find_pvs(cs_name + ":%")


def _is_area_first(name):
    p = name.split(":")
    return len(p) >= 3 and bool(_SECTOR.fullmatch(p[0]))


def _swap(name):
    p = name.split(":")
    p[0], p[1] = p[1], p[0]
    return ":".join(p)
