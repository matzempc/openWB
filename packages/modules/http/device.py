#!/usr/bin/env python3
""" Modul zum Auslesen von Alpha Ess Speichern, Zählern und Wechselrichtern.
"""
import re
import sys
from typing import Dict, List, Union

from helpermodules import log
from modules.common.abstract_device import AbstractDevice
from modules.common.component_context import SingleComponentUpdateContext
from modules.http import bat
from modules.http import counter
from modules.http import inverter


def get_default_config() -> dict:
    return {
        "name": "HTTP",
        "type": "http",
        "id": 0,
        "configuration":
        {
            "protocol": "http",
            "domain": "192.168.193.15"
        }
    }


http_component_classes = Union[bat.HttpBat, counter.HttpCounter, inverter.HttpInverter]


class Device(AbstractDevice):
    COMPONENT_TYPE_TO_CLASS = {
        "bat": bat.HttpBat,
        "counter": counter.HttpCounter,
        "inverter": inverter.HttpInverter
    }

    def __init__(self, device_config: dict) -> None:
        self._components = {}  # type: Dict[str, http_component_classes]
        try:
            self.device_config = device_config
        except Exception:
            log.MainLogger().exception("Fehler im Modul "+device_config["name"])

    def add_component(self, component_config: dict) -> None:
        component_type = component_config["type"]
        if component_type in self.COMPONENT_TYPE_TO_CLASS:
            domain = self.device_config["configuration"]["protocol"] + \
                "://" + self.device_config["configuration"]["domain"]
            self._components["component"+str(component_config["id"])] = self.COMPONENT_TYPE_TO_CLASS[component_type](
                component_config, domain)
        else:
            raise Exception(
                "illegal component type " + component_type + ". Allowed values: " +
                ','.join(self.COMPONENT_TYPE_TO_CLASS.keys())
            )

    def update(self) -> None:
        log.MainLogger().debug("Start device reading " + str(self._components))
        if self._components:
            for component in self._components:
                # Auch wenn bei einer Komponente ein Fehler auftritt, sollen alle anderen noch ausgelesen werden.
                with SingleComponentUpdateContext(self._components[component].component_info):
                    self._components[component].update()
        else:
            log.MainLogger().warning(
                self.device_config["name"] +
                ": Es konnten keine Werte gelesen werden, da noch keine Komponenten konfiguriert wurden."
            )


def read_legacy(argv: List[str]) -> None:
    COMPONENT_TYPE_TO_MODULE = {
        "bat": bat,
        "counter": counter,
        "inverter": inverter
    }
    component_type = argv[1]

    device_config = get_default_config()
    regex = re.search("(http[s]?)://([0-9.]+)", argv[2])
    device_config["configuration"]["protocol"] = regex.group(1)
    device_config["configuration"]["domain"] = regex.group(2)
    dev = Device(device_config)
    if component_type in COMPONENT_TYPE_TO_MODULE:
        component_config = COMPONENT_TYPE_TO_MODULE[component_type].get_default_config()
        if component_type == "bat":
            component_config["configuration"] = {
                "power_path": argv[2].replace(re.search("http[s]?://[0-9.]+", argv[2]).group(), ""),
                "imported_path": argv[3].replace(re.search("http[s]?://[0-9.]+", argv[3]).group(), ""),
                "exported_path": argv[4].replace(re.search("http[s]?://[0-9.]+", argv[4]).group(), ""),
                "soc_path": argv[5].replace(re.search("http[s]?://[0-9.]+", argv[5]).group(), "")
            }
            num = None
        elif component_type == "counter":
            component_config["configuration"] = {
                "power_all_path": argv[2].replace(re.search("http[s]?://[0-9.]+", argv[2]).group(), ""),
                "imported_path": argv[3].replace(re.search("http[s]?://[0-9.]+", argv[3]).group(), ""),
                "exported_path": argv[4].replace(re.search("http[s]?://[0-9.]+", argv[4]).group(), ""),
                "power_l1_path": argv[5].replace(re.search("http[s]?://[0-9.]+", argv[5]).group(), ""),
                "power_l2_path": argv[6].replace(re.search("http[s]?://[0-9.]+", argv[6]).group(), ""),
                "power_l3_path": argv[7].replace(re.search("http[s]?://[0-9.]+", argv[7]).group(), "")
            }
            num = None
        else:
            component_config["configuration"] = {
                "power_path": argv[2].replace(re.search("http[s]?://[0-9.]+", argv[2]).group(), ""),
                "counter_path": argv[3].replace(re.search("http[s]?://[0-9.]+", argv[3]).group(), "")
            }
            num = argv[4]
    else:
        raise Exception(
            "illegal component type " + component_type + ". Allowed values: " +
            ','.join(COMPONENT_TYPE_TO_MODULE.keys())
        )
    component_config["id"] = num
    dev.add_component(component_config)

    log.MainLogger().debug('Http Konfiguration: ' + str(component_config["configuration"]))

    dev.update()


if __name__ == "__main__":
    try:
        read_legacy(sys.argv)
    except Exception:
        log.MainLogger().exception("Fehler im HTTP Skript")