# Devices

TuxRun supports many architectures for the following virtual devices.

* AVH
* FVP
* QEMU

!!! tip "Listing devices"
    You can list the supported devices with:
    ```shell
    tuxrun --list-devices
    ```

## AVH devices

Device        | AVH Model      | Kernel |
--------------|----------------|--------|
avh-rpi4b     | Raspberry Pi 4 | Image  |
avh-imx93     | i.MX93         | Image  |

## FVP devices

Device                | FVP version         |OS         |
----------------------|---------------------|-----------|
fvp-aemva             | RevC AEMvA 11.28_23 |           |
fvp-lava              | N/A                 |           |
fvp-morello-android   | Morello 0.11.34     | Android   |
fvp-morello-baremetal | Morello 0.11.34     | Baremetal |
fvp-morello-busybox   | Morello 0.11.34     | Busybox   |
fvp-morello-debian    | Morello 0.11.34     | Debian    |
fvp-morello-oe        | Morello 0.11.34     | OE        |
fvp-morello-ubuntu    | Morello 0.11.34     | Ubuntu    |

## QEMU devices

Device        | Description         | Machine     | CPU              | Kernel
--------------|---------------------|-------------|------------------|--------
qemu-arm64    | 64-bit ARMv8        | virt        | Cortex-A57       | Image
qemu-arm64be  | 64-bit ARMv8 (BE)   | virt        | Cortex-A57       | Image
qemu-armv5    | 32-bit ARM          | versatilepb | arm926           | zImage
qemu-armv7    | 32-bit ARM          | virt        | Cortex-A15       | zImage
qemu-armv7be  | 32-bit ARM (BE)     | virt        | Cortex-A15       | zImage
qemu-i386     | 32-bit X86          | q35         | coreduo          | bzImage
qemu-m68k     | 32-bit m68k (BE)    | virt        | m68040           | vmlinux
qemu-mips32   | 32-bit MIPS         | malta       | mips32r6-generic | vmlinux
qemu-mips32el | 32-bit MIPS (EL)    | malta       | mips32r6-generic | vmlinux
qemu-mips64   | 64-bit MIPS         | malta       | 20Kc             | vmlinux
qemu-mips64el | 64-bit MIPS (EL)    | malta       | 20Kc             | vmlinux
qemu-ppc32    | 32-bit PowerPC      | ppce500     | e500mc           | uImage
qemu-ppc64    | 64-bit PowerPC      | pSeries     | Power8           | vmlinux
qemu-ppc64le  | 64-bit PowerPC (EL) | pSeries     | Power8           | vmlinux
qemu-riscv32  | 32-bit RISC-V       | virt        | rv32             | Image
qemu-riscv64  | 64-bit RISC-V       | virt        | rv64             | Image
qemu-s390     | 64-bit s390         | max,zpci=on | s390-ccw-virtio  | bzImage
qemu-sh4      | 32-bit SH           | r2d         | sh7785           | zImage
qemu-sparc64  | 64-bit Sparc        | sun4u       | UltraSPARC II    | vmlinux
qemu-x86_64   | 64-bit X86          | q35         | Nehalem          | bzImage

## SSH device

Run tests on an already booted machine over ssh

Device        | Description            | Machine     | CPU              | Kernel
--------------|------------------------|-------------|------------------|--------
ssh-device    | Device with ssh access | Any         | Any	        | N/A
