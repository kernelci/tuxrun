# Running under QEMU

TuxRun allows to run a linux kernel under QEMU.

> Note: "Supported devices"
    See the [architecture matrix](devices.md#qemu-devices) for the supported devices.

## Boot testing

In order to run a simple boot test on arm64:

```shell
tuxrun --device qemu-arm64 --kernel http://storage.tuxboot.com/buildroot/arm64/Image
```

> Tip: "Artefact URLs"
    Artefacts (kernel, dtb, rootfs, ...) can be either local or remote
    (http/https url). TuxRun will automatically download a remote artefacts.

## Modules overlay

TuxRun allows to provide a custom **modules.tar.xz** archive that will be
extracted on top of the rootfs.

```shell
tuxrun --device qemu-arm64 \
       --kernel http://storage.tuxboot.com/buildroot/arm64/Image \
       --modules modules.tar.xz
```

> Warning: "Modules format"
    The modules archive should be a **tar archive**, compressed with **xz**.

> Tip: "Overlays"
    Any overlay can be applied to the rootfs with the **--overlay** option.
    This option can be specified multiple times. Each overlay should be a
    **tar archive** compressed with **xz**.

## Custom script(s) overlay

```shell
#!/bin/sh

# Enable the events you want to trace
echo 1 > /sys/kernel/debug/tracing/events/sched/enable
# Enable tracer
echo 1 > /sys/kernel/debug/tracing/tracing_on

# Run whatever userspace tool you want to trace.
cd /arm64
./sve_regs
./sve_vl
./tpidr2_siginfo
./za_no_regs
./zt_no_regs
./zt_regs
./pac
./fp-stress

# Disable tracer
echo 0 > /sys/kernel/debug/tracing/tracing_on

cat /sys/kernel/debug/tracing/trace
```
Tar the custom-script scripts together
```shell
chmod +x *.sh
tar cJf ../custom-scripts.tar.xz .
```

Building an ftrace prepared kernel with [tuxmake](https://tuxmake.org/)
```shell
cd /to/your/kernel/tree
tuxmake --runtime podman --target-arch arm64 --toolchain gcc-12 --kconfig defconfig \
        --kconfig-add https://raw.githubusercontent.com/Linaro/meta-lkft/kirkstone/meta/recipes-kernel/linux/files/systemd.config \
        --kconfig-add CONFIG_KFENCE=y --kconfig-add CONFIG_FTRACE=y dtbs dtbs-legacy headers kernel kselftest modules
```

Running with the custom scripts
```shell
tuxrun --runtime docker --device qemu-arm64 --boot-args rw --tuxmake /home/anders/.cache/tuxmake/builds/1490 \
       --rootfs https://storage.tuxboot.com/debian/bookworm/arm64/rootfs.ext4.xz \
       --overlay file:///home/anders/.cache/tuxmake/builds/1490/kselftest.tar.xz \
       --overlay file:///home/anders/src/tmp/custom-scripts.tar.xz --timeouts boot=60 \
       --save-outputs --log-file - --timeouts commands=40 -- /custom-script.sh
```

## Boot arguments

You can specify custom boot arguments with:

```shell
tuxrun --device qemu-arm64 \
       --kernel http://storage.tuxboot.com/buildroot/arm64/Image \
       --boot-args "initcall_debug"
```

## Running tests

You can run a specific test with:

```shell
tuxrun --device qemu-arm64 \
       --kernel http://storage.tuxboot.com/buildroot/arm64/Image \
       --tests ltp-smoke
```

> Tip: "Multiple tests"
    Multiple tests can be specified after **--tests**.
    The tests will be executed one by one, in the order specified on the command-line.

## Custom qemu version

You can provide a container with qemu already installed. TuxRun will use qemu from this container:

```shell
tuxrun --device qemu-armv5 \
       --qemu-image docker.io/qemu/qemu:latest
```

## Extra qemu arguments

Add arguments to the qemu command line with `--qemu-args`:

```shell
tuxrun --device qemu-arm64 \
       --qemu-args "-m 8G"
```

For one option, use `--qemu-args=-S`. Give it more than once to add more.

## Custom command

You can run any command **inside** the VM with:

```shell
tuxrun --device qemu-arm64 \
       --kernel http://storage.tuxboot.com/buildroot/arm64/Image \
       -- cat /proc/cpuinfo
```

> Tip: "Command and tests"
    When combining a custom command and tests, the custom command will be ran
    after all the tests.

## Timeouts

You can override the default timeouts with:

```shell
tuxrun --device qemu-armv5 \
       --tests ltp-smoke
       --timeouts deploy=10 boot=12 ltp-smoke=32
```

This will set the timeouts to:

* `deploy`: 10 minutes
* `boot`: 12 minutes
* `ltp-smoke`: 32 minutes

## TuxMake and TuxBuild

You can run tests against TuxMake or TuxBuild artefacts with `--tuxmake` or `--tuxbuild`:

```shell
tuxrun --tuxmake ~/.cache/tuxmake/builds/1
tuxrun --tuxbuild https://builds.tuxbuild.com/<ksuid>/
```

> Tip: "default device"
    For some architectures (like ARM), the tuxrun device should be specified with `--device`.

## Mounting host directory

You can mount a host directory into the qemu vm using the [9p
protocol](https://en.wikipedia.org/wiki/9P_(protocol)).

Start tuxrun with `--shared`:
```shell
tuxrun --device qemu-arm64 --shared /home/user/shared
```

`--shared <src> <dst>` accepts zero, one or two parameters. The defaults are:

* src: the cache directory (in `~/.cache/tuxrun/tests/<id>`) on the host
* dst: /mnt/tuxrun in the VM

> Warning: Device support
    This feature is only supported on qemu devices

> Warning: Kernel support
    The Qemu kernel should be compiled with the support for 9p, PCI and virtio:
    ```
    CONFIG_NET_9P=y
    CONFIG_NET_9P_VIRTIO=y
    CONFIG_9P_FS=y
    CONFIG_PCI=y
    CONFIG_VIRTIO_PCI=y
    CONFIG_PCI_HOST_GENERIC=y (only needed for the QEMU Arm 'virt' board)
    ```
