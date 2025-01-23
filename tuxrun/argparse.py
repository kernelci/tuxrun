#!/usr/bin/python3
# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import argparse
import sys
from pathlib import Path

from tuxrun import __version__
from tuxrun.assets import get_rootfs, get_test_definitions
from tuxrun.utils import ProgressIndicator, pathurlnone, DEFAULT_DISPATCHER_DOWNLOAD_DIR

from tuxlava.devices import Device  # type: ignore
from tuxlava.tests import Test  # type: ignore


###########
# Helpers #
###########
def filter_artefacts(options):
    keys = [
        "ap-romfw",
        "bios",
        "bl1",
        "dtb",
        "fip",
        "kernel",
        "mcp-fw",
        "mcp-romfw",
        "modules",
        "overlays",
        "rootfs",
        "scp-fw",
        "scp-romfw",
        "uefi",
    ]
    return {k: getattr(options, k) for k in vars(options) if k in keys}


###########
# Actions #
###########
class ListDevicesAction(argparse.Action):
    def __init__(
        self, option_strings, help, dest=argparse.SUPPRESS, default=argparse.SUPPRESS
    ):
        super().__init__(option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser._print_message(
            "\n".join([d.name for d in Device.list(virtual_device=True)]) + "\n",
            sys.stdout,
        )
        parser.exit()


class ListTestsAction(argparse.Action):
    def __init__(
        self, option_strings, help, dest=argparse.SUPPRESS, default=argparse.SUPPRESS
    ):
        super().__init__(option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser._print_message(
            "\n".join(Test.list(virtual_device=True)) + "\n", sys.stdout
        )
        parser.exit()


class KeyValueAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        for value in values:
            key, value = value.split("=", maxsplit=1)
            getattr(namespace, self.dest)[key] = value


class KeyValueParameterAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        for value in values:
            key, value = value.split("=", maxsplit=1)
            if key in ["KSELFTEST"]:
                if "$BUILD/" not in value:
                    value = pathurlnone(value)
            getattr(namespace, self.dest)[key] = value


class KeyValueIntAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        KEYS = ["deploy", "boot"] + Test.list(virtual_device=True)
        for value in values:
            try:
                key, value = value.split("=")
            except ValueError:
                raise argparse.ArgumentError(
                    self, f"Invalid format for '{value}' timeout"
                )
            if key not in KEYS:
                raise argparse.ArgumentError(self, f"Invalid timeout '{key}'")
            try:
                getattr(namespace, self.dest)[key] = int(value)
            except ValueError:
                raise argparse.ArgumentError(
                    self, f"Invalid value for {key} timeout: '{value}'"
                )


class OneTwoPathAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if len(values) == 1:
            values = [values[0], "/"]
        elif len(values) > 2:
            raise argparse.ArgumentError(
                self,
                "takes one or two arguments, first should be a URL and second the destination.",
            )
        try:
            values[0] = pathurlnone(values[0])
        except argparse.ArgumentTypeError as exc:
            raise argparse.ArgumentError(self, str(exc))
        if isinstance(getattr(namespace, self.dest), list):
            getattr(namespace, self.dest).append(values)
        else:
            setattr(namespace, self.dest, values)


class SharedAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values is None:
            return
        if len(values) == 1:
            values = [values[0], "/mnt/tuxrun"]
        if len(values) > 2:
            raise argparse.ArgumentError(
                self,
                "takes zero, one or two arguments, first is the source and the second the destination. The later is optional.",
            )
        setattr(namespace, self.dest, values)


class UpdateCacheAction(argparse.Action):
    def __init__(
        self, option_strings, help, dest=argparse.SUPPRESS, default=argparse.SUPPRESS
    ):
        super().__init__(option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        print("Updating local cache:")
        print("* Rootfs:")
        for device in [
            d for d in Device.list(virtual_device=True) if d.flag_cache_rootfs
        ]:
            print(f"  * {device.name}")
            get_rootfs(
                device, progress=ProgressIndicator.get("Downloading root filesystem")
            )
        print("* Test definitions")
        get_test_definitions(
            progress=ProgressIndicator.get("Downloading test definitions")
        )
        parser.exit()


##########
# Setups #
##########
def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tuxrun", description="TuxRun")

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s, {__version__}"
    )

    group = parser.add_argument_group("listing")
    group.add_argument(
        "--list-devices", action=ListDevicesAction, help="List available devices"
    )
    group.add_argument(
        "--list-tests", action=ListTestsAction, help="List available tests"
    )

    group = parser.add_argument_group("cache")
    group.add_argument(
        "--update-cache", action=UpdateCacheAction, help="Update assets cache"
    )

    group = parser.add_argument_group("artefacts")

    def artefact(name):
        group.add_argument(
            f"--{name}",
            default=None,
            metavar="URL",
            type=pathurlnone,
            help=f"{name} URL",
        )

    artefact("ap-romfw")
    artefact("bios")
    artefact("bl1")
    artefact("ssh-identity-file")
    artefact("dtb")
    artefact("fip")
    artefact("job-definition")
    artefact("kernel")
    artefact("mcp-fw")
    artefact("mcp-romfw")
    group.add_argument(
        "--modules",
        default=None,
        type=str,
        help="modules URL and optionally PATH to extract the modules, default PATH '/'",
        action=OneTwoPathAction,
        nargs="+",
    )
    group.add_argument(
        "--overlay",
        default=[],
        type=str,
        help="Tarball with overlay and optionally PATH to extract the tarball, default PATH '/'. Overlay can be specified multiple times",
        action=OneTwoPathAction,
        nargs="+",
        dest="overlays",
    )
    group.add_argument(
        "--partition",
        default=None,
        metavar="NUMBER",
        type=int,
        help="rootfs partition number",
    )
    artefact("rootfs")
    artefact("scp-fw")
    artefact("scp-romfw")
    group.add_argument(
        "--ssh-host",
        default=None,
        metavar="HOST ADDR",
        type=str,
        help="ssh host address, applicable to ssh-device",
    )
    group.add_argument(
        "--ssh-port",
        default=None,
        metavar="NUMBER",
        type=int,
        help="ssh port number. Defaults to 22, applicable to ssh-device",
    )
    group.add_argument(
        "--ssh-prompt",
        default=None,
        metavar="STRING",
        type=str,
        help="ssh prompt to expect, applicable to ssh-device",
    )
    group.add_argument(
        "--ssh-user",
        default=None,
        metavar="USERNAME",
        type=str,
        help="ssh username, applicable to ssh-device",
    )
    group.add_argument(
        "--tuxbuild",
        metavar="URL",
        default=None,
        type=str,
        help="URL of a TuxBuild build",
    )
    group.add_argument(
        "--tuxmake",
        metavar="DIRECTORY",
        default=None,
        type=str,
        help="directory containing a TuxMake build",
    )
    artefact("test-definitions")
    artefact("uefi")
    group.add_argument(
        "--fvp-ubl-license",
        default=None,
        metavar="FVP UBL License",
        type=str,
        help="UBL License to be passed to FVP that need User Based License. Applicable to FVP device type only",
    )

    group = parser.add_argument_group("secrets")
    group.add_argument(
        "--secrets",
        metavar="K=V",
        default={},
        type=str,
        help="job secrets as key=value",
        action=KeyValueAction,
        nargs="+",
    )

    group = parser.add_argument_group("test parameters")
    group.add_argument(
        "--parameters",
        metavar="K=V",
        default={},
        type=str,
        help="test parameters as key=value",
        action=KeyValueParameterAction,
        nargs="+",
    )
    group.add_argument(
        "--tests",
        nargs="+",
        default=[],
        metavar="T",
        help="test suites",
        choices=Test.list(virtual_device=True),
        action="extend",
    )
    group.add_argument(
        "--shell",
        action="store_true",
        help="Start a shell in the VM",
    )
    group.add_argument(
        "commands",
        nargs="*",
        help="Space separated list of commands to run inside the VM",
    )

    group = parser.add_argument_group("run options")
    group.add_argument(
        "--device",
        default=None,
        metavar="NAME",
        help="Device type",
        choices=[d.name for d in Device.list(virtual_device=True)],
    )
    group.add_argument(
        "--boot-args", default=None, metavar="ARGS", help="extend boot arguments"
    )
    group.add_argument(
        "--prompt", default=None, metavar="PROMPT", help="extra console prompt"
    )
    group.add_argument(
        "--timeouts",
        metavar="K=V",
        default={},
        type=str,
        help="timeouts in minutes as action=duration",
        action=KeyValueIntAction,
        nargs="+",
    )
    group.add_argument(
        "--enable-kvm",
        default=False,
        action="store_true",
        help="Enable kvm, only possible if host and QEMU system are the same",
    )
    group.add_argument(
        "--enable-trustzone",
        default=False,
        action="store_true",
        help="Enable trustzone, applicable to QEMU arm64 device only",
    )

    group.add_argument(
        "--enable-network",
        default=False,
        action="store_true",
        help="Enable network",
    )

    group = parser.add_argument_group("runtime")
    group.add_argument(
        "--runtime",
        default="podman",
        metavar="RUNTIME",
        choices=["docker", "null", "podman"],
        help="Runtime",
    )
    group.add_argument(
        "--image",
        default="docker.io/linaro/tuxrun-dispatcher:latest",
        help="Image to use",
    )
    group.add_argument(
        "--qemu-image", default=None, help="Use qemu from the given container image"
    )

    group.add_argument(
        "--qemu-binary",
        default=None,
        type=Path,
        help="Use qemu from the given path",
    )

    group = parser.add_argument_group("output")
    group.add_argument(
        "--cache-dir",
        default=None,
        type=Path,
        help="Change the cache directory for storing log files, default: XDG_CACHE_DIR",
    )
    group.add_argument(
        "--dispatcher-download-dir",
        default=DEFAULT_DISPATCHER_DOWNLOAD_DIR,
        type=Path,
        help="Change the path that the dispatcher is installed to.",
    )
    group.add_argument(
        "--save-outputs",
        default=False,
        action="store_true",
        help="Automatically save every outputs",
    )
    group.add_argument("--log-file", default=None, type=Path, help="Store logs to file")
    group.add_argument(
        "--log-file-html", default=None, type=Path, help="Store logs to file as HTML"
    )
    group.add_argument(
        "--log-file-text", default=None, type=Path, help="Store logs to file as text"
    )
    group.add_argument(
        "--log-file-yaml", default=None, type=Path, help="Store logs to file as YAML"
    )
    group.add_argument(
        "--metadata", default=None, type=Path, help="Save test metadata to file (JSON)"
    )
    group.add_argument(
        "--results-hook",
        type=str,
        action="append",
        dest="results_hooks",
        metavar="COMMAND",
        help="Execute COMMAND after the run is finished, if the run is successful. Can be specified multiple times. The command is executed with the run output directory (i.e. where all the artifacts are) as working directory. If any results hook fails, tuxrun exits with a non-zero exit code.",
    )
    group.add_argument(
        "--results", default=None, type=Path, help="Save test results to file (JSON)"
    )
    group.add_argument(
        "--lava-definition",
        default=False,
        action="store_true",
        help="Save the LAVA definition.yaml file",
    )
    group.add_argument(
        "--shared",
        default=None,
        type=str,
        help="Directory to share with the device",
        action=SharedAction,
        nargs="*",
    )

    group = parser.add_argument_group("debugging")
    group.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Print more debug information about tuxrun",
    )

    return parser
