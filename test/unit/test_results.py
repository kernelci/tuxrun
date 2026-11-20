import json
import os
from pathlib import Path
from xml.etree import ElementTree

import pytest

from tuxrun.results import Results
from tuxlava.tests import Test  # type: ignore

BASE = (Path(__file__) / "..").resolve()


def test_returns_0_by_default():
    results = Results([], {})
    results.__data__ = {"lava": {}}
    assert results.ret() == 0


def gen_test(name, result, suite_name="mytestsuite"):
    return f'{{ "lvl": "results", "msg": {{"definition": "{suite_name}", "case": "{name}", "result": "{result}"}}}}'


def test_returns_0_with_no_failures():
    t1 = Test(timeout=None)
    t1.name = "mytestsuite"
    results = Results([t1], {})
    results.parse(gen_test("test1", "pass"))
    results.parse(gen_test("test2", "pass"))
    results.parse(gen_test("job", "pass", suite_name="lava"))
    assert results.ret() == 0


def test_returns_1_on_failure():
    results = Results([], {})
    results.parse(gen_test("test1", "pass", suite_name="lava"))
    results.parse(gen_test("test2", "fail", suite_name="lava"))
    assert results.ret() == 1


def test_returns_2_on_missing_test():
    t1 = Test(timeout=None)
    t1.name = "mytestsuite"
    results = Results([t1], {})
    results.parse(gen_test("test1", "pass", suite_name="lava"))
    assert results.ret() == 2


def test_returns_invalid_logs():
    results = Results([], {})
    results.parse("{")
    results.parse('{ "lvl": "results", "msg": {"case": "tux", "result": "pass"}}')


def test_data():
    results = Results([], {})
    results.parse(gen_test("test1", "pass"))
    assert results.data["mytestsuite"]["test1"]["result"] == "pass"


@pytest.mark.parametrize(
    "name,testsuite",
    [
        ("canceled-1", "ltp-smoke"),
        ("fail-empty", "ltp-smoke"),
        ("fail-1", "ltp-containers"),
        ("fail-2", "ltp-mm"),
        ("fail-3", "ltp-syscalls"),
        ("fail-4", "libhugetlbfs"),
        ("fail-5", "ltp-tracing"),
        ("fail-6", "ltp-smoke"),
        ("pass-1", "ltp-io"),
        ("pass-2", "ltp-smoke"),
    ],
)
def test_results_parsing(name, testsuite):
    logs = (BASE / "logs" / (name + ".yaml")).read_text(encoding="utf-8").strip("\n")

    results = Results(
        [Test.select(testsuite)],
        {
            "kernel": "https://example.com/bzImage",
            "modules": "https://example.com/modules.tar.xz",
            "rootfs": "https://example.com/rootfs.ext4.xz",
            "overlays": [["https://example.com/ltp.tar.xz", "/"]],
        },
    )
    assert results.__artefacts__ == {
        "kernel": "https://example.com/bzImage",
        "rootfs": "https://example.com/rootfs.ext4.xz",
        "modules": "https://example.com/modules.tar.xz",
        "overlays": [["https://example.com/ltp.tar.xz", "/"]],
        "overlay-00": "https://example.com/ltp.tar.xz",
    }
    for line in logs.split("\n"):
        results.parse(line[2:])

    # Full results
    if os.environ.get("TUXRUN_RENDER"):
        (BASE / "results" / (name + ".json")).write_text(
            json.dumps(results.data), encoding="utf-8"
        )
    data = (BASE / "results" / (name + ".json")).read_text(encoding="utf-8")
    assert results.data == json.loads(data)

    if os.environ.get("TUXRUN_RENDER"):
        (BASE / "results" / (name + "-metadata.json")).write_text(
            json.dumps(results.metadata), encoding="utf-8"
        )
    data = (BASE / "results" / (name + "-metadata.json")).read_text(encoding="utf-8")
    assert results.metadata == json.loads(data)


def junit_suites(results):
    root = ElementTree.fromstring(results.junit())
    assert root.tag == "testsuites"
    return {suite.get("name"): suite for suite in root.findall("testsuite")}


def dated(dt):
    return json.dumps({"dt": dt, "lvl": "target", "msg": "line"})


@pytest.mark.parametrize(
    "dts",
    [
        ["2026-11-19T18:47:29", "not a date"],
        ["2026-11-19T18:47:29", "2026-11-19T18:47:30+00:00"],
    ],
)
def test_junit_without_a_job_time_when_the_dates_are_odd(dts):
    results = Results([], {})
    for dt in dts:
        results.parse(dated(dt))
    results.parse(gen_test("job", "pass", suite_name="lava"))

    root = ElementTree.fromstring(results.junit())
    assert root.get("time") is None
    assert root.find("testsuite").get("time") is None


