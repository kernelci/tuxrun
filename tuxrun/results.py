# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import logging
import re
from datetime import datetime
from xml.etree import ElementTree

import yaml

from tuxrun.yaml import yaml_load

LOG = logging.getLogger("tuxrun")
PATTERN = re.compile(r"^(\d+_)")
BOARD_LEVELS = ["target", "feedback"]
NOT_XML = re.compile("[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")


def xml_text(value) -> str:
    return NOT_XML.sub("", str(value))


def next_index(lines, text, start=0):
    for index in range(start, len(lines)):
        if text in str(lines[index].get("msg")):
            return index
    return None


def excerpt_line(entry):
    return f"[{entry.get('dt')}] {entry['msg']}"


def junit_cases(cases):
    for case, test in cases.items():
        if "result" in test:
            yield case, test
        else:
            for label, labelled in test.items():
                yield f"{case}.{label}", labelled


def junit_testcase(suite, name, test):
    case = ElementTree.Element(
        "testcase", classname=xml_text(suite), name=xml_text(name)
    )
    if test.get("duration"):
        case.set("time", xml_text(test["duration"]))
    result = test.get("result")
    if result == "fail":
        ElementTree.SubElement(case, "failure", message="fail")
    elif result == "skip":
        ElementTree.SubElement(case, "skipped")
    elif result != "pass":
        ElementTree.SubElement(case, "error", message=xml_text(result))
    lines = list(test.get("log_excerpt", []))
    if "measurement" in test:
        lines.insert(0, f"{test['measurement']} {test.get('units', '')}".strip())
    if lines:
        out = ElementTree.SubElement(case, "system-out")
        out.text = xml_text("\n".join(lines))
    return case


def junit_testsuite(name, cases, time):
    suite = ElementTree.Element("testsuite", name=xml_text(name))
    if time:
        suite.set("time", xml_text(time))
    suite.extend(cases)
    suite.set("tests", str(len(cases)))
    for tag, attribute in [
        ("failure", "failures"),
        ("error", "errors"),
        ("skipped", "skipped"),
    ]:
        suite.set(attribute, str(sum(1 for c in cases if c.find(tag) is not None)))
    return suite


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
        self.__log_lines__ = []
        self.__late_signal__ = None
        self.__first_dt__ = None
        self.__last_dt__ = None

    def parse(self, line):
        try:
            data = yaml_load(line)
        except yaml.YAMLError:
            LOG.debug(line)
            return
        if not data or not isinstance(data, dict):
            LOG.debug(line)
            return
        if data.get("lvl") in BOARD_LEVELS and not self.add_late_signal(data):
            self.__log_lines__.append(data)
        if data.get("dt"):
            self.__first_dt__ = self.__first_dt__ or data["dt"]
            self.__last_dt__ = data["dt"]
        if data.get("lvl") != "results":
            return

        test = data.get("msg")
        if not {"case", "definition"}.issubset(test.keys()):
            LOG.debug(line)
            return

        definition = re.sub(PATTERN, "", test.pop("definition"))
        raw_case = test.pop("case")
        case = re.sub(PATTERN, "", raw_case)
        self.__late_signal__ = None
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
            if "starttc" in test and "endtc" in test:
                test["log_excerpt"] = self.log_excerpt(raw_case, test)

        if test["result"] == "fail":
            self.__ret__ = 1

        return (definition, case, test)

    def log_excerpt(self, case, test):
        lines = self.__log_lines__
        if test["starttc"] == test["endtc"]:
            signal = f"<LAVA_SIGNAL_TESTCASE TEST_CASE_ID={case} "
            first = last = next_index(lines, signal)
            if first is None:
                lines.clear()
                # LAVA logs a line when its newline comes, that can be after the result
                self.__late_signal__ = (signal, test)
                return []
        else:
            first = next_index(lines, f"<LAVA_SIGNAL_STARTTC {case}>")
            if first is None:
                lines.clear()
                return []
            last = next_index(lines, f"<LAVA_SIGNAL_ENDTC {case}>", first)
            if last is None:
                next_start = next_index(lines, "<LAVA_SIGNAL_STARTTC ", first + 1)
                last = len(lines) - 1 if next_start is None else next_start - 1
            else:
                self.drop_shell_signal(case, last)
        excerpt = [excerpt_line(entry) for entry in lines[first : last + 1]]
        # The board can already be at the next test cases, keep their lines
        del lines[: last + 1]
        return excerpt

    def drop_shell_signal(self, case, endtc):
        lines = self.__log_lines__
        signal = f"<LAVA_SIGNAL_TESTCASE TEST_CASE_ID={case} "
        index = next_index(lines, signal, endtc + 1)
        if index is None:
            self.__late_signal__ = (signal, None)
        else:
            del lines[index]

    def add_late_signal(self, data):
        if self.__late_signal__ is None:
            return False
        signal, test = self.__late_signal__
        if signal not in str(data.get("msg")):
            return False
        if test is not None:
            test["log_excerpt"].append(excerpt_line(data))
        self.__late_signal__ = None
        return True

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

    def elapsed(self):
        if not self.__first_dt__:
            return None
        try:
            first = datetime.fromisoformat(self.__first_dt__)
            last = datetime.fromisoformat(self.__last_dt__)
            return f"{(last - first).total_seconds():.2f}"
        except (TypeError, ValueError):
            return None

    def suite_time(self, suite, elapsed):
        if suite == "lava":
            return elapsed
        return self.data.get("lava", {}).get(suite, {}).get("duration")

    def junit(self) -> str:
        root = ElementTree.Element("testsuites")
        elapsed = self.elapsed()
        if elapsed:
            root.set("time", elapsed)
        for suite, cases in self.data.items():
            testcases = [
                junit_testcase(suite, name, test) for name, test in junit_cases(cases)
            ]
            time = self.suite_time(suite, elapsed)
            root.append(junit_testsuite(suite, testcases, time))
        for suite in self.__tests__:
            if suite not in self.data:
                missing = junit_testcase(suite, suite, {"result": "no results"})
                time = self.suite_time(suite, elapsed)
                root.append(junit_testsuite(suite, [missing], time))
        return ElementTree.tostring(root, encoding="unicode", xml_declaration=True)
