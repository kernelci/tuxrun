# vim: set ts=4
#
# Copyright 2022-present Linaro Limited
#
# SPDX-License-Identifier: MIT

from tuxrun.tests import Test


class KSelfTest(Test):
    devices = ["qemu-*", "fvp-aemva", "avh-imx93", "avh-rpi4b"]
    cmdfile: str = ""
    need_test_definition = True

    def render(self, **kwargs):
        kwargs["name"] = self.name
        kwargs["timeout"] = self.timeout
        kwargs["cmdfile"] = (
            self.cmdfile if self.cmdfile else self.name.replace("kselftest-", "")
        )

        if "CPUPOWER" in kwargs["parameters"]:
            kwargs["overlays"].insert(
                0, ("cpupower", kwargs["parameters"]["CPUPOWER"], "/")
            )
        if "KSELFTEST" in kwargs["parameters"]:
            kwargs["overlays"].insert(
                0,
                (
                    "kselftest",
                    kwargs["parameters"]["KSELFTEST"],
                    "/opt/kselftests/default-in-kernel/",
                ),
            )

        return self._render("kselftest.yaml.jinja2", **kwargs)


class KSelftestAcct(KSelfTest):
    name = "kselftest-acct"
    timeout = 5


class KSelftestAlsa(KSelfTest):
    name = "kselftest-alsa"
    timeout = 5


class KSelftestAmdPstate(KSelfTest):
    name = "kselftest-amd-pstate"
    timeout = 5


class KSelftestArm64(KSelfTest):
    devices = ["qemu-arm64", "fvp-aemva", "avh-imx93", "avh-rpi4b"]
    name = "kselftest-arm64"
    timeout = 45


class KSelftestBreakpoints(KSelfTest):
    devices = ["qemu-arm64", "fvp-aemva", "qemu-x86_64", "avh-imx93", "avh-rpi4b"]
    name = "kselftest-breakpoints"
    timeout = 5


class KSelftestCachestat(KSelfTest):
    name = "kselftest-cachestat"
    timeout = 5


class KSelftestCapabilities(KSelfTest):
    name = "kselftest-capabilities"
    timeout = 5


class KSelftestCgroup(KSelfTest):
    name = "kselftest-cgroup"
    timeout = 5


class KSelftestConnector(KSelfTest):
    name = "kselftest-connector"
    timeout = 5


class KSelftestClone3(KSelfTest):
    name = "kselftest-clone3"
    timeout = 5


class KSelftestCore(KSelfTest):
    name = "kselftest-core"
    timeout = 5


class KSelftestCpufreq(KSelfTest):
    name = "kselftest-cpufreq"
    timeout = 5


class KSelftestCpuHotplug(KSelfTest):
    name = "kselftest-cpu-hotplug"
    timeout = 5


class KSelftestDamon(KSelfTest):
    name = "kselftest-damon"
    timeout = 5


class KSelftestDevicesErrorLogs(KSelfTest):
    name = "kselftest-devices-error_logs"
    timeout = 5


class KSelftestDevicesProbe(KSelfTest):
    name = "kselftest-devices-probe"
    timeout = 5


class KSelftestDma(KSelfTest):
    name = "kselftest-dma"
    timeout = 5


class KSelftestDmabufHeaps(KSelfTest):
    name = "kselftest-dmabuf-heaps"
    timeout = 5


class KSelftestDrivers(KSelfTest):
    name = "kselftest-drivers"
    timeout = 5


class KSelftestDriversDmaBuf(KSelfTest):
    name = "kselftest-drivers-dma-buf"
    cmdfile = "drivers.dma-buf"
    timeout = 5


class KSelftestDriversGpu(KSelfTest):
    name = "kselftest-drivers-gpu"
    cmdfile = "drivers.gpu"
    timeout = 5


class KSelftestDriversNet(KSelfTest):
    name = "kselftest-drivers-net"
    cmdfile = "drivers.net"
    timeout = 15


class KSelftestDriversNetBonding(KSelfTest):
    name = "kselftest-drivers-net-bonding"
    cmdfile = "drivers.net.bonding"
    timeout = 15


