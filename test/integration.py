#!/usr/bin/python3
import argparse
import fnmatch
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

from tuxlava.devices import Device  # type: ignore
from tuxlava.tests import Test  # type: ignore
from tuxrun.yaml import yaml_load


###########
# Helpers #
###########
def get_results(tmpdir: Path) -> Dict:
    required_keys = {"msg", "lvl", "dt"}
    res: Dict[Any, Any] = {}
    data = yaml_load((tmpdir / "logs.yaml").read_text(encoding="utf-8"))

    if data is None:
        return {}

    for line in data:
        if not isinstance(line, dict):
            continue
        if not required_keys.issubset(set(line.keys())):
            continue
        if line["lvl"] != "results":
            continue
        definition = line["msg"]["definition"]
        case = line["msg"]["case"]
        del line["msg"]["definition"]
        del line["msg"]["case"]
        res.setdefault(definition, {})[case] = line["msg"]

    return res


def get_simple_results(res: Dict) -> Dict:
    results = {
        "boot": res.get("lava", {}).get("login-action", {}).get("result", "fail")
    }
    for name in res:
        if name == "lava":
            continue
        key = "_".join(name.split("_")[1:])
        if all(res[name][case]["result"] in ["skip", "pass"] for case in res[name]):
            results[key] = "pass"
        else:
            results[key] = "fail"
    return results


def get_job_result(results: Dict, simple_results: Dict) -> str:
    # lava.job is missing: error
    lava = results.get("lava", {}).get("job")
    if lava is None:
        return "error"

    if lava["result"] == "fail":
        if lava.get("error_type") == "Job":
            return "fail"
        return "error"

    if all(v == "pass" for (k, v) in simple_results.items()):
        return "pass"
    return "fail"