def test_junit_counts_pass_fail_skip():
    t1 = Test(timeout=None)
    t1.name = "mytestsuite"
    results = Results([t1], {})
    results.parse(gen_test("job", "pass", suite_name="lava"))
    results.parse(gen_test("test1", "pass"))
    results.parse(gen_test("test2", "fail"))
    results.parse(gen_test("test3", "skip"))

    suite = junit_suites(results)["mytestsuite"]
    assert suite.get("tests") == "3"
    assert suite.get("failures") == "1"
    assert suite.get("skipped") == "1"
    assert suite.get("errors") == "0"
    cases = {case.get("name"): case for case in suite.findall("testcase")}
    assert cases["test1"].find("failure") is None
    assert cases["test2"].find("failure").get("message") == "fail"
    assert cases["test3"].find("skipped") is not None
    assert cases["test1"].get("classname") == "mytestsuite"


def test_junit_unknown_result_is_an_error():
    results = Results([], {})
    results.parse(gen_test("job", "unknown", suite_name="lava"))

    suite = junit_suites(results)["lava"]
    assert suite.get("errors") == "1"
    case = suite.find("testcase")
    assert case.find("error").get("message") == "unknown"


def test_junit_reports_a_test_without_results_as_an_error():
    t1 = Test(timeout=None)
    t1.name = "mytestsuite"
    results = Results([t1], {})
    results.parse(gen_test("job", "fail", suite_name="lava"))

    suite = junit_suites(results)["mytestsuite"]
    assert suite.get("tests") == "1"
    assert suite.get("errors") == "1"
    assert suite.find("testcase").find("error").get("message") == "no results"


def test_junit_names_the_downloads_by_label():
    results = Results([], {"rootfs": "https://example.com/rootfs.ext4"})
    results.parse(
        '{ "lvl": "results", "msg": {"definition": "lava", "case": "http-download",'
        ' "result": "pass", "extra": {"label": "rootfs", "sha256sum": "00"}}}'
    )

    suite = junit_suites(results)["lava"]
    assert [c.get("name") for c in suite.findall("testcase")] == [
        "http-download.rootfs"
    ]
    assert suite.get("failures") == "0"


def test_junit_keeps_the_log_excerpt_and_duration():
    results = Results([], {})
    results.parse(gen_test("job", "fail", suite_name="lava"))
    results.__data__["lava"]["job"]["log_excerpt"] = ["line one", "line <two>"]
    results.__data__["lava"]["job"]["duration"] = "12.50"

    case = junit_suites(results)["lava"].find("testcase")
    assert case.find("system-out").text == "line one\nline <two>"
    assert case.get("time") == "12.50"


def test_junit_suite_time():
    t1 = Test(timeout=None)
    t1.name = "boot"
    results = Results([t1], {})
    results.parse(
        '{ "dt": "2026-11-19T14:58:00.000000", "lvl": "info", "msg": "start"}'
    )
    results.parse(
        '{ "lvl": "results", "msg": {"definition": "lava", "case": "boot",'
        ' "result": "pass", "duration": "68.77"}}'
    )
    results.parse(gen_test("kernel", "pass", suite_name="1_boot"))
    results.parse('{ "dt": "2026-11-19T15:04:30.500000", "lvl": "info", "msg": "end"}')

    root = ElementTree.fromstring(results.junit())
    suites = {s.get("name"): s for s in root.findall("testsuite")}
    assert suites["boot"].get("time") == "68.77"
    assert suites["lava"].get("time") == "390.50"
    assert root.get("time") == "390.50"


def test_junit_keeps_the_measurement():
    t1 = Test(timeout=None)
    t1.name = "boot"
    results = Results([t1], {})
    results.parse(
        '{ "lvl": "results", "msg": {"definition": "1_boot", "case": "userspace",'
        ' "result": "pass", "measurement": 91.673, "units": "seconds"}}'
    )
    results.parse(
        '{ "lvl": "results", "msg": {"definition": "1_boot", "case": "kernel",'
        ' "result": "pass", "measurement": 6.351}}'
    )
    results.__data__["boot"]["kernel"]["log_excerpt"] = ["Linux version 6.18"]

    cases = {c.get("name"): c for c in junit_suites(results)["boot"]}
    assert cases["userspace"].find("system-out").text == "91.673 seconds"
    assert cases["kernel"].find("system-out").text == "6.351\nLinux version 6.18"


