from pathlib import Path

import pytest

from tuxrun.quiet import Quiet
from tuxrun.writer import COLORS
from tuxrun.yaml import yaml_load

DT = "2022-06-03T05:38:46.976272"

JOB = {
    "actions": [
        {"deploy": {"to": "tmpfs", "images": {}}},
        {"boot": {"method": "qemu", "timeout": {"minutes": 15}}},
        {
            "test": {
                "definitions": [
                    {"name": "ltp-io", "from": "url", "path": "ltp.yaml"},
                    {"name": "ltp-fs", "from": "url", "path": "ltp.yaml"},
                ]
            }
        },
        {"command": {"name": "shutdown"}},
    ]
}


def log(lvl, msg, **extra):
    return {"dt": DT, "lvl": lvl, "msg": msg, **extra}


def run(quiet, lvl, msg):
    out = quiet(log(lvl, msg))
    if out is None:
        return None
    assert out["lvl"] in COLORS
    return (out["lvl"], out["msg"])


@pytest.mark.parametrize(
    "msg,expected",
    [
        ("start: 0 validate", "Start validate"),
        (
            "start: 1 deployimages (timeout 00:05:00) [common]",
            "Deploy to tmpfs (deployimages, timeout 00:05:00)",
        ),
        (
            "start: 2 boot-image-retry (timeout 00:15:00) [common]",
            "Boot with qemu (boot-image-retry, timeout 00:15:00)",
        ),
        (
            "start: 3 lava-test-retry (timeout 00:02:00) [common]",
            "Test ltp-io, ltp-fs (lava-test-retry, timeout 00:02:00)",
        ),
        (
            "start: 4 command (timeout 00:01:00) [common]",
            "Run command shutdown (command, timeout 00:01:00)",
        ),
        (
            "start: 5 finalize (timeout 00:05:00) [common]",
            "Start finalize (timeout 00:05:00)",
        ),
        (
            "end: 1 deployimages (duration 00:01:07) [common]",
            "End of deployimages (duration 00:01:07)",
        ),
    ],
)
def test_root_action(msg, expected):
    assert run(Quiet(JOB), "info", msg) == ("info", expected)


@pytest.mark.parametrize(
    "msg",
    [
        "start: 1.1 download-retry (timeout 00:05:00) [common]",
        "end: 1.1 download-retry (duration 00:00:01) [common]",
    ],
)
def test_sub_action_is_hidden(msg):
    assert run(Quiet(JOB), "debug", msg) is None


def test_root_action_without_job_definition():
    msg = "start: 1 deployimages (timeout 00:05:00) [common]"
    assert run(Quiet(None), "info", msg) == (
        "info",
        "Start deployimages (timeout 00:05:00)",
    )


@pytest.mark.parametrize(
    "job",
    [
        "not a dict",
        {"actions": "not a list"},
        {"actions": ["deploy", {}, {"deploy": "tmpfs"}]},
        {"actions": [{"deploy": {"to": ["tmpfs"]}}]},
        {"actions": [{"test": {"definitions": "ltp"}}]},
        {"actions": [{"test": {"definitions": ["ltp", {"name": 3}]}}]},
        {"actions": [{"deploy": {}, "boot": {}}]},
    ],
)
def test_broken_job_definition(job):
    msg = "start: 1 deployimages (timeout 00:05:00) [common]"
    assert run(Quiet(job), "info", msg) == (
        "info",
        "Start deployimages (timeout 00:05:00)",
    )


def test_interactive_and_monitors():
    job = {
        "actions": [
            {"test": {"interactive": [{"name": "uboot"}]}},
            {"test": {"monitors": [{"name": "tftf"}]}},
        ]
    }
    quiet = Quiet(job)
    assert run(quiet, "info", "start: 1 lava-test-interactive-retry")[1].startswith(
        "Test uboot "
    )
    assert run(quiet, "info", "start: 2 lava-test-monitor-retry")[1].startswith(
        "Test tftf "
    )


