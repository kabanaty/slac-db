# FACET PVs in slac-db: working notes

Status as of 2026-10-28. Goal: get PVs for FACET devices (areas BC20, FF20, EXPT20, LI20)
into slac-db, using MEME over PVA.

## TL;DR

- FACET devices currently have **no PVs** in `device.sqlite3`: 73 devices across BC20,
  FF20, EXPT20 and LI20, 0 of them with addresses.
- That's because `create/meme_names.py` only queries the **LCLS** directory service, which
  doesn't know FACET names.
- FACET names are in a **second directory service** on `mccas0:6078`, which is reachable
  from dev-srv09.
- The two services can't be combined through `EPICS_PVA_ADDR_LIST`; each needs its own
  p4p `Context`.
- FACET `ds` names are **type-first** (`LGPS:LI20:3011`), while Oracle `cs_name`s are
  **area-first** (`LI20:LGPS:3011`). These are different live CA channels with different
  values.

## Environment (dev-srv09)

Use `envSet_prodOnDev.bash` (the `mprod` alias in `~/.bashrc`). With it:

| Access | LCLS | FACET |
|---|---|---|
| CA (`caget`) | ✅ | ✅ both `LI20:LGPS:3011:BACT` and `LGPS:LI20:3011:BACT` |
| PVA (`pvget`/p4p) for normal PVs | ✅ | ❌ FACET names aren't served over PVA from here |
| MEME (`meme.names`) | ✅ | ❌ returns 0 for FACET names |

```
EPICS_CA_ADDR_LIST="lcls-prod01:5068 lcls-prod01:5063 mcc-dmz"
EPICS_CA_SERVER_PORT=5068
EPICS_PVA_ADDR_LIST="lcls-prod01:5168 lcls-prod01:5063 mcc-dmz mccas0.slac.stanford.edu"
EPICS_PVA_AUTO_ADDR_LIST=NO
```

**Don't add `mccas0:6078` to `EPICS_PVA_ADDR_LIST`.** It answers searches for every name but
only supports RPC, so `pvget QUAD:IN20:425:BACT` then fails with "only channelRPC requests
are supported". MEME still picks the LCLS `ds` (you'll see "Duplicate PV name ds"), so it
gains nothing.

The default login environment (from `ENVS64.bash`) is a dev setup. MEME there returns far
fewer PVs (e.g. 60 vs 2844 for `OTRS:DIAG0:420`). **Never rebuild
`directory_service_pvs.sqlite3` without `mprod`**, or the DB silently shrinks.

The Jupyter kernel doesn't inherit `mprod` from a terminal. Either set `os.environ` before
importing `epics`/`p4p`/`meme`, or source it in `.bashrc`.

For reference, facet-srv01 uses `EPICS_PVA_ADDR_LIST="172.27.75.255 mccas0:6078 mcc-dmz"`.
`172.27.75.255` is a FACET-subnet broadcast address and doesn't work from dev-srv09.

## The two directory services

`meme.names` is a thin p4p RPC client: `Context('pva').rpc("ds", NTURI(name=pattern))`.
It uses one module-level context, built from the environment.

| PVA address | Contents | `QUAD:IN20:425:%` | `LGPS:LI20:3011:%` | `%` |
|---|---|---|---|---|
| `mccas0.slac.stanford.edu` (default port) | LCLS | 277 | 0 | ~1 M (current DB) |
| `mccas0:6078` | FACET / SLC | 0 | 63 | **2,407,763** |
| `mcc-dmz` | — | timeout | timeout | timeout |

Query either one explicitly (tested from dev-srv09):