class KSelftestDriversNetDsa(KSelfTest):
    name = "kselftest-drivers-net-dsa"
    cmdfile = "drivers.net.dsa"
    timeout = 15


class KSelftestDriversNetHW(KSelfTest):
    name = "kselftest-drivers-net-hw"
    cmdfile = "drivers.hw"
    timeout = 15


class KSelftestDriversNetLib(KSelfTest):
    name = "kselftest-drivers-net-lib"
    cmdfile = "drivers.net.lib"
    timeout = 15


class KSelftestDriversNetMicrochip(KSelfTest):
    name = "kselftest-drivers-net-microchip"
    cmdfile = "drivers.net.microchip"
    timeout = 15


class KSelftestDriversNetMlxsw(KSelfTest):
    name = "kselftest-drivers-net-mlxsw"
    cmdfile = "drivers.net.mlxsw"
    timeout = 15


class KSelftestDriversNetNetdevsim(KSelfTest):
    name = "kselftest-drivers-net-netdevsim"
    cmdfile = "drivers.net.netdevsim"
    timeout = 15


class KSelftestDriversNetOcelot(KSelfTest):
    name = "kselftest-drivers-net-ocelot"
    cmdfile = "drivers.net.ocelot"
    timeout = 15


class KSelftestDriversNetTeam(KSelfTest):
    name = "kselftest-drivers-net-team"
    cmdfile = "drivers.net.team"
    timeout = 15


class KSelftestDriversNetVirtioNet(KSelfTest):
    name = "kselftest-drivers-net-virtio_net"
    cmdfile = "drivers.net.virtio_net"
    timeout = 15


class KSelftestDriversSdsi(KSelfTest):
    name = "kselftest-drivers-sdsi"
    cmdfile = "drivers.sdsi"
    timeout = 5


class KSelftestDriversUsbUsbip(KSelfTest):
    name = "kselftest-drivers-usb-usbip"
    cmdfile = "drivers.usb.usbip"
    timeout = 15


class KSelftestEfivarfs(KSelfTest):
    name = "kselftest-efivarfs"
    timeout = 5


class KSelftestExec(KSelfTest):
    name = "kselftest-exec"
    timeout = 5


class KSelftestFchmodat2(KSelfTest):
    name = "kselftest-fchmodat2"
    timeout = 15


class KSelftestFilesystems(KSelfTest):
    name = "kselftest-filesystems"
    timeout = 15


class KSelftestFilesystemsBinderfs(KSelfTest):
    name = "kselftest-filesystems-binderfs"
    cmdfile = "filesystem.binderfs"
    timeout = 15


class KSelftestFilesystemsEpoll(KSelfTest):
    name = "kselftest-filesystems-epoll"
    cmdfile = "filesystem.epoll"
    timeout = 15


class KSelftestFilesystemsFat(KSelfTest):
    name = "kselftest-filesystems-fat"
    cmdfile = "filesystem.fat"
    timeout = 15


class KSelftestFilesystemOverlayfs(KSelfTest):
    name = "kselftest-filesystems-overlayfs"
    cmdfile = "filesystem.overlayfs"
    timeout = 15


class KSelftestFilesystemStatmount(KSelfTest):
    name = "kselftest-filesystems-statmount"
    cmdfile = "filesystem.statmount"
    timeout = 15


class KSelftestFirmware(KSelfTest):
    name = "kselftest-firmware"
    timeout = 5


class KSelftestFpu(KSelfTest):
    name = "kselftest-fpu"
    timeout = 5


class KSelftestFtrace(KSelfTest):
    name = "kselftest-ftrace"
    timeout = 15


class KSelftestFutex(KSelfTest):
    name = "kselftest-futex"
    timeout = 5


class KSelftestGpio(KSelfTest):
    name = "kselftest-gpio"
    timeout = 5


class KSelftestHid(KSelfTest):
    name = "kselftest-hid"
    timeout = 5


class KSelftestIa64(KSelfTest):
    name = "kselftest-ia64"
    timeout = 5


class KSelftestIntelPstate(KSelfTest):
    devices = ["qemu-x86_64", "qemu-i386"]
    name = "kselftest-intel_pstate"
    timeout = 5


