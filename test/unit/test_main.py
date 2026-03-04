import json
import os

import pytest
import shlex
import yaml

import tuxrun.__main__
from tuxrun.__main__ import main, start


def touch(directory, name):
    f = directory / name
    f.touch()
    return f


@pytest.fixture
def artefacts(tmp_path):
    os.chdir(tmp_path)
    touch(tmp_path, "arm.dtb")
    touch(tmp_path, "device.yaml")
    touch(tmp_path, "definition.yaml")
    touch(tmp_path, "bios.bin")
    touch(tmp_path, "bzImage")
    touch(tmp_path, "stuff.tar.gz")
    touch(tmp_path, "morestuff.tar.gz")
    touch(tmp_path, "fvp.bin")
    touch(tmp_path, "foo.tar.xz")
    touch(tmp_path, "modules.tar")
    return tmp_path


@pytest.fixture
def run(mocker):
    return mocker.patch("tuxrun.__main__.run")


@pytest.fixture
def tuxrun_args(monkeypatch):
    args = ["tuxrun", "--device", "qemu-armv5"]
    monkeypatch.setattr("sys.argv", args)
    return args


@pytest.fixture
def tuxrun_args_generate(monkeypatch):
    args = [
        "tuxrun",
        "--device",
        "qemu-i386",
        "--kernel",
        "https://storage.tuxboot.com/buildroot/i386/bzImage",
    ]
    monkeypatch.setattr("sys.argv", args)
    return args


@pytest.fixture
def lava_run_call(mocker):
    return mocker.patch("subprocess.Popen")


@pytest.fixture
def lava_run(lava_run_call, mocker):
    mocker.patch("tuxrun.results.Results.ret", return_value=0)
    proc = lava_run_call.return_value
    proc.wait.return_value = 0
    proc.communicate.return_value = (mocker.MagicMock(), mocker.MagicMock())
    return proc


def test_start_calls_main(monkeypatch, mocker):
    monkeypatch.setattr(tuxrun.__main__, "__name__", "__main__")
    main = mocker.patch("tuxrun.__main__.main")
    with pytest.raises(SystemExit):
        start()
    main.assert_called()