@pytest.mark.parametrize("name", ["fail-1", "pass-1"])
def test_junit_matches_the_json_results(name):
    data = json.loads((BASE / "results" / (name + ".json")).read_text(encoding="utf-8"))
    results = Results([], {})
    results.__data__ = data

    suites = junit_suites(results)
    for suite_name, cases in data.items():
        fails = [c for c in cases.values() if c.get("result") == "fail"]
        assert suites[suite_name].get("failures") == str(len(fails))


def test_junit_drops_characters_xml_can_not_hold():
    results = Results([], {})
    results.parse(gen_test("job", "fail", suite_name="lava"))
    results.__data__["lava"]["job"]["log_excerpt"] = ["\x1b[0mred\x00 text"]

    case = junit_suites(results)["lava"].find("testcase")
    assert case.find("system-out").text == "[0mred text"


def board(msg, lvl="target"):
    return json.dumps({"dt": "2026-11-19T18:47:29", "lvl": lvl, "msg": msg})


def shell_result(case, starttc, endtc):
    msg = {"definition": "1_firmware", "case": case, "result": "pass"}
    msg.update(starttc=starttc, endtc=endtc)
    return json.dumps({"lvl": "results", "msg": msg})


def excerpt_of(results, case):
    return [
        line.split("] ", 1)[1] for line in results.data["firmware"][case]["log_excerpt"]
    ]


def test_log_excerpt_when_the_board_is_ahead_of_the_signals():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_STARTTC uefi-boot>"),
        board("uefi output"),
        board("<LAVA_SIGNAL_ENDTC uefi-boot>"),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=uefi-boot RESULT=pass>"),
        board("<LAVA_SIGNAL_STARTTC esrt>"),
        board("esrt output"),
        board("<LAVA_SIGNAL_ENDTC esrt>"),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=esrt RESULT=pass>"),
        board("Received signal: <TESTCASE> TEST_CASE_ID=uefi-boot", "debug"),
        shell_result("uefi-boot", 1, 3),
        board("Received signal: <TESTCASE> TEST_CASE_ID=esrt", "debug"),
        shell_result("esrt", 4, 6),
    ]:
        results.parse(line)

    assert excerpt_of(results, "uefi-boot") == [
        "<LAVA_SIGNAL_STARTTC uefi-boot>",
        "uefi output",
        "<LAVA_SIGNAL_ENDTC uefi-boot>",
    ]
    assert excerpt_of(results, "esrt") == [
        "<LAVA_SIGNAL_STARTTC esrt>",
        "esrt output",
        "<LAVA_SIGNAL_ENDTC esrt>",
    ]


def test_log_excerpt_of_a_measurement_only_has_its_own_signal():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=boot RESULT=pass>"),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=boot-kernel RESULT=pass>"),
        shell_result("boot", 1, 1),
        shell_result("boot-kernel", 2, 2),
    ]:
        results.parse(line)

    assert excerpt_of(results, "boot") == [
        "<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=boot RESULT=pass>"
    ]
    assert excerpt_of(results, "boot-kernel") == [
        "<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=boot-kernel RESULT=pass>"
    ]


def test_log_excerpt_when_the_signal_is_logged_after_the_result():
    results = Results([], {})
    for line in [
        shell_result("boot", 1, 1),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=boot RESULT=pass>"),
        board("<LAVA_SIGNAL_STARTTC uefi-boot>"),
        board("uefi output"),
        board("<LAVA_SIGNAL_ENDTC uefi-boot>"),
        shell_result("uefi-boot", 2, 4),
    ]:
        results.parse(line)

    assert excerpt_of(results, "boot") == [
        "<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=boot RESULT=pass>"
    ]
    assert excerpt_of(results, "uefi-boot") == [
        "<LAVA_SIGNAL_STARTTC uefi-boot>",
        "uefi output",
        "<LAVA_SIGNAL_ENDTC uefi-boot>",
    ]


def test_log_excerpt_after_results_without_a_signal():
    results = Results([], {})
    for index in range(100):
        results.parse(board(f"case{index}: pass"))
        results.parse(shell_result(f"case{index}", index, index))
    assert results.__log_lines__ == []
    for line in [
        board("<LAVA_SIGNAL_STARTTC esrt>"),
        board("<LAVA_SIGNAL_ENDTC esrt>"),
        shell_result("esrt", 200, 201),
    ]:
        results.parse(line)

    assert results.data["firmware"]["case0"]["log_excerpt"] == []
    assert excerpt_of(results, "esrt") == [
        "<LAVA_SIGNAL_STARTTC esrt>",
        "<LAVA_SIGNAL_ENDTC esrt>",
    ]