class KSelftestIommu(KSelfTest):
    name = "kselftest-iommu"
    timeout = 5


class KSelftestIPC(KSelfTest):
    name = "kselftest-ipc"
    timeout = 5


class KSelftestIR(KSelfTest):
    name = "kselftest-ir"
    timeout = 5


class KSelftestKcmp(KSelfTest):
    name = "kselftest-kcmp"
    timeout = 5


class KSelftestKexec(KSelfTest):
    devices = ["qemu-x86_64", "qemu-i386", "qemu-ppc64le"]
    name = "kselftest-kexec"
    timeout = 5


class KSelftestKmod(KSelfTest):
    name = "kselftest-kmod"
    timeout = 5


class KSelftestKvm(KSelfTest):
    name = "kselftest-kvm"
    timeout = 15


class KSelftestLandlock(KSelfTest):
    name = "kselftest-landlock"
    timeout = 5


class KSelftestLib(KSelfTest):
    name = "kselftest-lib"
    timeout = 5


class KSelftestLivepatch(KSelfTest):
    devices = ["qemu-x86_64", "qemu-i386"]
    name = "kselftest-livepatch"
    timeout = 5


# Can't run this in LAVA since the intention is to trigger crashes.
# That will mean that LAVA will always end with a failure.
# class KSelftestLkdtm(KSelfTest):
#    name = "kselftest-lkdtm"
#    timeout = 5


class KSelftestLocking(KSelfTest):
    name = "kselftest-locking"
    timeout = 5


class KSelftestLsm(KSelfTest):
    name = "kselftest-lsm"
    timeout = 5


class KSelftestMembarrier(KSelfTest):
    name = "kselftest-membarrier"
    timeout = 5


class KSelftestMemfd(KSelfTest):
    name = "kselftest-memfd"
    timeout = 5


class KSelftestMemoryHotplug(KSelfTest):
    name = "kselftest-memory-hotplug"
    timeout = 5


class KSelftestMm(KSelfTest):
    name = "kselftest-mm"
    timeout = 15


class KSelftestMincore(KSelfTest):
    name = "kselftest-mincore"
    timeout = 5


class KSelftestMount(KSelfTest):
    name = "kselftest-mount"
    timeout = 15


class KSelftestMountSetattr(KSelfTest):
    name = "kselftest-mount_setattr"
    timeout = 5


class KSelftestMoveMountSetGroup(KSelfTest):
    name = "kselftest-move_mount_set_group"
    timeout = 5


class KSelftestMqueue(KSelfTest):
    name = "kselftest-mqueue"
    timeout = 15


class KSelftestNci(KSelfTest):
    name = "kselftest-nci"
    timeout = 5


class KSelftestNet(KSelfTest):
    name = "kselftest-net"
    timeout = 15


class KSelftestNetAfUnix(KSelfTest):
    name = "kselftest-net-af_unix"
    cmdfile = "net.af_unix"
    timeout = 15


class KSelftestNetForwarding(KSelfTest):
    name = "kselftest-net-forwarding"
    cmdfile = "net.forwarding"
    timeout = 10


class KSelftestNetHsr(KSelfTest):
    name = "kselftest-net-hsr"
    cmdfile = "net.hsr"
    timeout = 5


class KSelftestNetMptcp(KSelfTest):
    name = "kselftest-net-mptcp"
    cmdfile = "net.mptcp"
    timeout = 15


class KSelftestNetfilter(KSelfTest):
    name = "kselftest-netfilter"
    timeout = 15


class KSelftestNetRds(KSelfTest):
    name = "kselftest-net-rds"
    cmdfile = "net.rds"
    timeout = 15


class KSelftestNetTcpAo(KSelfTest):
    name = "kselftest-net-tcp_ao"
    cmdfile = "net.tcp_ao"
    timeout = 15


class KSelftestNolibc(KSelfTest):
    name = "kselftest-nolibc"
    timeout = 5


class KSelftestNsfs(KSelfTest):
    name = "kselftest-nsfs"
    timeout = 15