def run(device, test, runtime, debug):
    tmpdir = Path(tempfile.mkdtemp(prefix="tuxrun-"))

    args = [
        "python3",
        "-m",
        "tuxrun",
        "--device",
        device,
        "--runtime",
        runtime,
        "--log-file-yaml",
        str(tmpdir / "logs.yaml"),
        "--log-file",
        "/dev/null",
    ]
    if test:
        args.extend(["--tests", test])

    if device == "fvp-morello-android":
        args.extend(
            [
                "--mcp-fw",
                "https://storage.tuxboot.com/fvp-morello-android/mcp_fw.bin",
                "--mcp-romfw",
                "https://storage.tuxboot.com/fvp-morello-android/mcp_romfw.bin",
                "--rootfs",
                "https://storage.tuxboot.com/fvp-morello-android/android-nano.img.xz",
                "--scp-fw",
                "https://storage.tuxboot.com/fvp-morello-android/scp_fw.bin",
                "--scp-romfw",
                "https://storage.tuxboot.com/fvp-morello-android/scp_romfw.bin",
                "--fip",
                "https://storage.tuxboot.com/fvp-morello-busybox/fip.bin",
            ]
        )
        if test == "binder":
            args.extend(
                [
                    "--parameters",
                    "USERDATA=https://storage.tuxboot.com/fvp-morello-android/userdata.tar.xz",
                ]
            )
        elif test == "bionic":
            args.extend(
                [
                    "--parameters",
                    "USERDATA=https://storage.tuxboot.com/fvp-morello-android/userdata.tar.xz",
                ]
            )
        elif test == "boringssl":
            args.extend(
                [
                    "--parameters",
                    "SYSTEM_URL=https://storage.tuxboot.com/fvp-morello-android/system.tar.xz",
                ]
            )
        elif test == "compartment":
            args.extend(
                [
                    "--parameters",
                    "USERDATA=https://storage.tuxboot.com/fvp-morello-android/userdata.tar.xz",
                ]
            )
        elif test == "libjpeg-turbo":
            args.extend(
                [
                    "--parameters",
                    "LIBJPEG_TURBO_URL=https://storage.tuxboot.com/fvp-morello-android/libjpeg-turbo.tar.xz",
                    "--parameters",
                    "SYSTEM_URL=https://storage.tuxboot.com/fvp-morello-android/system.tar.xz",
                ]
            )
        elif test == "libpng":
            args.extend(
                [
                    "--parameters",
                    "PNG_URL=https://storage.tuxboot.com/fvp-morello-android/png-testfiles.tar.xz",
                    "--parameters",
                    "SYSTEM_URL=https://storage.tuxboot.com/fvp-morello-android/system.tar.xz",
                ]
            )
        elif test == "libpdfium":
            args.extend(
                [
                    "--parameters",
                    "PDFIUM_URL=https://storage.tuxboot.com/fvp-morello-android/pdfium-testfiles.tar.xz",
                    "--parameters",
                    "SYSTEM_URL=https://storage.tuxboot.com/fvp-morello-android/system.tar.xz",
                ]
            )
        elif test == "lldb":
            args.extend(
                [
                    "--parameters",
                    "LLDB_URL=https://storage.tuxboot.com/fvp-morello-android/lldb_tests.tar.xz",
                    "--parameters",
                    "TC_URL=https://storage.tuxboot.com/fvp-morello-android/morello-clang.tar.xz",
                ]
            )
        elif test == "logd":
            args.extend(
                [
                    "--parameters",
                    "USERDATA=https://storage.tuxboot.com/fvp-morello-android/userdata.tar.xz",
                ]
            )
        elif test == "zlib":
            args.extend(
                [
                    "--parameters",
                    "SYSTEM_URL=https://storage.tuxboot.com/fvp-morello-android/system.tar.xz",
                ]
            )
    elif device == "fvp-morello-busybox":
        args.extend(
            [
                "--mcp-fw",
                "https://storage.tuxboot.com/fvp-morello-busybox/mcp_fw.bin",
                "--mcp-romfw",
                "https://storage.tuxboot.com/fvp-morello-busybox/mcp_romfw.bin",
                "--rootfs",
                "https://storage.tuxboot.com/fvp-morello-busybox/busybox.img.xz",
                "--scp-fw",
                "https://storage.tuxboot.com/fvp-morello-busybox/scp_fw.bin",
                "--scp-romfw",
                "https://storage.tuxboot.com/fvp-morello-busybox/scp_romfw.bin",
                "--fip",
                "https://storage.tuxboot.com/fvp-morello-busybox/fip.bin",
            ]
        )
    elif device == "fvp-morello-ubuntu":
        args.extend(
            [
                "--mcp-fw",
                "https://storage.tuxboot.com/fvp-morello-ubuntu/mcp_fw.bin",
                "--mcp-romfw",
                "https://storage.tuxboot.com/fvp-morello-ubuntu/mcp_romfw.bin",
                "--scp-fw",
                "https://storage.tuxboot.com/fvp-morello-ubuntu/scp_fw.bin",
                "--scp-romfw",
                "https://storage.tuxboot.com/fvp-morello-ubuntu/scp_romfw.bin",
                "--fip",
                "https://storage.tuxboot.com/fvp-morello-ubuntu/fip.bin",
            ]
        )

    try:
        ret = subprocess.call(args)
        if ret != 0:
            print(f"Command return non-zero exist status {ret}")
            print((tmpdir / "logs.yaml").read_text(encoding="utf-8"))
            return ret

        results = get_results(tmpdir)
        simple_results = get_simple_results(results)
        result = get_job_result(results, simple_results)

        if debug:
            print("Results:")
            for res in results:
                print(f"* {res}: {results[res]}")

            print("\nSimple results:")
            for res in simple_results:
                print(f"* {res}: {simple_results[res]}")
            print(f"Result {result}")
        else:
            print(f"{result}")
        assert result == "pass"
    finally:
        shutil.rmtree(tmpdir)


##############
# Entrypoint #
##############
def main():
    parser = argparse.ArgumentParser(description="Integration tests")
    parser.add_argument("--devices", nargs="+", required=True, help="device")
    parser.add_argument(
        "--tests",
        default=["boot"],
        nargs="+",
        help="tests",
    )
    parser.add_argument("--debug", default=False, action="store_true", help="debug")
    parser.add_argument(
        "--runtime",
        default="podman",
        choices=["docker", "null", "podman"],
        help="Runtime",
    )
    options = parser.parse_args()

    if len(options.devices) == 1 and "*" in options.devices[0]:
        pat = options.devices[0]
        options.devices = [
            d.name
            for d in Device.list(virtual_device=True)
            if fnmatch.fnmatch(d.name, pat)
        ]
        for qemu in ["qemu-riscv32", "qemu-sh4"]:
            if qemu in options.devices:
                options.devices.remove(qemu)

    for device in options.devices:
        tests = options.tests.copy()
        if tests == ["all"]:
            tests = ["boot"] + Test.list(device=device)
        for test in tests:
            print(f"=> {device} x {test}")
            if run(
                device, "" if test == "boot" else test, options.runtime, options.debug
            ):
                return 1
            print("")


if __name__ == "__main__":
    sys.exit(main())
