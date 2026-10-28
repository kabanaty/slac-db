# slac-db learning guide

A step-by-step path through the codebase, ordered so each stage builds on the last.
Each stage has files to read and something to try. Budget roughly half a day in total.

Run everything from the repo root, so `import slac_db` picks up this checkout and not the
shared AFS install (check with `python -c "import slac_db; print(slac_db.__file__)"`).

---

## The big picture

slac-db answers questions like "which screens are in DIAG0?" or "what's the image PV for
OTRDG02?" from local SQLite files, without needing Oracle or EPICS at query time.

```
Oracle (V_LCLS_ELEMENTS_DIAG)        MEME directory service (PVA)
        │                                   │
        ▼                                   ▼
 lcls_elements.csv                 every PV in the control system
        │  create.oracle_db()               │  create.directory_service_db()
        ▼                                   ▼
 lcls_elements.sqlite3             directory_service_pvs.sqlite3
        └──────────────┬────────────────────┘
                       │  create.device_db()   (+ accessor_names.yaml, *_metadata.yaml)
                       ▼
                device.sqlite3   ◄── slac_db.device  (the API you'll normally use)
                       │
                       ▼  db_to_yaml.write()
           package_data/yaml/<AREA>.yaml   (exported per-area YAML)
```

Three layers:

| Layer | Modules | Role |
|---|---|---|
| Query API | `device.py` | Everyday lookups against `device.sqlite3` |
| Source DBs | `element_tables.py`, `directory_service.py` | Thin wrappers over the two input DBs |
| Builders | `create/*.py` | Rebuild the SQLite files from Oracle, MEME and YAML |

Older code that predates the SQLite design still exists: `__init__.py` (`get_device`,
`get_yaml`), `generate.py`, `write.py`, `metadata.py` and `controls_information.py`. These
work from the CSV and the per-area YAML. Learn them last.

---

## Stage 1: Use the API (30 min)

**Read:** [slac_db/device.py](slac_db/device.py), lines 1–242 (the public functions only).

**Try** in a notebook or REPL:

```python
import slac_db.device as d

d.get_all_areas()[:10]
d.get_devices(area="DIAG0", device_type="PROF")        # ['OTRDG02', 'OTRDG04']
d.get_attribute("OTRDG02", "cs_name")                   # 'OTRS:DIAG0:420'
d.get_all_accessors("OTRDG02")                          # friendly name -> PV
len(d.get_all_addresses("OTRDG02"))                     # every PV under the prefix
d.get_all_meta("WS04")                                  # metadata from YAML + Oracle
d.get_device_from_cs_name("QUAD:IN20:425")              # 'QE01'
d.get_beampath("CU_HXR", device_type="QUAD")[:5]        # ordered by Z
```

**Understand:**
- Devices are keyed by their **MAD name** (`device_name`, e.g. `QE01`).
- `cs_name` is the EPICS prefix (`QUAD:IN20:425`). A `cs_address` is one full PV.
- `addresses` holds every PV under the prefix. `accessors` is the curated subset with
  friendly names.
- Inactive devices are hidden unless you pass `include_inactive=True`.

**Check yourself:** why does `get_devices` return devices in beamline order? (Look for
`sum_l_meters`.)

---

## Stage 2: The schema and the DB plumbing (30 min)

