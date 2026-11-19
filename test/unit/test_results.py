import json
import os
from pathlib import Path

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


def test_log_excerpt_of_a_case_after_a_shell_case_with_the_same_name():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_STARTTC foo>"),
        board("<LAVA_SIGNAL_ENDTC foo>"),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=foo RESULT=fail>"),
        shell_result("foo", 1, 2),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=foo RESULT=pass>"),
        shell_result("foo", 4, 4),
    ]:
        results.parse(line)

    assert excerpt_of(results, "foo") == [
        "<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=foo RESULT=pass>"
    ]


def test_log_excerpt_of_a_case_after_a_shell_case_with_a_late_signal():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_STARTTC foo>"),
        board("<LAVA_SIGNAL_ENDTC foo>"),
        shell_result("foo", 1, 2),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=foo RESULT=fail>"),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=foo RESULT=pass>"),
        shell_result("foo", 4, 4),
    ]:
        results.parse(line)

    assert excerpt_of(results, "foo") == [
        "<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=foo RESULT=pass>"
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


def test_log_excerpt_of_numbered_test_cases():
    results = Results([], {})
    for line in [
        board("<LAVA_SIGNAL_STARTTC 01_foo>"),
        board("foo output"),
        board("<LAVA_SIGNAL_ENDTC 01_foo>"),
        shell_result("01_foo", 1, 3),
        board("<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=02_bar RESULT=pass>"),
        shell_result("02_bar", 4, 4),
    ]:
        results.parse(line)

    assert excerpt_of(results, "foo") == [
        "<LAVA_SIGNAL_STARTTC 01_foo>",
        "foo output",
        "<LAVA_SIGNAL_ENDTC 01_foo>",
    ]
    assert excerpt_of(results, "bar") == [
        "<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=02_bar RESULT=pass>"
    ]


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
