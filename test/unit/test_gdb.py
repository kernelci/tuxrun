import re
from pathlib import Path

import pytest

from tuxrun.exceptions import InvalidArgument
from tuxrun.gdb import (
    ELF_ARCHES,
    attach_message,
    check_vmlinux,
    gdb_command,
    gdb_script,
)
from tuxrun.runtimes import DockerRuntime, NullRuntime
from tuxlava.devices import Device  # type: ignore
from tuxlava.devices.qemu import QemuDevice  # type: ignore


def test_gdb_command_in_a_container():
    runtime = DockerRuntime(Path("/tmp"))
    assert gdb_command(runtime, "tuxrun-abc", None, "/t/gdb.py") == (
        "docker exec -it tuxrun-abc gdb-multiarch -q -x /t/gdb.py"
    )


def test_gdb_command_on_the_host():
    cmd = gdb_command(NullRuntime(Path("/tmp")), "x", Path("/v"), "/t/gdb.py")
    assert cmd == "gdb-multiarch -q /v -x /t/gdb.py"


def test_gdb_script():
    assert gdb_script("/t/gdb.sock", None) == (
        "import gdb\ngdb.execute('target remote /t/gdb.sock')\n"
    )


def test_gdb_script_maps_the_source():
    script = gdb_script("/t/gdb.sock", Path("/linux"))
    compile(script, "gdb.py", "exec")
    assert "src = '/linux'" in script
    assert 'directory "{src}"' in script
    assert 'set substitute-path "{prefix}" "{src}"' in script
    assert script.endswith("gdb.execute('target remote /t/gdb.sock')\n")


@pytest.mark.parametrize("arch", ["arm64", ""])
def test_check_vmlinux_ok(elf, arch):
    check_vmlinux(elf(183, 64, "little"), arch)


@pytest.mark.parametrize(
    "machine,bits,order,found",
    [
        (62, 64, "little", "x86_64"),
        (183, 64, "big", "arm64be"),
        (40, 32, "little", "armv5/armv7"),
        (99, 32, "little", "an unknown arch"),
    ],
)
def test_check_vmlinux_wrong_arch(elf, machine, bits, order, found):
    with pytest.raises(InvalidArgument, match=f"built for {found}, not arm64$"):
        check_vmlinux(elf(machine, bits, order), "arm64")


def test_check_vmlinux_not_elf(tmp_path):
    vmlinux = tmp_path / "vmlinux"
    vmlinux.write_bytes(b"not an elf file at all")
    with pytest.raises(InvalidArgument, match="not an ELF file"):
        check_vmlinux(vmlinux, "arm64")


def test_attach_message():
    msg = re.sub(r"\x1b\[[0-9;]*m", "", attach_message("podman exec -it x gdb"))
    assert msg == (
        "\nqemu waits for gdb. Run this in another terminal:\n\n"
        "    podman exec -it x gdb\n"
    )


def test_elf_arches_cover_the_qemu_devices():
    archs = {
        d.arch for d in Device.list(virtual_device=True) if issubclass(d, QemuDevice)
    }
    assert archs - {""} <= ELF_ARCHES.keys()