def test_main_usage(monkeypatch, capsys, run):
    monkeypatch.setattr("tuxrun.__main__.sys.argv", ["tuxrun"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    _, err = capsys.readouterr()
    assert "usage: tuxrun" in err


def test_almost_real_run(monkeypatch, tuxrun_args, lava_run, capsys):
    lava_run.stderr = [
        '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513"}\n'
    ]
    exitcode = main()
    assert exitcode == 0
    stdout, _ = capsys.readouterr()
    assert "Hello, world" in stdout

    monkeypatch.setattr(
        "sys.argv",
        [
            "tuxrun",
            "--device=qemu-x86_64",
            "--modules",
            "foo.tar.xz",
            "/usr/",
            "argh",
        ],
    )
    with pytest.raises(SystemExit):
        main()

    monkeypatch.setattr(
        "sys.argv",
        [
            "tuxrun",
            "--device=qemu-x86_64",
            "--overlay",
            "foo.tar.xz",
            "/usr/",
            "argh",
        ],
    )
    with pytest.raises(SystemExit):
        main()

    monkeypatch.setattr(
        "sys.argv",
        [
            "tuxrun",
            "--device=qemu-x86_64",
            "--shared",
            "foo.tar.xz",
            "/usr/",
            "argh",
        ],
    )
    with pytest.raises(SystemExit):
        main()

    monkeypatch.setattr(
        "sys.argv",
        [
            "tuxrun",
            "--device=fvp-aemva",
            "--shared",
        ],
    )
    with pytest.raises(SystemExit):
        main()


FVP_MORELLO_ARGS = [
    "--ap-romfw",
    "fvp.bin",
    "--mcp-fw",
    "fvp.bin",
    "--mcp-romfw",
    "fvp.bin",
    "--rootfs",
    "fvp.bin",
    "--scp-fw",
    "fvp.bin",
    "--scp-romfw",
    "fvp.bin",
    "--fip",
    "fvp.bin",
]


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--device", "qemu-armv7", "--boot-args", 'bla"bl'],
        ["--device", "fvp-aemva", "--boot-args", 'bla"bl'],
        ["--device", "qemu-armv7", "--prompt", 'bla"bl'],
        ["--device", "fvp-aemva", "--prompt", 'bla"bl'],
        ["--device", "qemu-armv7", "--dtb", "arm.dtb"],
        ["--device", "qemu-armv7", "--tests", "kselftest-arm64"],
        ["--device", "qemu-arm64", "--modules", "modules.tar"],
        ["--kernel", "https://storage.tuxboot.com/buildroot/i386/bzImage"],
        ["--device", "fvp-aemva", "--mcp-fw", "fvp.bin"],
        ["--device", "fvp-aemva", "--modules", "modules.tar"],
        ["--device", "fvp-morello-android", "--mcp-fw", "fvp.bin"],
        ["--device", "fvp-morello-android", "--test", "multicore"],
        [
            "--device",
            "fvp-morello-android",
            *FVP_MORELLO_ARGS,
            "--tests",
            "bionic",
            "--parameters",
            "BIONIC_TEST_TYPE=invalid",
        ],
        ["--device", "fvp-morello-android", *FVP_MORELLO_ARGS, "--tests", "lldb"],
        [
            "--device",
            "fvp-morello-busybox",
            *FVP_MORELLO_ARGS,
            "--tests",
            "libjpeg-turbo",
        ],
        ["--device", "fvp-morello-busybox", *FVP_MORELLO_ARGS, "--tests", "libpng"],
        ["--device", "fvp-morello-busybox", *FVP_MORELLO_ARGS, "--tests", "libpdfium"],
        ["--device", "fvp-morello-busybox", *FVP_MORELLO_ARGS, "--tests", "zlib"],
        ["--device", "fvp-morello-busybox", *FVP_MORELLO_ARGS, "--tests", "boringssl"],
        [
            "--device",
            "fvp-morello-busybox",
            *FVP_MORELLO_ARGS,
            "--kernel",
            "https://storage.tuxboot.com/buildroot/i386/bzImage",
        ],
        ["--device", "fvp-morello-ubuntu", *FVP_MORELLO_ARGS],
        [
            "--device",
            "fvp-morello-ubuntu",
            "--ap-romfw",
            "fvp.bin",
            "--mcp-fw",
            "fvp.bin",
            "--mcp-romfw",
            "fvp.bin",
            "--scp-fw",
            "fvp.bin",
            "--scp-romfw",
            "fvp.bin",
            "--fip",
            "fvp.bin",
            "--tests",
            "lldb",
        ],
        [
            "--device",
            "fvp-morello-android",
            *FVP_MORELLO_ARGS,
            "--tests",
            "lldb",
            "--parameters",
            "LLDB_URL=http://example.com/lldb.tar.xz",
        ],
        [
            "--device",
            "fvp-morello-android",
            *FVP_MORELLO_ARGS,
            "--tests",
            "libpng",
            "--parameters",
            "SYSTEM_URL=http://example.com/system.tar.xz",
        ],
        [
            "--device",
            "fvp-morello-android",
            *FVP_MORELLO_ARGS,
            "--tests",
            "libjpeg-turbo",
            "--parameters",
            "SYSTEM_URL=http://example.com/system.tar.xz",
        ],
        [
            "--device",
            "fvp-morello-android",
            *FVP_MORELLO_ARGS,
            "--tests",
            "libpdfium",
            "--parameters",
            "SYSTEM_URL=http://example.com/system.tar.xz",
        ],
        [
            "--device",
            "fvp-morello-android",
            *FVP_MORELLO_ARGS,
            "--tests",
            "libpdfium",
            "--parameters",
            "PDF_URL=http://example.com/pdfium-testfiles.tar.xz",
        ],
        [
            "--device",
            "fvp-morello-android",
            *FVP_MORELLO_ARGS,
            "--tests",
            "ltp-smoke",
        ],
        [
            "--device",
            "fvp-morello-android",
            *FVP_MORELLO_ARGS,
            "--tests",
            "kselftest",
        ],
        ["--device", "qemu-arm64", "--tests", "ltp-smoke", "ltp-smoke"],
        ["--device", "fvp-lava"],
    ],
)
def test_command_line_errors(argv, capsys, monkeypatch, mocker, artefacts):
    monkeypatch.setattr("tuxrun.__main__.sys.argv", ["tuxrun"] + argv)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    stdout, stderr = capsys.readouterr()
    assert "usage: tuxrun" in stderr
    assert "tuxrun: error:" in stderr


