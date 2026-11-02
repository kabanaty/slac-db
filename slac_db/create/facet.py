import re

import sqlalchemy

import slac_db.directory_service
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


def add_to_directory_service_db():
    """Add FACET PVs to the existing directory_service sqlite3 database.

    PVs are stored under their Oracle control system names, so
    slac_db.create.device_db() finds them unchanged. FACET rows from
    a previous run are replaced; all other rows are left alone.

    Returns:
        int: Number of addresses added.
    """
    headers = {}
    addresses = {}
    for cs in control_system_names():
        for pv in device_pvs(cs):
            part = pv.split(":")
            if len(part) < 4:
                continue
            head = ":".join(part[0:3])
            area, kind = (part[0], part[1]) if _is_area_first(head) else (part[1], part[0])
            headers[head] = {"head": head, "type": kind, "area": area, "unit": part[2]}
            addresses[pv] = {"head": head, "address": pv}
    with slac_db.directory_service._session() as s:
        t = s.t
        s.execute(t.addresses.delete().where(t.addresses.c.head.in_(headers)))
        s.execute(t.headers.delete().where(t.headers.c.head.in_(headers)))
        for table, rows in (
            (t.types, [{"type": k} for k in {h["type"] for h in headers.values()}]),
            (t.areas, [{"area": a} for a in {h["area"] for h in headers.values()}]),
            (t.headers, list(headers.values())),
            (t.addresses, list(addresses.values())),
        ):
            if rows:
                s._conn.execute(sqlalchemy.insert(table).prefix_with("OR IGNORE"), rows)
    return len(addresses)


def _is_area_first(name):
    p = name.split(":")
    return len(p) >= 3 and bool(_SECTOR.fullmatch(p[0]))


def _swap(name):
    p = name.split(":")
    p[0], p[1] = p[1], p[0]
    return ":".join(p)
