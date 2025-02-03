<div align="center">
  <img src="docs/tuxrun_full.svg" alt="TuxRun Logo" width="40%" />
</div>

[![Pipeline Status](https://gitlab.com/Linaro/tuxrun/badges/master/pipeline.svg)](https://gitlab.com/Linaro/tuxrun/pipelines)
[![coverage report](https://gitlab.com/Linaro/tuxrun/badges/master/coverage.svg)](https://gitlab.com/Linaro/tuxrun/commits/master)
[![PyPI version](https://badge.fury.io/py/tuxrun.svg)](https://pypi.org/project/tuxrun/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI - License](https://img.shields.io/pypi/l/tuxrun)](https://gitlab.com/Linaro/tuxrun/blob/master/LICENSE)

[Documentation](https://tuxrun.org/) - [Repository](https://gitlab.com/Linaro/tuxrun) - [Issues](https://gitlab.com/Linaro/tuxrun/-/issues)

TuxRun, by [Linaro](https://www.linaro.org/), is a command line tool for
testing Linux on the following virtual devices, using curated test suites.

* AVH
* FVP
* QEMU

TuxRun is a part of [TuxSuite](https://tuxsuite.com), a suite of tools and
services to help with Linux kernel development.

[[_TOC_]]

# About TuxRun

Testing the Linux kernel is as simple as using QEMU but it gets complicated
when you want to support the following combinations:

- Architectures (arm64, armv5, armv7, i386, mips32, mips32el, mips64, mips64el,
  ppc32, ppc64, ppc64le, riscv64, s390, sh4, sparc64, x86_64)

- Emulation systems (QEMU or FVP or AVH)
- Tests (every test suite has dependencies on the rootfs)

Each of those items requires specific configuration and root file systems. In
order to allow for reproducible tests, TuxRun uses containers runtimes (Docker
or Podman).

# Installing TuxRun

There are several options for installing TuxRun:

- [From PyPI](docs/install-pypi.md)
- [Run uninstalled](docs/run-uninstalled.md)

# Using TuxRun

To use TuxRun, compile your own linux kernel for arm64, for example using
[TuxMake](https://tuxmake.org).

Then call tuxrun:

```shell
tuxrun --device qemu-arm64 --kernel /path/to/Image
```

TuxRun will automatically start qemu-system with the right arguments and the
right root filesystem.

# TuxLAVA Library

TuxRun uses [TuxLAVA](https://gitlab.com/Linaro/tuxlava) library to generate LAVA job definition files.

# Known issues

Known issues when booting on different virtual platforms.

- [From issues](docs/issues.md)

# Examples

Boot test a mipsel kernel at https://mykernel.org/vmlinux:

```shell
tuxrun --device qemu-mips32el \
       --kernel https://mykernel.org/vmlinux
```

Running *ltp-smoke*:

```shell
tuxrun --device qemu-mips32el \
       --kernel https://mykernel.org/vmlinux \
       --test ltp-smoke
```

Using a custom root file system

```shell
tuxrun --device qemu-mips32el \
       --kernel https://mykernel.org/vmlinux \
       --rootfs https://mykernel.org/rootfs.tar.xz
```