class KSelftestNtb(KSelfTest):
    name = "kselftest-ntb"
    timeout = 5


class KSelftestOpenat2(KSelfTest):
    name = "kselftest-openat2"
    timeout = 5


class KSelftestPerfEvents(KSelfTest):
    name = "kselftest-perf_events"
    timeout = 15


class KSelftestPidfd(KSelfTest):
    name = "kselftest-pidfd"
    timeout = 5


class KSelftestPidNamespace(KSelfTest):
    name = "kselftest-pid_namespace"
    timeout = 5


class KSelftestPrctl(KSelfTest):
    name = "kselftest-prctl"
    timeout = 5


class KSelftestProc(KSelfTest):
    name = "kselftest-proc"
    timeout = 5


class KSelftestPstore(KSelfTest):
    name = "kselftest-pstore"
    timeout = 5


class KSelftestPtp(KSelfTest):
    name = "kselftest-ptp"
    timeout = 5


class KSelftestPtrace(KSelfTest):
    devices = ["qemu-x86_64", "qemu-i386"]
    name = "kselftest-ptrace"
    timeout = 5


class KSelftestRcutorture(KSelfTest):
    name = "kselftest-rcutorture"
    timeout = 5


class KSelftestResctrl(KSelfTest):
    name = "kselftest-resctrl"
    timeout = 5


class KSelftestRlimits(KSelfTest):
    name = "kselftest-rlimits"
    timeout = 5


class KSelftestRseq(KSelfTest):
    name = "kselftest-rseq"
    timeout = 15


class KSelftestRtc(KSelfTest):
    name = "kselftest-rtc"
    timeout = 15


class KSelftestRust(KSelfTest):
    name = "kselftest-rust"
    timeout = 5


class KSelftestSafesetid(KSelfTest):
    name = "kselftest-safesetid"
    timeout = 5


class KSelftestSched(KSelfTest):
    name = "kselftest-sched"
    timeout = 5


class KSelftestSeccomp(KSelfTest):
    name = "kselftest-seccomp"
    timeout = 15


class KSelftestSgx(KSelfTest):
    name = "kselftest-sgx"
    timeout = 5


class KSelftestSignal(KSelfTest):
    name = "kselftest-signal"
    timeout = 5


class KSelftestSize(KSelfTest):
    name = "kselftest-size"
    timeout = 5


class KSelftestSplice(KSelfTest):
    name = "kselftest-splice"
    timeout = 5


class KSelftestStaticKeys(KSelfTest):
    name = "kselftest-static_keys"
    timeout = 5


class KSelftestSync(KSelfTest):
    name = "kselftest-sync"
    timeout = 5


class KSelftestSysctl(KSelfTest):
    name = "kselftest-sysctl"
    timeout = 5


class KSelftestTcTesting(KSelfTest):
    name = "kselftest-tc-testing"
    timeout = 15


class KSelftestTdx(KSelfTest):
    name = "kselftest-tdx"
    timeout = 5


class KSelftestTimens(KSelfTest):
    name = "kselftest-timens"
    timeout = 5


class KSelftestTimers(KSelfTest):
    name = "kselftest-timers"
    timeout = 15


class KSelftestTmpfs(KSelfTest):
    name = "kselftest-tmpfs"
    timeout = 5


class KSelftestTpm2(KSelfTest):
    name = "kselftest-tpm2"
    timeout = 5


class KSelftestUevent(KSelfTest):
    name = "kselftest-uevent"
    timeout = 5


class KSelftestUser(KSelfTest):
    name = "kselftest-user"
    timeout = 5


class KSelftestUserEvents(KSelfTest):
    name = "kselftest-user_events"
    timeout = 5


class KSelftestVDSO(KSelfTest):
    name = "kselftest-vDSO"
    timeout = 5


class KSelftestWatchdog(KSelfTest):
    name = "kselftest-watchdog"
    timeout = 5


class KSelftestX86(KSelfTest):
    devices = ["qemu-x86_64", "qemu-i386"]
    name = "kselftest-x86"
    timeout = 5


class KSelftestZram(KSelfTest):
    name = "kselftest-zram"
    timeout = 5