def test_command_line_parameters(monkeypatch, mocker, artefacts):
    monkeypatch.setattr(
        "tuxrun.__main__.sys.argv",
        [
            "tuxrun",
            "--device",
            "fvp-morello-android",
            "--ap-romfw",
            "fvp.bin",
            "--mcp-fw",
            "fvp.bin",
            "--mcp-romfw",
            "fvp.bin",
            "--rootfs",
            "fvp.bin",
            "--scp-fw",
            "fvp.bin",
            "--scp-romfw",
            "fvp.bin",
            "--fip",
            "fvp.bin",
            "--parameters",
            "USERDATA=http://userdata.tar.xz",
        ],
    )
    run = mocker.patch("tuxrun.__main__.run", return_value=0)
    exitcode = main()
    assert exitcode == 0
    assert len(run.call_args.args) == 4
    print(run.call_args.parameters)
    assert run.call_args[0][0].parameters == {"USERDATA": "http://userdata.tar.xz"}


def test_almost_real_run_generate(tuxrun_args_generate, lava_run, capsys):
    lava_run.stderr = [
        '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513"}\n'
    ]
    exitcode = main()
    assert exitcode == 0
    stdout, _ = capsys.readouterr()
    assert "Hello, world" in stdout


def test_ignores_empty_line_from_lava_run_stdout(tuxrun_args, lava_run):
    lava_run.stderr = [
        '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513"}\n',
        "",
        '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:26.139513"}\n',
    ]
    exitcode = main()
    assert exitcode == 0


def test_ignores_empty_line_from_lava_run_logfile(tuxrun_args, lava_run, tmp_path):
    log = tmp_path / "log.yaml"
    tuxrun_args += ["--log-file-yaml", str(log)]
    lava_run.stderr = [
        '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513"}\n',
        "",
        '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:26.139513"}\n',
    ]
    exitcode = main()
    assert exitcode == 0
    logdata = yaml.safe_load(log.open())
    assert type(logdata[0]) is dict
    assert type(logdata[1]) is dict


def test_exit_status_is_0_on_success(tuxrun_args, lava_run):
    assert main() == 0


def test_exit_status_matches_results(tuxrun_args, lava_run, mocker):
    mocker.patch("tuxrun.results.Results.ret", return_value=1)
    assert main() == 1


def test_save_output(monkeypatch, tmp_path, run):
    monkeypatch.setattr(
        "sys.argv", ["tuxrun", "--device", "qemu-armv5", "--save-outputs"]
    )
    main()
    run.assert_called()
    options = run.call_args[0][0]
    assert (
        options.log_file
        == tmp_path / "home" / ".cache" / "tuxrun" / "tests" / "1" / "logs"
    )
    assert (
        options.log_file_html
        == tmp_path / "home" / ".cache" / "tuxrun" / "tests" / "1" / "logs.html"
    )
    assert (
        options.log_file_text
        == tmp_path / "home" / ".cache" / "tuxrun" / "tests" / "1" / "logs.txt"
    )
    assert (
        options.log_file_yaml
        == tmp_path / "home" / ".cache" / "tuxrun" / "tests" / "1" / "logs.yaml"
    )
    assert (
        options.metadata
        == tmp_path / "home" / ".cache" / "tuxrun" / "tests" / "1" / "metadata.json"
    )
    assert (
        options.results
        == tmp_path / "home" / ".cache" / "tuxrun" / "tests" / "1" / "results.json"
    )


def test_tuxbuild(get, mocker):
    from tuxlava.jobs import tuxbuild_url  # type: ignore

    data = json.dumps(
        {
            "results": {
                "artifacts": {"kernel": ["bzImage"], "modules": ["modules.tar.xz"]},
            },
            "build": {"target_arch": "x86_64"},
        }
    )
    get.side_effect = [mocker.Mock(status_code=200, text=data)]

    tux = tuxbuild_url("https://example.com")
    assert tux.kernel == "https://example.com/bzImage"
    assert tux.modules[0] == "https://example.com/modules.tar.xz"
    assert tux.target_arch == "x86_64"


def test_tuxmake_directory(tmp_path, run):
    from tuxlava.jobs import tuxmake_directory

    tuxmake_build = tmp_path / "build"
    tuxmake_build.mkdir()
    (tuxmake_build / "metadata.json").write_text(
        """
        {
            "results": {
                "artifacts": {"kernel": ["bzImage"], "modules": ["modules.tar.xz"]}
            },
            "build": {"target_arch": "x86_64"}
        }
        """
    )

    tux = tuxmake_directory(tuxmake_build)
    assert tux.kernel == f"file://{tuxmake_build}/bzImage"
    assert tux.modules[0] == f"file://{tuxmake_build}/modules.tar.xz"
    assert tux.modules[1] == "/"
    assert tux.target_arch == "x86_64"


