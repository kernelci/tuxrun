import os
import subprocess
from pathlib import Path

import pytest

from tuxrun.runtimes import DockerRuntime, NullRuntime, PodmanRuntime, Runtime


def test_select():
    assert Runtime.select("docker") == DockerRuntime
    assert Runtime.select("null") == NullRuntime
    assert Runtime.select("podman") == PodmanRuntime


def test_cmd_null(tmp_path):
    runtime = Runtime.select("null")(tmp_path)
    assert runtime.cmd(["hello", "world"]) == ["hello", "world"]

    runtime.bind("/hello/world")
    assert runtime.cmd(["hello", "world"]) == ["hello", "world"]


def test_cmd_podman(tmp_path):
    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    args = [
        "podman",
        "run",
        "--log-driver=none",
        "--rm",
        "--hostname",
        "tuxrun",
        "-v",
        "/boot:/boot:ro",
        "-v",
        "/lib/modules:/lib/modules:ro",
    ]
    if Path("/dev/kvm").exists():
        args.extend(
            [
                "--device",
                "/dev/kvm:/dev/kvm:rw",
            ]
        )
    if Path(f"/var/tmp/.guestfs-{os.getuid()}").exists():
        args.extend(
            [
                "-v",
                f"/var/tmp/.guestfs-{os.getuid()}:/var/tmp/.guestfs-0:rw",
            ]
        )
    assert runtime.cmd(["hello", "world"]) == args + [
        "--name",
        "name",
        "image",
        "hello",
        "world",
    ]

    runtime.bind("/hello/world")
    assert runtime.cmd(["hello", "world"]) == args + [
        "-v",
        "/hello/world:/hello/world:rw",
        "--name",
        "name",
        "image",
        "hello",
        "world",
    ]


def test_kill_null(mocker, tmp_path):
    runtime = Runtime.select("null")(tmp_path)
    runtime.__proc__ = None
    runtime.kill()

    runtime.__proc__ = mocker.MagicMock()
    runtime.kill()
    runtime.__proc__.send_signal.assert_called_once_with(15)


def test_kill_podman(mocker, tmp_path):
    popen = mocker.patch("subprocess.Popen")
    runtime = Runtime.select("podman")(tmp_path)
    runtime.kill()
    popen.assert_called_once_with(
        ["podman", "stop", "--time", "60", None],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        preexec_fn=os.setpgrp,
    )
    assert len(runtime.__sub_procs__) == 1


def test_kill_podman_raise(mocker, tmp_path):
    popen = mocker.patch("subprocess.Popen", side_effect=FileNotFoundError)
    runtime = Runtime.select("podman")(tmp_path)
    runtime.kill()
    popen.assert_called_once_with(
        ["podman", "stop", "--time", "60", None],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        preexec_fn=os.setpgrp,
    )
    assert len(runtime.__sub_procs__) == 0


def test_pre_run_docker(tmp_path):
    runtime = Runtime.select("docker")(tmp_path)
    runtime.pre_run(tmp_path)
    assert runtime.__bindings__[-1] == (
        "/var/run/docker.sock",
        "/var/run/docker.sock",
        False,
        False,
    )


def test_pre_run_null(tmp_path):
    runtime = Runtime.select("null")(tmp_path)
    runtime.pre_run(None)


def test_pre_run_podman(mocker, tmp_path):
    (tmp_path / "podman.sock").touch()
    popen = mocker.patch("subprocess.Popen")
    run = mocker.patch("subprocess.run")

    runtime = Runtime.select("podman")(tmp_path)
    runtime.pre_run(tmp_path)
    assert runtime.__pre_proc__ is not None
    popen.assert_called_once()
    run.assert_called_once()


def test_pre_run_podman_errors(mocker, tmp_path):
    popen = mocker.patch("subprocess.Popen")
    run = mocker.patch("subprocess.run")
    sleep = mocker.patch("time.sleep")

    runtime = Runtime.select("podman")(tmp_path)
    with pytest.raises(Exception) as exc:
        runtime.pre_run(tmp_path)
    assert exc.match("Unable to create podman socket at ")
    assert exc.match("podman.sock")
    popen.assert_called_once()
    run.assert_called_once()
    sleep.assert_called()


def test_post_run_null(tmp_path):
    runtime = Runtime.select("null")(tmp_path)
    runtime.post_run()


def test_post_run_podman(mocker, tmp_path):
    runtime = Runtime.select("podman")(tmp_path)
    runtime.post_run()

    runtime.__pre_proc__ = mocker.MagicMock()
    runtime.post_run()
    runtime.__pre_proc__.kill.assert_called_once_with()
    runtime.__pre_proc__.wait.assert_called_once_with()


def test_run(mocker, tmp_path):
    popen = mocker.patch("subprocess.Popen")

    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    with runtime.run(["hello", "world"]):
        popen.assert_called_once()
        assert runtime.__proc__ is not None
        assert runtime.__ret__ is None
    runtime.__proc__.wait.assert_called_once()


def test_run_errors(mocker, tmp_path):
    popen = mocker.patch("subprocess.Popen", side_effect=FileNotFoundError)

    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    with pytest.raises(FileNotFoundError):
        with runtime.run(["hello", "world"]):
            pass
    popen.assert_called_once()

    popen = mocker.patch("subprocess.Popen", side_effect=Exception)
    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    with pytest.raises(Exception):
        with runtime.run(["hello", "world"]):
            pass
    popen.assert_called_once()

    # Test duplicated destination bindings (duplicated sources are allowed)
    popen = mocker.patch("subprocess.Popen", side_effect=FileNotFoundError)
    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    runtime.bind("/hello", "/world")
    runtime.bind("/hello2", "/world")
    with pytest.raises(Exception) as exc:
        with runtime.run(["hello", "world"]):
            pass
    assert exc.match("Duplicated mount destination '/world'")
    popen.assert_not_called()


def test_use_host_network(tmp_path):
    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    runtime.use_host_network()

    cmd = runtime.cmd(["hello", "world"])
    found_host_network = False
    for i, arg in enumerate(cmd):
        if arg == "--network" and i + 1 < len(cmd) and cmd[i + 1] == "host":
            found_host_network = True
            break
    assert found_host_network, f"--network host not found in {cmd}"


def test_skip_http_server_sets_entrypoint(tmp_path):
    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    runtime.skip_http_server()

    cmd = runtime.cmd(["hello", "world"])
    assert "--entrypoint" in cmd
    entrypoint_idx = cmd.index("--entrypoint")
    assert cmd[entrypoint_idx + 1] == "/usr/bin/lava-run"


def test_skip_http_server_strips_lava_run_from_args(tmp_path):
    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    runtime.skip_http_server()

    cmd = runtime.cmd(["lava-run", "--device", "foo", "definition.yaml"])
    assert cmd[-3:] == ["--device", "foo", "definition.yaml"]
    assert "--entrypoint" in cmd


def test_skip_http_server_preserves_other_args(tmp_path):
    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    runtime.skip_http_server()

    cmd = runtime.cmd(["other-command", "--option", "value"])
    assert cmd[-3:] == ["other-command", "--option", "value"]


def test_host_network_and_skip_http_server_combined(tmp_path):
    runtime = Runtime.select("podman")(tmp_path)
    runtime.name("name")
    runtime.image("image")
    runtime.use_host_network()
    runtime.skip_http_server()

    cmd = runtime.cmd(["lava-run", "--device", "foo"])
    assert "--network" in cmd
    assert "--entrypoint" in cmd
    assert cmd[-2:] == ["--device", "foo"]
