# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import logging
import re

import yaml

from tuxrun.yaml import yaml_load

LOG = logging.getLogger("tuxrun")
PATTERN = re.compile(r"^(\d+_)")


class Results:
    def __init__(self, tests, artefacts):
        self.__artefacts__ = artefacts.copy()
        # Add overlays
        for index, overlay in enumerate(self.__artefacts__.get("overlays", [])):
            self.__artefacts__[f"overlay-{index:02}"] = overlay[0]
        self.__data__ = {}
        self.__metadata__ = {}
        self.__post_processed = False
        self.__tests__ = ["lava"] + [t.name for t in tests]
        self.__ret__ = 0

    def parse(self, line):
        try:
            data = yaml_load(line)
        except yaml.YAMLError:
            LOG.debug(line)
            return
        if not data or not isinstance(data, dict):
            LOG.debug(line)
            return
        if data.get("lvl") != "results":
            return

        test = data.get("msg")
        if not {"case", "definition"}.issubset(test.keys()):
            LOG.debug(line)
            return

        definition = re.sub(PATTERN, "", test.pop("definition"))
        case = re.sub(PATTERN, "", test.pop("case"))
        # download action can be duplicated
        if (
            definition == "lava"
            and case.endswith("-download")
            and test.get("extra", {}).get("label")
        ):
            label = test["extra"]["label"]
            label = label[len("rootfs.") :] if label.startswith("rootfs.") else label
            self.__data__.setdefault(definition, {}).setdefault(case, {})[label] = test
            if label in self.__artefacts__:
                self.__data__[definition][case][label]["url"] = (
                    self.__artefacts__[label]
                    if isinstance(self.__artefacts__[label], str)
                    else (
                        None
                        if not self.__artefacts__[label]
                        else self.__artefacts__[label][0]
                    )
                )
        else:
            self.__data__.setdefault(definition, {})[case] = test
        if test["result"] == "fail":
            self.__ret__ = 1

        return (definition, case, test)

    def __post_process(self):
        if self.__post_processed:
            return
        self.__post_processed = True

        if set(self.__tests__) != set(self.__data__.keys()):
            self.__ret__ = 2

        # Add qemu info
        if self.__data__.get("lava", {}).get("execute-qemu", {}).get("extra"):
            self.__metadata__ = {
                "arch": self.__data__["lava"]["execute-qemu"]["extra"].get("job_arch"),
                "host_arch": self.__data__["lava"]["execute-qemu"]["extra"].get(
                    "host_arch"
                ),
                "qemu_version": self.__data__["lava"]["execute-qemu"]["extra"].get(
                    "qemu_version"
                ),
            }
        # Add artefacts with url and checksum
        self.__metadata__["artefacts"] = {}
        for lava_key in ["file-download", "http-download"]:
            for k, v in self.__data__.get("lava", {}).get(lava_key, {}).items():
                if "url" in v:
                    self.__metadata__["artefacts"][k] = {
                        "url": v["url"],
                        "sha256sum": v["extra"]["sha256sum"],
                    }

        # Add test durations
        self.__metadata__["durations"] = {"tests": {}}
        for test in self.__tests__[1:]:
            self.__metadata__["durations"]["tests"][test] = (
                self.__data__.get("lava", {}).get(test, {}).get("duration", 0)
            )
        self.__metadata__["durations"]["tests"]["boot"] = (
            self.__data__.get("lava", {}).get("login-action", {}).get("duration", 0)
        )

    @property
    def data(self):
        self.__post_process()
        return self.__data__

    @property
    def metadata(self):
        self.__post_process()
        return self.__metadata__

    def ret(self):
        self.__post_process()
        return self.__ret__