@pytest.mark.parametrize(
    "msg",
    [
        "downloading https://builds.tuxbuild.com/2A3N5MEYUoB0ZxvZ56jL2XLJntq/bzImage",
        "12MB downloaded in 0.24s (52.03MB/s)",
        "539 MB downloaded in 20.37 s (26.47 MB/s)",
        "Fetching tests from https://github.com/Linaro/test-definitions.git",
        "Untar tests from file /var/lib/lava/dispatcher/tmp/tuxrun-6m_yncxf-1/url_repo/td.tar to directory /tmp/0, stripping 0 components",
    ],
)
def test_download_and_test_definitions(msg):
    assert run(Quiet(JOB), "info", msg) == ("info", msg)


@pytest.mark.parametrize(
    "msg",
    [
        "lava-dispatcher, installed at version: 2022.04",
        "Using unzstd to decompress zstd",
        "Creating lava-test-runner.conf files",
        "Job finished correctly",
    ],
)
def test_other_info_is_hidden(msg):
    assert run(Quiet(JOB), "info", msg) is None


@pytest.mark.parametrize(
    "msg,expected",
    [
        (
            "Calling: ['nice', 'docker', 'stop', 'tuxrun-g06tkwb1-lava-1']",
            "$ nice docker stop tuxrun-g06tkwb1-lava-1",
        ),
        (
            "Calling: 'nice' 'docker' 'stop' 'tuxrun-g06tkwb1-lava-1'",
            "$ nice docker stop tuxrun-g06tkwb1-lava-1",
        ),
        (
            "Calling: ['sh', '-c', 'echo hello world']",
            "$ sh -c 'echo hello world'",
        ),
        ("Calling: ['nice', 3]", "$ ['nice', 3]"),
        ("Calling: [{[]: 1}]", "$ [{[]: 1}]"),
        ("Calling: ['nice'", "$ ['nice'"),
        ("Calling: 'nice", "$ 'nice"),
        ("Calling: ", "$ "),
    ],
)
def test_run_cmd_command(msg, expected):
    assert run(Quiet(JOB), "debug", msg) == ("debug", expected)


def test_run_cmd_output_and_exit_code():
    quiet = Quiet(JOB)
    assert run(quiet, "debug", ">> tuxrun-g06tkwb1-lava-1\r") == (
        "debug",
        "tuxrun-g06tkwb1-lava-1",
    )
    assert run(quiet, "debug", ">> a\nb\n") == ("debug", "a\nb")
    assert run(quiet, "debug", "Returned 125 in 0 seconds") == (
        "debug",
        "Exit code 125 (0 s)",
    )


def test_parsed_command():
    quiet = Quiet(JOB)
    assert run(quiet, "debug", "sh -c docker run --rm fvp --version") is None
    assert run(quiet, "debug", "output: Fast Models [11.17.21 (Feb 16 2022)]") == (
        "debug",
        "$ sh -c docker run --rm fvp --version\nFast Models [11.17.21 (Feb 16 2022)]",
    )
    assert run(quiet, "debug", "output: All Rights Reserved.") == (
        "debug",
        "All Rights Reserved.",
    )


def test_parsed_command_empty_first_output():
    quiet = Quiet(JOB)
    run(quiet, "debug", "sh -c docker run --rm fvp --version")
    assert run(quiet, "debug", "output: ") == (
        "debug",
        "$ sh -c docker run --rm fvp --version",
    )


def test_parsed_command_failed():
    quiet = Quiet(JOB)
    run(quiet, "debug", "docker pull fvp")
    assert run(quiet, "info", "Parsed command exited 1.") == (
        "debug",
        "$ docker pull fvp\nExit code 1",
    )


def test_parsed_command_allow_fail():
    quiet = Quiet(JOB)
    run(quiet, "debug", "docker pull fvp")
    run(quiet, "debug", "output: done")
    assert run(
        quiet,
        "info",
        "Parsed command exited zero with allow_fail set, returning 4 bytes.",
    ) == ("debug", "Exit code 0")