**Read:** [slac_db/device.py:287-354](slac_db/device.py#L287-L354), the `_init_db` schema
and `_session`.

**Understand:**
- The schema is a `PKDict` passed to `pykern.sql_db.Meta`. Column specs are strings like
  `"str 64 primary_key foreign"`.
- There are 8 tables: `areas`, `beampaths`, `devices`, `device_meta` plus the
  `_float`/`_string` value tables, `addresses`, and `accessors`.
- `_meta` is a module-level singleton created on the first query. Every function does
  `with _session() as s:` and builds SQLAlchemy queries against `s.t.<table>`.
- `element_tables.py` and `directory_service.py` follow exactly the same pattern. Skim
  both and notice how similar they are.

**Try:** open the DB directly and compare it with what the API returns:

```bash
sqlite3 slac_db/package_data/device.sqlite3 ".tables"
sqlite3 slac_db/package_data/device.sqlite3 \
  "select * from accessors where device_name='OTRDG02' limit 5"
```

**Check yourself:** `get_all_meta` joins three tables. Why are meta values split into
float and string tables, and why does it call `yaml.safe_load` on string values?

---

## Stage 3: Where PVs come from (45 min)

**Read, in order:**
1. [slac_db/create/meme_names.py](slac_db/create/meme_names.py): pulls every PV from MEME
   and stores it under its first three `:`-separated fields as the `head`.
2. [slac_db/directory_service.py:58-86](slac_db/directory_service.py#L58-L86):
   `get_addresses`, which matches a device to PVs using its Oracle `control system name`.
   Note the 4-field "instance" case.
3. [slac_db/create/lcls_elements.py](slac_db/create/lcls_elements.py): CSV →
   `lcls_elements.sqlite3`, and the `ORACLE_TO_YAML_TYPE_MAP`.

**Understand:** a device gets PVs only when its Oracle `control system name` exactly matches
the first three fields of those PVs. This explains most "why does device X have no PVs"
questions.

**Try:** compare the snapshot with live MEME for one device. `get_meme_pvs` in
`camera.ipynb` does the live lookup:

```python
import slac_db.directory_service as ds
snap = ds.get_addresses("OTRDG02")
live = get_meme_pvs("OTRDG02")
set(live) - set(snap), set(snap) - set(live)
```

MEME is reached over **PV Access** (`EPICS_PVA_ADDR_LIST`), not CA.

---

## Stage 4: Building the device DB (1 hr)

This is the core of the codebase, so take your time here.

**Read:** [slac_db/create/device.py](slac_db/create/device.py) top to bottom.

**Follow `_Parser.__init__`** and trace where each table's rows come from:

| Table | Built by | Source |
|---|---|---|
| `devices` | `_device` | Oracle rows; skipped if any field is empty or the name contains `:` |
| `areas`, `beampaths` | inline in `__init__`, `_beampaths` | Oracle `area` / `beampath` columns |
| `device_meta_float` | `_device_meta_float` | Oracle columns listed in `DEVICE_META_MAP` |
| `device_meta_string` | `_device_meta_string` | `*_area_metadata.yaml`, merged with per-device `*_metadata.yaml` |
| `addresses` | `_address_meta` | `directory_service.get_addresses` |
| `accessors` | `_accessor_meta` | addresses × `accessor_names.yaml`, plus `_overrides` |

**Then read the YAML inputs:**
- [package_data/accessor_names.yaml](slac_db/package_data/accessor_names.yaml): device type
  → PV suffix → accessor name. Note the `[SOLE, QUAD, ...]:` multi-key syntax, handled by
  `io.read_dict` in [slac_db/io.py](slac_db/io.py). Also note the `_overrides` section and
  `_<suffix>_attributes`.
- [package_data/wire_area_metadata.yaml](slac_db/package_data/wire_area_metadata.yaml) and
  [wire_metadata.yaml](slac_db/package_data/wire_metadata.yaml): area defaults and
  per-device overrides.

**Try:** add a fake accessor and rebuild. This needs no Oracle or MEME access; revert
afterwards with `git checkout`.

```bash
# 1. under PROF: in accessor_names.yaml add e.g.   ALPHA_X: test_alpha_x
python -c "import slac_db.create as c; c.device_db()"      # fresh process required
python -c "import slac_db.device as d; print(d.get_all_accessors('OTRDG02').get('test_alpha_x'))"
git checkout slac_db/package_data/accessor_names.yaml slac_db/package_data/device.sqlite3
```

**Gotchas:**
- `recreate()` refuses to run if the process has already opened that DB. Always rebuild in
  a fresh Python process.
- Rebuilding deletes the old file first, so a crash mid-build leaves no DB.
- Klystrons are `LCAV` in Oracle but are re-typed as `KLYS` when their `cs_name` contains
  `KLYS` ([create/device.py:122](slac_db/create/device.py#L122)).

**Check yourself:** an override accessor points at a PV under another device's prefix. Does
that PV also appear in `get_all_addresses()` for the device? Why not?

---

## Stage 5: Tests (30 min)

**Read:** [tests/test_device.py](tests/test_device.py), then skim
[tests/test_element_tables.py](tests/test_element_tables.py) and
[tests/test_directory_service.py](tests/test_directory_service.py).

**Run:**

```bash
pip install deepdiff          # needed by test_db_to_yaml.py; listed in the [dev] extra
python -m pytest tests -q
```

The tests run against the real committed SQLite files, so they double as working examples
of the API. CI ([.github/workflows/tests.yml](.github/workflows/tests.yml)) checks out with
`lfs: true` for this reason.

**Try:** write a test for something you learned, e.g. that every accessor PV for `OTRDG02`
starts with its `cs_name`, or that `get_device_from_cs_name` round-trips with
`get_attribute(..., "cs_name")`.

---

## Stage 6: YAML export and legacy code (as needed)

Read these only when you need them.

- [slac_db/db_to_yaml.py](slac_db/db_to_yaml.py): `build()` and `write()` regenerate
  `package_data/yaml/<AREA>.yaml` from `device.sqlite3`. `test_db_to_yaml.py` checks that
  the output matches the committed YAML.
- [slac_db/\_\_init\_\_.py](slac_db/__init__.py): `get_device` and `get_yaml` read those
  per-area YAMLs (used by lcls-tools-style consumers).
- [slac_db/generate.py](slac_db/generate.py), [write.py](slac_db/write.py),
  [metadata.py](slac_db/metadata.py), [controls_information.py](slac_db/controls_information.py):
  the original generator, which reads the CSV and queries MEME directly. It has a CLI:
  `python -m slac_db.write -m overwrite|greedy|lazy`.
- [slac_db/oracle_remote.py](slac_db/oracle_remote.py): direct Oracle connection (works
  only on production).

---

## Known rough edges (good first fixes)

- `create/lcls_elements.py:36` calls `get_connection()` without importing it, so refreshing
  the CSV from Oracle raises `NameError`, and the broad `except` hides it.
- The `get_all_addresses` docstring says "Get all accessors".
- `recreate()` in `device.py` says the parser needs `device_address_meta`, but it checks
  for `address_meta`.

---

## Quick reference

```bash
# rebuild everything (each in a fresh process, in this order)
python -c "import slac_db.create as c; c.oracle_db()"              # CSV -> lcls_elements
python -c "import slac_db.create as c; c.directory_service_db()"   # MEME -> PVs (slow, PVA)
python -c "import slac_db.create as c; c.device_db()"              # -> device.sqlite3
python -c "import slac_db.db_to_yaml as y; y.write()"              # -> per-area YAML

# fetch LFS databases without SSH
git -c lfs.url=https://github.com/slaclab/slac-db.git/info/lfs lfs pull
```
