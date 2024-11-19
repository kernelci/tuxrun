# Running under FVP

TuxRun allows to run linux kernel under FVP for Morello and AEMvA.

> Note: "Supported devices"
    See the [architecture matrix](devices.md#fvp-devices) for the supported devices.

## Preparing the environment

In order to use TuxRun with FVP, you have to build container images:

* AEMvA fvp model
* morello fvp model

Start by cloning the git repository:

```shell
git clone https://gitlab.com/Linaro/tuxrun
cd tuxrun
```

### AEMvA fvp model

Build the container containing the AEMvA FVP model:

=== "podman"

```shell
cd share/fvp
make fvp-aemva
```

=== "docker"

```shell
cd share/fvp
make fvp-aemva RUNTIME=docker
```

> Warning: "Container tag"
    The container should be named **fvp:aemva-11.28_23** in order for TuxRun
    to work.


### Morello fvp model

Build the container containing the Morello FVP model:

=== "podman"

```shell
cd share/fvp
make fvp-morello
```

=== "docker"

```shell
cd share/fvp
make fvp-morello RUNTIME=docker
```

> Warning: "Container tag"
    The container should be named **fvp:morello-0.11.34** in order for TuxRun
    to work.

## AEMvA testing

The command line is really similar to the qemu one:

### Example

=== "podman"
```shell
tuxrun --device fvp-aemva \
       --kernel https://example.com/Image \
       --dtb https://example.com/fvp-base-revc.dtb
```

=== "docker"
```shell
tuxrun --runtime docker \
       --device fvp-aemva \
       --kernel https://example.com/Image \
       --dtb https://example.com/fvp-base-revc.dtb
```

## Boot testing

In order to run a simple boot test on **fvp-morello-busybox**:

### Example

=== "podman"
```shell
tuxrun --device fvp-morello-buxybox \
       --ap-romfw https://example.com/fvp/morello/tf-bl1.bin \
       --mcp-fw https://example.com/fvp/morello/mcp_fw.bin \
       --mcp-romfw https://example.com/fvp/morello/mcp_romfw.bin \
       --rootfs https://example.com/fvp/morello/rootfs.img.xz \
       --scp-fw https://example.com/fvp/morello/scp_fw.bin \
       --scp-romfw https://example.com/fvp/morello/scp_romfw.bin \
       --fip https://example.com/fvp/morello/fip.bin
```

=== "docker"
```shell
tuxrun --runtime docker \
       --device fvp-morello-buxybox \
       --ap-romfw https://example.com/fvp/morello/tf-bl1.bin \
       --mcp-fw https://example.com/fvp/morello/mcp_fw.bin \
       --mcp-romfw https://example.com/fvp/morello/mcp_romfw.bin \
       --rootfs https://example.com/fvp/morello/rootfs.img.xz \
       --scp-fw https://example.com/fvp/morello/scp_fw.bin \
       --scp-romfw https://example.com/fvp/morello/scp_romfw.bin \
       --fip https://example.com/fvp/morello/fip.bin
```

## Modules overlay

TuxRun allows to provide a custom **modules.tar.xz** archive that will be
extracted on top of the rootfs.

```shell
tuxrun --device fvp-aemva \
       --kernel https://example.com/Image \
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
tuxrun --runtime docker --device fvp-aemva --boot-args rw --tuxmake /home/anders/.cache/tuxmake/builds/1490 \
       --rootfs https://storage.tuxboot.com/debian/bookworm/arm64/rootfs.ext4.xz \
       --overlay file:///home/anders/.cache/tuxmake/builds/1490/kselftest.tar.xz \
       --overlay file:///home/anders/src/tmp/custom-scripts.tar.xz --timeouts boot=60 \
       --save-outputs --log-file - --timeouts commands=40 -- /custom-script.sh
```

## Testing on Android

In order to run an Android test on **fvp-morello-android**:

=== "podman"

```shell
tuxrun --device fvp-morello-android \
       --ap-romfw https://example.com/fvp/morello/tf-bl1.bin \
       --mcp-fw https://example.com/fvp/morello/mcp_fw.bin \
       --mcp-romfw https://example.com/fvp/morello/mcp_romfw.bin \
       --rootfs https://example.com/fvp/morello/rootfs.img.xz \
       --scp-fw https://example.com/fvp/morello/scp_fw.bin \
       --scp-romfw https://example.com/fvp/morello/scp_romfw.bin \
       --fip https://example.com/fvp/morello/fip.bin \
       --parameters USERDATA=https://example.com/fvp/morello/userdata.tar.xz \
       --tests binder
```

=== "docker"

```shell
tuxrun --runtime docker \
       --device fvp-morello-android \
       --ap-romfw https://example.com/fvp/morello/tf-bl1.bin \
       --mcp-fw https://example.com/fvp/morello/mcp_fw.bin \
       --mcp-romfw https://example.com/fvp/morello/mcp_romfw.bin \
       --rootfs https://example.com/fvp/morello/rootfs.img.xz \
       --scp-fw https://example.com/fvp/morello/scp_fw.bin \
       --scp-romfw https://example.com/fvp/morello/scp_romfw.bin \
       --fip https://example.com/fvp/morello/fip.bin \
       --parameters USERDATA=https://example.com/fvp/morello/userdata.tar.xz \
       --tests binder
```

## Running a LAVA job definition
TuxRun can run a LAVA job definition which is running any tests for FVP as shown below. Any other parameters passed to the cli other than the ones mentioned below will be ignored:
```shell
tuxrun --device fvp-lava --job-definition definition.yaml
```
