# vim: set ts=4
#
# Copyright 2026 Linaro Limited
#
# SPDX-License-Identifier: MIT

import shlex

from tuxrun.exceptions import InvalidArgument
from tuxrun.writer import COLORS

# (e_machine, ELF class bits, byte order) from the ELF header
ELF_ARCHES = {
    "arm64": (183, 64, "little"),
    "arm64be": (183, 64, "big"),
    "armv5": (40, 32, "little"),
    "armv7": (40, 32, "little"),
    "armv7be": (40, 32, "big"),
    "i386": (3, 32, "little"),
    "m68k": (4, 32, "big"),
    "mips32": (8, 32, "big"),
    "mips32el": (8, 32, "little"),
    "mips64": (8, 64, "big"),
    "mips64el": (8, 64, "little"),
    "ppc32": (20, 32, "big"),
    "ppc64": (21, 64, "big"),
    "ppc64le": (21, 64, "little"),
    "riscv32": (243, 32, "little"),
    "riscv64": (243, 64, "little"),
    "s390": (22, 64, "big"),
    "sh4": (42, 32, "little"),
    "sparc64": (43, 64, "big"),
    "x86_64": (62, 64, "little"),
}


def check_vmlinux(vmlinux, arch):
    if arch not in ELF_ARCHES:
        return
    with open(vmlinux, "rb") as f:
        header = f.read(20)
    if len(header) < 20 or header[:4] != b"\x7fELF":
        raise InvalidArgument("argument --vmlinux: not an ELF file")
    order = "big" if header[5] == 2 else "little"
    bits = 64 if header[4] == 2 else 32
    machine = int.from_bytes(header[18:20], order)
    elf = (machine, bits, order)
    if elf != ELF_ARCHES[arch]:
        found = "/".join(a for a, e in ELF_ARCHES.items() if e == elf)
        raise InvalidArgument(
            f"argument --vmlinux: built for {found or 'an unknown arch'}, not {arch}"
        )


def attach_message(cmd):
    return (
        f"\n{COLORS['warning']}qemu waits for gdb. Run this in another terminal:"
        f"{COLORS['end']}\n\n    {COLORS['info']}{cmd}{COLORS['end']}\n"
    )


def gdb_script(socket, src):
    lines = ["import gdb"]
    if src:
        lines += [
            f"src = {str(src)!r}",
            "gdb.execute(f'directory \"{src}\"')",
            'sym = gdb.lookup_global_symbol("start_kernel")',
            "if sym is None:",
            '    print("tuxrun: vmlinux has no debug info, --kernel-src is not used")',
            'elif sym.symtab.filename.endswith("/init/main.c"):',
            '    prefix = sym.symtab.filename.removesuffix("/init/main.c")',
            '    gdb.execute(f\'set substitute-path "{prefix}" "{src}"\')',
        ]
    lines.append(f"gdb.execute({'target remote ' + str(socket)!r})")
    return "\n".join(lines) + "\n"


def gdb_command(runtime, name, vmlinux, script):
    cmd = [runtime.binary, "exec", "-it", name] if runtime.container else []
    cmd += ["gdb-multiarch", "-q"]
    if vmlinux:
        cmd.append(str(vmlinux))
    return shlex.join(cmd + ["-x", str(script)])
