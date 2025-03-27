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