def test_no_modules(tmp_path):
    from tuxlava.jobs import tuxmake_directory

    tuxmake_build = tmp_path / "build"
    tuxmake_build.mkdir()
    (tuxmake_build / "metadata.json").write_text(
        """
        {
            "results": {
                "artifacts": {"kernel": ["bzImage"]}
            },
            "build": {"target_arch": "x86_64"}
        }
        """
    )

    tux = tuxmake_directory(tuxmake_build)
    assert tux.modules == []


def test_invalid_tuxmake_directory(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.argv", ["tuxrun", "--tuxmake", str(tmp_path)])
    with pytest.raises(SystemExit) as exit:
        main()
        assert exit.status_code != 0
    _, err = capsys.readouterr()
    assert "metadata.json" in err


def test_modules(monkeypatch, lava_run_call, lava_run, artefacts):
    monkeypatch.setattr(
        "sys.argv",
        [
            "tuxrun",
            "--kernel=bzImage",
            "--device=qemu-x86_64",
            "--modules=foo.tar.xz",
        ],
    )
    assert main() == 0
    lava_run_call.assert_called()
    args = lava_run_call.call_args[0][0]
    assert f"{artefacts}/foo.tar.xz:{artefacts}/foo.tar.xz:ro" in args


def test_shared(monkeypatch, lava_run_call, lava_run, artefacts):
    monkeypatch.setattr(
        "sys.argv",
        [
            "tuxrun",
            "--kernel=bzImage",
            "--device=qemu-x86_64",
            "--shared",
        ],
    )
    assert main() == 0
    lava_run_call.assert_called()
    args = lava_run_call.call_args[0][0]
    assert (
        f"{artefacts}/home/.cache/tuxrun/tests/1:{artefacts}/home/.cache/tuxrun/tests/1:rw"
        in args
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "tuxrun",
            "--kernel=bzImage",
            "--device=qemu-x86_64",
            "--shared",
            "/home/",
        ],
    )
    assert main() == 0
    lava_run_call.assert_called()
    args = lava_run_call.call_args[0][0]
    assert "/home/:/home/:rw" in args

    monkeypatch.setattr(
        "sys.argv",
        [
            "tuxrun",
            "--kernel=bzImage",
            "--device=qemu-x86_64",
            "--shared",
            "/home/",
            "/mnt/home",
        ],
    )
    assert main() == 0
    lava_run_call.assert_called()
    args = lava_run_call.call_args[0][0]
    assert "/home/:/home/:rw" in args


def test_overlays(monkeypatch, lava_run_call, lava_run, artefacts):
    monkeypatch.setattr(
        "sys.argv",
        [
            "tuxrun",
            "--kernel=bzImage",
            "--device=qemu-x86_64",
            "--overlay=stuff.tar.gz",
            "--overlay=morestuff.tar.gz",
        ],
    )
    assert main() == 0
    lava_run_call.assert_called()
    args = lava_run_call.call_args[0][0]
    assert f"{artefacts}/stuff.tar.gz:{artefacts}/stuff.tar.gz:ro" in args
    assert f"{artefacts}/morestuff.tar.gz:{artefacts}/morestuff.tar.gz:ro" in args


def test_custom_commands(mocker, run):
    from tuxlava.jobs import Job

    cmds = ["cat /etc/hostname"]

    job = Job(kernel="bzImage", device="qemu-x86_64", commands=cmds)
    mocker.patch("tempfile.mkdtemp")
    job.initialize()
    assert len(job.tests) == 1
    assert job.tests[0].name == "commands"
    assert job.commands == " ".join(shlex.quote(s) for s in cmds)


def test_list_devices(mocker, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["tuxrun", "--list-devices"],
    )
    with pytest.raises(SystemExit):
        main()
    stdout, stderr = capsys.readouterr()
    assert stderr == ""
    assert "qemu-i386" in stdout


def test_list_tests(mocker, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["tuxrun", "--list-tests"],
    )
    with pytest.raises(SystemExit):
        main()
    stdout, stderr = capsys.readouterr()
    assert stderr == ""
    assert "ltp-smoke" in stdout


