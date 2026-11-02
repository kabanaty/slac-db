import argparse
import collections.abc
import os

import yaml

import slac_db.config
import slac_db.create.facet
from slac_db.generate import YAMLGenerator


class YAMLWriter:
    def __init__(self, location=None, use_meme=True, suppress_warnings=False):
        if location is None:
            location = slac_db.config.yaml()
        self.out_location = location
        self.generator = YAMLGenerator(
            use_meme=use_meme, suppress_warnings=suppress_warnings
        )

    @property
    def areas(self) -> list[str]:
        return self.generator.areas

    def _is_area(self, area: str) -> bool:
        return area in self.generator.areas

    def _construct_yaml_contents(
        self, area: str, devices: list[str] = None
    ) -> dict[str, str]:
        if area not in self.generator.areas:
            raise RuntimeError(
                f"Area {area} provided is not a known machine area.",
            )
        file_contents = {}

        extractors = {
            "magnets": self.generator.extract_magnets,
            "screens": self.generator.extract_screens,
            "wires": self.generator.extract_wires,
            "lblms": self.generator.extract_lblms,
            "bpms": self.generator.extract_bpms,
            "tcavs": self.generator.extract_tcavs,
            "pmts": self.generator.extract_pmts,
            "toroids": self.generator.extract_toroids,
        }

        if devices is None:
            devices = list(extractors.keys())

        for k, v in extractors.items():
            if k in devices:
                device_data = v(area=area)
                if device_data:
                    file_contents[k] = device_data

        if file_contents:
            return file_contents
        return {}

    def _yaml_dump(self, area, output):
        filename = area + ".yaml"
        fullpath = os.path.join(self.out_location, filename)
        if output:
            with open(fullpath, "w") as file:
                yaml.safe_dump(output, file)

    def overwrite(
        self, area: str | None = "GUNB", devices: list[str] = None
    ) -> None:
        yaml_output = self._construct_yaml_contents(area=area, devices=devices)
        self._yaml_dump(area, yaml_output)

    def overwrite_facet(self, devices: list[str] = None) -> None:
        """Overwrite the FACET area YAMLs with PVs from the FACET
        directory service. Other areas are not touched.
        """
        query_pv = self.generator.query_pv
        self.generator.query_pv = slac_db.create.facet.find_pvs
        try:
            for a in slac_db.create.facet.AREAS:
                self.overwrite(a, devices)
        finally:
            self.generator.query_pv = query_pv

    def _get_current(self, area):
        area_location = self.out_location / (area + ".yaml")
        if not os.path.exists(area_location):
            return {}
        with open(area_location, "r") as file:
            res = yaml.safe_load(file)
        return res

    def _greedy_update(self, target, update):
        for k, v in update.items():
            if isinstance(v, collections.abc.Mapping):
                target[k] = self._greedy_update(target.get(k, {}), v)
            else:
                target[k] = v
        return target

    def greedy_write(
        self, area: str | None = "GUNB", devices: list[str] = None
    ) -> None:
        current = self._get_current(area)
        update = self._construct_yaml_contents(area=area, devices=devices)
        yaml_output = self._greedy_update(current, update)
        self._yaml_dump(area, yaml_output)

    def _lazy_update(self, target, update):
        for k, v in update.items():
            if isinstance(v, collections.abc.Mapping):
                target[k] = self._lazy_update(target.get(k, {}), v)
            else:
                if k not in target:
                    target[k] = v
        return target

    def lazy_write(
        self, area: str | None = "GUNB", devices: list[str] = None
    ) -> None:
        current = self._get_current(area)
        update = self._construct_yaml_contents(area=area, devices=devices)
        yaml_output = self._lazy_update(current, update)
        self._yaml_dump(area, yaml_output)


def write(mode="overwrite", devices=None, areas=None, location=None):
    yaml_writer = YAMLWriter(location=location)
    if areas is None:
        areas = yaml_writer.areas
    if type(areas) is not list:
        areas = [areas]
    match mode:
        case "overwrite":
            w = yaml_writer.overwrite
        case "greedy":
            w = yaml_writer.greedy_write
        case "lazy":
            w = yaml_writer.lazy_write


    for a in areas:
        w(a, devices)
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="YAML Writer")
    parser.add_argument(
        "-m",
        "--mode",
        choices=["overwrite", "greedy", "lazy"],
        default="overwrite",
        help=(
            "The YAML writing mode. 'overwrite' replaces the YAML with "
            "current data. 'greedy' adds new data and corrects old data. "
            "'lazy' adds new data and leaves old data alone. "
            "Default: %(default)s"
        ),
    )
    parser.add_argument(
        "--devices",
        nargs="+",
        help=(
            "The devices to read from lcls_elements.csv. Use this arg "
            "with --mode greedy or lazy to avoid deleting devices that "
            "aren't currently selected."
        ),
    )
    parser.add_argument(
        "--areas",
        nargs="+",
        help=(
            "The devices to read from lcls_elements.csv. Use this arg "
            "with --mode greedy or lazy to avoid deleting devices that "
            "aren't currently selected."
        ),
    )
    parser.add_argument(
        "--facet",
        action="store_true",
        help=(
            "Overwrite only the FACET area YAMLs, using the FACET "
            "directory service. Ignores --mode and --areas."
        ),
    )
    args = parser.parse_args()
    if args.facet:
        YAMLWriter().overwrite_facet(devices=args.devices)
    else:
        write(mode=args.mode, areas=args.areas, devices=args.devices)