def test_log_excerpt_of_a_late_signal_is_only_used_once():
    results = Results([], {})
    for line in [
        shell_result("iter", 1, 1),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=iter RESULT=pass MEASUREMENT=1>"),
        shell_result("iter", 2, 2),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=iter RESULT=pass MEASUREMENT=2>"),
    ]:
        results.parse(line)

    assert excerpt_of(results, "iter") == [
        "<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=iter RESULT=pass MEASUREMENT=2>"
    ]


def test_log_excerpt_with_the_same_case_twice():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=a RESULT=fail>"),
        board("<LAVA_SIGNAL_STARTTC b>"),
        board("<LAVA_SIGNAL_ENDTC b>"),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=b RESULT=pass>"),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=a RESULT=pass>"),
        shell_result("a", 1, 1),
        shell_result("b", 2, 3),
        shell_result("a", 5, 5),
    ]:
        results.parse(line)

    assert excerpt_of(results, "b") == [
        "<LAVA_SIGNAL_STARTTC b>",
        "<LAVA_SIGNAL_ENDTC b>",
    ]
    assert excerpt_of(results, "a") == [
        "<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=a RESULT=pass>"
    ]


def test_log_excerpt_only_has_the_board_output():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_STARTTC esrt>"),
        board("esrt output"),
        board("Received signal: <TESTCASE> TEST_CASE_ID=uefi-boot", "debug"),
        board("more esrt output"),
        board("<LAVA_SIGNAL_ENDTC esrt>"),
        shell_result("esrt", 1, 4),
    ]:
        results.parse(line)

    assert excerpt_of(results, "esrt") == [
        "<LAVA_SIGNAL_STARTTC esrt>",
        "esrt output",
        "more esrt output",
        "<LAVA_SIGNAL_ENDTC esrt>",
    ]


def test_log_excerpt_when_a_test_case_has_no_endtc():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_STARTTC killed>"),
        board("killed output"),
        board("<LAVA_SIGNAL_STARTTC esrt>"),
        board("esrt output"),
        board("<LAVA_SIGNAL_ENDTC esrt>"),
        shell_result("killed", 1, 4),
        shell_result("esrt", 3, 5),
    ]:
        results.parse(line)

    assert excerpt_of(results, "killed") == [
        "<LAVA_SIGNAL_STARTTC killed>",
        "killed output",
    ]
    assert excerpt_of(results, "esrt") == [
        "<LAVA_SIGNAL_STARTTC esrt>",
        "esrt output",
        "<LAVA_SIGNAL_ENDTC esrt>",
    ]


def test_log_excerpt_of_the_last_test_case_without_endtc():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_STARTTC killed>"),
        board("killed output"),
        shell_result("killed", 1, 3),
    ]:
        results.parse(line)

    assert excerpt_of(results, "killed") == [
        "<LAVA_SIGNAL_STARTTC killed>",
        "killed output",
    ]
    assert results.__log_lines__ == []


def test_log_excerpt_has_the_feedback_lines():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_STARTTC esrt>"),
        board("Unable to handle kernel paging request", "feedback"),
        board("esrt output"),
        board("<LAVA_SIGNAL_ENDTC esrt>"),
        shell_result("esrt", 1, 4),
    ]:
        results.parse(line)

    assert excerpt_of(results, "esrt") == [
        "<LAVA_SIGNAL_STARTTC esrt>",
        "Unable to handle kernel paging request",
        "esrt output",
        "<LAVA_SIGNAL_ENDTC esrt>",
    ]


def test_log_excerpt_of_the_rpi4_firmware_tests():
    logs = (BASE / "logs" / "rpi4-firmware.yaml").read_text(encoding="utf-8")
    results = Results([], {})
    for line in logs.strip("\n").split("\n"):
        results.parse(line[2:])

    cases = results.data["firmware"]
    assert list(cases) == [
        "uefi-boot",
        "efi-variables",
        "esrt",
        "firmware-is-u-boot",
        "fwupd-devices",
        "boot-finished",
        "systemd-analyze",
    ]
    for case in cases:
        excerpt = excerpt_of(results, case)
        assert excerpt[0] == f"<LAVA_SIGNAL_STARTTC {case}>"
        assert excerpt[-1] == f"<LAVA_SIGNAL_ENDTC {case}>"
        assert sum("<LAVA_SIGNAL_STARTTC" in line for line in excerpt) == 1
    assert "   Secure Boot: enabled (user)" in excerpt_of(results, "firmware-is-u-boot")
    assert excerpt_of(results, "systemd-analyze")[1].startswith("Startup finished in ")