def test_update_cache(mocker, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["tuxrun", "--update-cache"],
    )
    with pytest.raises(SystemExit):
        main()
    stdout, stderr = capsys.readouterr()
    assert (
        stdout
        == """Updating local cache:
* Rootfs:
  * avh-imx93
  * avh-rpi4b
  * fvp-aemva
  * qemu-arm64
  * qemu-arm64be
  * qemu-armv5
  * qemu-armv7
  * qemu-armv7be
  * qemu-i386
  * qemu-m68k
  * qemu-mips32
  * qemu-mips32el
  * qemu-mips64
  * qemu-mips64el
  * qemu-ppc32
  * qemu-ppc64
  * qemu-ppc64le
  * qemu-riscv32
  * qemu-riscv64
  * qemu-s390
  * qemu-sh4
  * qemu-sparc64
  * qemu-x86_64
* Test definitions
"""
    )


def test_save_results_json(tuxrun_args, lava_run, mocker, tmp_path):
    json = tmp_path / "results.json"
    tuxrun_args += [f"--results={json}"]
    main()
    assert json.read_text().strip() == "{}"


def test_timeouts(monkeypatch, run):
    from tuxlava.jobs import Job

    job = Job(
        device="qemu-x86_64", tests=["ltp-smoke"], timeouts={"boot": 1, "ltp-smoke": 12}
    )
    job.initialize()
    assert len(job.tests) == 1
    assert job.tests[0].name == "ltp-smoke"
    assert job.tests[0].timeout == 12
    assert job.timeouts == {"boot": 1, "ltp-smoke": 12}


# To test the qemu_binary overlay we basically fake up the responses
# for all the various readelf/ldd/qemu calls on a real system


@pytest.fixture
def tuxrun_args_qemu_overlay(monkeypatch):
    args = [
        "tuxrun",
        "--qemu-binary",
        "/usr/bin/qemu-system-aarch64",
        "--device",
        "qemu-arm64",
    ]
    monkeypatch.setattr("sys.argv", args)
    return args


fake_readelf = b"""
String dump of section '.interp':
  [     0]  /lib64/ld-linux-x86-64.so.2
"""

# a real QEMU binary links considerably more libraries
fake_ldd = b"""
        linux-vdso.so.1 (0x00007ffe29e5f000)
        libz.so.1 => /lib/x86_64-linux-gnu/libz.so.1 (0x00007f743b834000)
        libpixman-1.so.0 => /lib/x86_64-linux-gnu/libpixman-1.so.0 (0x00007f743b789000)
        libepoxy.so.0 => /lib/x86_64-linux-gnu/libepoxy.so.0 (0x00007f743b65a000)
        libcapstone.so.4 => /lib/x86_64-linux-gnu/libcapstone.so.4 (0x00007f743aff9000)
        libspice-server.so.1 => /lib/x86_64-linux-gnu/libspice-server.so.1 (0x00007f743aeca000)
        libdw.so.1 => /lib/x86_64-linux-gnu/libdw.so.1 (0x00007f743ae21000)
"""

fake_firmware_paths = b"""
/usr/share/qemu
/usr/share/seabios
/usr/lib/ipxe/qemu
"""


@pytest.fixture
def overlay_subprocess_calls(mocker):
    def my_outputs(*args, **kwargs):
        if args[0] == "readelf":
            return fake_readelf
        elif args[0] == "ldd":
            return fake_ldd
        else:
            return fake_firmware_paths

    return mocker.patch("subprocess.check_output", new=my_outputs)


def test_qemu_overlay(tuxrun_args_qemu_overlay, lava_run, overlay_subprocess_calls):
    main()


@pytest.mark.parametrize(
    "args,cnt",
    [
        ("rw", 1),
        ("rw", 2),
        ("" "'" "rw systemd.log_level=warning" "'" "", 3),
        ("r'w", 4),
        ("'rw", 5),
        ("rw'", 6),
    ],
)
def test_boot_args(monkeypatch, mocker, tmpdir, args, cnt):
    monkeypatch.setattr(
        "tuxrun.__main__.sys.argv",
        ["tuxrun", "--device", "qemu-arm64", "--boot-args"] + [args],
    )
    mocker.patch("tuxrun.__main__.Runtime.select", side_effect=SystemExit)
    mocker.patch("tuxrun.assets.__download_and_cache__", side_effect=lambda a, b: a)
    mocker.patch(
        "tuxrun.__main__.get_test_definitions", return_value="file://testdef.tar.zst"
    )
    mocker.patch("tempfile.mkdtemp", return_value=tmpdir)
    mocker.patch("shutil.rmtree")
    if cnt < 4:
        with pytest.raises(SystemExit):
            main()
    else:
        # Invalid case
        with pytest.raises(Exception):
            main()