def test_parsed_command_allow_fail_keeps_the_output():
    quiet = Quiet(JOB)
    run(quiet, "debug", "nice ls /nope")
    assert run(quiet, "info", "Parsed command exited 2.") == (
        "debug",
        "$ nice ls /nope\nExit code 2",
    )
    assert run(
        quiet,
        "info",
        "action: foo\ncommand: ['nice', 'ls', '/nope']\n"
        "message: Command returned non-zero exit status 2.\n"
        "output: ls: cannot access '/nope'\nsecond line\nreturn code: 2",
    ) == ("debug", "ls: cannot access '/nope'\nsecond line")


@pytest.mark.parametrize(
    "level,msg",
    [
        ("info", "Boot command: /usr/bin/qemu-system-arm -cpu arm926 -m 256"),
        (
            "debug",
            "Boot command: lava-outerr docker run --rm --interactive --tty --hostname lava --name tuxrun-lava-1",
        ),
        (
            "debug",
            "Connect command: lava-outerr docker exec --interactive --tty tuxrun-lava-1 telnet localhost 5000",
        ),
        (
            "debug",
            "Feedback command: lava-outerr docker exec --interactive --tty tuxrun-lava-1 telnet localhost 5001",
        ),
    ],
)
def test_host_command(level, msg):
    command = msg.split(" command: ", 1)[1]
    assert run(Quiet(JOB), level, msg) == ("debug", f"$ {command}")


def test_output_without_command():
    quiet = Quiet(JOB)
    run(quiet, "debug", "sh -c true")
    run(quiet, "target", "login:")
    assert run(quiet, "debug", "output: done") == ("debug", "done")


@pytest.mark.parametrize(
    "msg,expected",
    [
        (
            {"case": "validate", "definition": "lava", "result": "pass"},
            ("results", "lava.validate: pass"),
        ),
        (
            {"case": "aio01", "definition": "0_ltp-io", "result": "pass"},
            ("results", "ltp-io.aio01: pass"),
        ),
        (
            {"case": "0_ltp-io", "definition": "lava", "result": "fail"},
            ("error", "lava.ltp-io: fail"),
        ),
        (
            {
                "case": "boot-time",
                "definition": "1_systemd-analyze",
                "result": "pass",
                "measurement": 3.5,
                "units": "s",
            },
            ("results", "systemd-analyze.boot-time: pass (3.5 s)"),
        ),
        (
            {"case": "c", "definition": "d", "result": "pass", "measurement": 7},
            ("results", "d.c: pass (7)"),
        ),
        ({}, ("results", "?.?: ?")),
        (
            {"case": 1, "definition": None, "result": ["fail"]},
            ("results", "None.1: ['fail']"),
        ),
    ],
)
def test_results(msg, expected):
    assert run(Quiet(JOB), "results", msg) == expected


@pytest.mark.parametrize(
    "lvl", ["target", "input", "feedback", "warning", "error", "exception"]
)
def test_kept_as_is(lvl):
    data = log(lvl, "Booting Linux on physical CPU 0x0", ns="common")
    assert Quiet(JOB)(data) == data


@pytest.mark.parametrize(
    "data",
    [
        log("results", "not a dict"),
        log("info", {"a": 1}),
        log("debug", None),
        log("event", "something"),
        log(3, "level is not a string"),
    ],
)
def test_odd_input_is_hidden(data):
    assert Quiet(JOB)(data) is None


@pytest.mark.parametrize("lvl", ["target", "input", "warning"])
def test_board_output_not_a_string(lvl):
    assert Quiet(JOB)(log(lvl, 42)) == log(lvl, "42")


def test_real_logs():
    for path in sorted((Path(__file__).parent / "logs").glob("*.yaml")):
        quiet = Quiet(None)
        for data in yaml_load(path.read_text(encoding="utf-8")) or []:
            out = quiet(data)
            if out is not None:
                assert out["lvl"] in COLORS
                assert isinstance(out["msg"], str)
