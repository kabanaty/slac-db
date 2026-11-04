import slac_db.directory_service

def to_directory_service_db():
    """Build  device DB with SQLAlchemy."""
    return slac_db.directory_service.recreate(_Parser())


class _Parser:
    """Container for DB row data."""

    def __init__(self):
        self.areas = set()
        self.types = set()
        self.headers = dict()
        self.addresses = list()
        self._get_from_meme()

    def _get_from_meme(self):
        import meme.names

        address_list = meme.names.list_pvs("%", timeout=600)
        address_list += _list_facet_pvs("%", timeout=600)
        # A PV in both directory services would break the addresses primary key. use from dict to grab first hit
        for a in dict.fromkeys(address_list):
            part = a.split(":")
            if len(part) < 4:
                continue
            head = ":".join(part[0:3])
            entry = {
                "head": head,
                "type": part[0],
                "area": part[1],
                "unit": part[2],
            }
            self.types.add(entry["type"])
            self.areas.add(entry["area"])
            self.headers[head] = entry
            self.addresses.append({"head": head, "address": a})

        self.types = [{"type": t} for t in sorted(self.types)]
        self.areas = [{"area": t} for t in sorted(self.areas)]
        self.headers = [i for h, i in sorted(self.headers.items())]


def _list_facet_pvs(pattern, timeout=None):
    """Get PVs matching pattern from the FACET directory service.

    Uses its own PVA context so the environment's address list does not matter.

    Args:
        pattern (str): Directory service pattern, e.g. 'QUAD:LI13:701:%'.
        timeout (float): RPC timeout in seconds.
    Returns:
        list of str: Matching PV names.
    """
    from p4p.client.thread import Context
    from p4p.nt import NTURI
    _FACET_DS_ADDR = "mccas0:6078"
    ctx = Context(
        "pva",
        useenv=False,
        conf={"EPICS_PVA_ADDR_LIST": _FACET_DS_ADDR, "EPICS_PVA_AUTO_ADDR_LIST": "NO"},
    )
    try:
        request = NTURI([("name", "s")]).wrap("ds", scheme="pva", kws={"name": pattern})
        return list(ctx.rpc("ds", request, timeout=timeout).value.name)
    finally:
        ctx.close()