```python
from p4p.client.thread import Context
from p4p.nt import NTURI

_DS = {
    "lcls":  Context("pva", useenv=False, conf={"EPICS_PVA_ADDR_LIST": "mccas0.slac.stanford.edu",
                                                 "EPICS_PVA_AUTO_ADDR_LIST": "NO"}),
    "facet": Context("pva", useenv=False, conf={"EPICS_PVA_ADDR_LIST": "mccas0:6078",
                                                 "EPICS_PVA_AUTO_ADDR_LIST": "NO"}),
}

def list_pvs(pattern, source="lcls", timeout=30):
    uri = NTURI([("name", "s")]).wrap("ds", scheme="pva", kws={"name": pattern})
    return list(_DS[source].rpc("ds", uri, timeout=timeout).value.name)

list_pvs("QUAD:IN20:425:%")                   # 277
list_pvs("LGPS:LI20:3011:%", source="facet")  # 63
list_pvs("QUAD:LI20:%", source="facet")       # 540
```

## Name-order mismatch (needs a decision)

| Source | Example | `BACT` via CA |
|---|---|---|
| Oracle `control system name` (slac-db `cs_name`) | `LI20:LGPS:3011` | `-72.1595` |
| FACET `ds` | `LGPS:LI20:3011` | `65464` |
| Oracle | `LI20:QUAD:2086` | `0.00043` |
| FACET `ds` | `QUAD:LI20:2086` | `0` |

Both forms connect over CA, but they're different channels. The type-first values look like
raw SLC, and the area-first ones like the EPICS-side records; this is unconfirmed. **Ask the
FACET controls folks which form to use.**

## Proposed change to slac-db (not started)

In `slac_db/create/meme_names.py` (`_Parser._get_from_meme`):

1. Keep the LCLS query as it is.
2. Add a FACET query against `mccas0:6078` with its own `Context`. Restrict the pattern to
   FACET areas (e.g. `%:LI20:%` returns 235,329 names) rather than `%` (2.4 M), so that
   `directory_service_pvs.sqlite3` (958 MB now) doesn't grow to several GB.
3. Choose one of:
   - **Map to Oracle form:** swap the first two fields (`LGPS:LI20:3011:X` →
     `LI20:LGPS:3011:X`) so the existing `head` matching in `directory_service.get_addresses`
     works unchanged. Only correct if the area-first PVs are the ones wanted and the suffix
     sets match.
   - **Keep FACET form:** store it as is, and teach `get_addresses` to also try the swapped
     head for FACET areas.
4. Rebuild under `mprod`, each in a fresh process:
   ```bash
   python -c "import slac_db.create as c; c.directory_service_db()"
   python -c "import slac_db.create as c; c.device_db()"
   python -c "import slac_db.db_to_yaml as y; y.write()"
   ```
5. Check: `slac_db.device.get_all_addresses("Q5FF")` should be non-empty, and
   `get_attribute("Q5FF", "cs_name") == "LI20:LGPS:3011"`.

## Related repo state and gotchas

- The LFS DBs were fetched over HTTPS because SSH to GitHub fails from dev-srv09:
  `git -c lfs.url=https://github.com/slaclab/slac-db.git/info/lfs lfs pull`.
  Pushing new LFS objects needs SSH working (`ssh -T git@github.com`).
- Old personal work: the `chris` branch was deleted, but commit `ff75dd0` ("backup...") still
  exists. Recover it with `git branch chris ff75dd0`. It has `cameras.yaml`,
  `.vscode/settings.json` and edits to `controls_information.py`, `device.py`, etc.
- Run Python from the repo root. Elsewhere, `import slac_db` picks up the shared AFS install.
- `create/lcls_elements.py:36` calls `get_connection()` without importing it, so a fresh
  Oracle CSV pull fails with `NameError`.
- When regenerated, the per-area YAMLs differ from the committed ones in BYP, DOG, EXT, L3B,
  L4B and SPD (devices that moved areas). Review the diff before committing.
- Diagnostic script: `~/pv_diag.sh` (CA/PVA/MEME probe, read-only). Probe scripts used
  here: `/tmp/dstest.py`, `/tmp/dstest2.py` (not kept).
- See also `LEARNING_GUIDE.md` for the codebase walkthrough.
