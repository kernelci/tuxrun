# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

from typing import Dict, List, Optional

import urllib
import yaml
from tuxrun import templates
from tuxrun.devices import Device
from tuxrun.exceptions import InvalidArgument
from tuxrun.utils import compression, notnone, slugify


class FVPDevice(Device):
    flag_use_pre_run_cmd = True
    deploy_timeout = 5

    def device_dict(self, context):
        return templates.devices().get_template("fvp.yaml.jinja2").render(**context)


class AEMvAFVPDevice(FVPDevice):
    name = "fvp-aemva"

    enable_network: bool = True
    flag_cache_rootfs = True
    boot_timeout = 10

    bl1 = "https://storage.tuxboot.com/buildroot/fvp-aemva/bl1.bin"
    dtb = "https://storage.tuxboot.com/buildroot/fvp-aemva/fvp-base-revc.dtb"
    fip = "https://storage.tuxboot.com/buildroot/fvp-aemva/fip.bin"
    kernel = "https://storage.tuxboot.com/buildroot/fvp-aemva/Image"
    rootfs = "https://storage.tuxboot.com/buildroot/fvp-aemva/rootfs.ext4.zst"
    uefi = "https://storage.tuxboot.com/buildroot/fvp-aemva/edk2-flash.img"

    def validate(
        self,
        bl1,
        boot_args,
        commands,
        dtb,
        fip,
        kernel,
        rootfs,
        uefi,
        overlays,
        parameters,
        prompt,
        modules,
        enable_network,
        tests,
        **kwargs,
    ):
        invalid_args = ["--" + k.replace("_", "-") for k in kwargs if kwargs[k]]
        if len(invalid_args) > 0:
            raise InvalidArgument(
                f"Invalid option(s) for fvp devices: {', '.join(sorted(invalid_args))}"
            )

        if boot_args and '"' in boot_args:
            raise InvalidArgument('argument --boot-args should not contains "')
        if prompt and '"' in prompt:
            raise InvalidArgument('argument --prompt should not contains "')
        if modules and compression(modules[0]) not in [("tar", "gz"), ("tar", "xz")]:
            raise InvalidArgument(
                "argument --modules should be a .tar.gz, tar.xz or .tgz"
            )

        for test in tests:
            test.validate(device=self, parameters=parameters, **kwargs)

    def default(self, options) -> None:
        options.bl1 = notnone(options.bl1, self.bl1)
        options.dtb = notnone(options.dtb, self.dtb)
        options.fip = notnone(options.fip, self.fip)
        options.kernel = notnone(options.kernel, self.kernel)
        options.rootfs = notnone(options.rootfs, self.rootfs)
        options.uefi = notnone(options.uefi, self.uefi)

    def definition(self, **kwargs):
        kwargs = kwargs.copy()

        kwargs["no_network"] = not kwargs["enable_network"]

        # Options that can be updated
        if kwargs["tux_prompt"]:
            kwargs["tux_prompt"] = [kwargs["tux_prompt"]]
        else:
            kwargs["tux_prompt"] = []

        kwargs["command_name"] = slugify(
            kwargs.get("parameters").get("command-name", "command")
        )
        kwargs["boot_timeout"] = kwargs["timeouts"].get("boot", self.boot_timeout)
        if not kwargs["timeouts"].get("deploy"):
            kwargs["deploy_timeout"] = self.deploy_timeout + (
                10 if kwargs["tests_timeout"] + kwargs["boot_timeout"] < 15 else 0
            )

        # render the template
        tests = [
            t.render(
                arch="arm64",
                device=kwargs["device"],
                commands=kwargs["commands"],
                command_name=kwargs["command_name"],
                tmpdir=kwargs["tmpdir"],
                overlays=kwargs["overlays"],
                parameters=kwargs["parameters"],
                test_definitions=kwargs["test_definitions"],
            )
            for t in kwargs["tests"]
        ]
        return templates.jobs().get_template("fvp-aemva.yaml.jinja2").render(
            **kwargs
        ) + "".join(tests)

    def extra_assets(self, tmpdir, dtb, kernel, tux_boot_args, **kwargs):
        dtb = notnone(dtb, self.dtb).split("/")[-1]
        kernel = notnone(kernel, self.kernel).split("/")[-1]
        # Drop the extension if the kernel is compressed. LAVA will decompress it for us.
        if compression(kernel)[1]:
            kernel = kernel[: -1 - len(compression(kernel)[1])]
        (tmpdir / "startup.nsh").write_text(
            f"{kernel} dtb={dtb} systemd.log_level=warning {tux_boot_args + ' ' if tux_boot_args else ''}console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp",
            encoding="utf-8",
        )
        return [f"file://{tmpdir / 'startup.nsh'}"]


class MorelloFVPDevice(FVPDevice):
    mandatory = [
        "ap_romfw",
        "mcp_fw",
        "mcp_romfw",
        "rootfs",
        "scp_fw",
        "scp_romfw",
        "fip",
    ]

    prompts: List[str] = []
    auto_login: Dict[str, str] = {}
    boot_timeout = 20
    kernel_start_message: Optional[str] = None
    support_tests = False
    rootfs: Optional[str] = None

    def validate(
        self,
        ap_romfw,
        mcp_fw,
        mcp_romfw,
        rootfs,
        scp_fw,
        scp_romfw,
        overlays,
        parameters,
        tests,
        fip,
        **kwargs,
    ):
        invalid_args = ["--" + k.replace("_", "-") for k in kwargs if kwargs[k]]
        if len(invalid_args) > 0:
            raise InvalidArgument(
                f"Invalid option(s) for fvp-morello devices: {', '.join(sorted(invalid_args))}"
            )

        args = locals()
        missing_args = [
            "--" + k.replace("_", "-") for k in self.mandatory if not args[k]
        ]
        if len(missing_args) > 0:
            raise InvalidArgument(
                f"Missing option(s) for fvp devices: {', '.join(sorted(missing_args))}"
            )

        if tests and not self.support_tests:
            raise InvalidArgument("Tests are not supported on this device")

        if self.rootfs and rootfs:
            raise InvalidArgument("Invalid option for this fvp device: --rootfs")

        for test in tests:
            test.validate(device=self, parameters=parameters, **kwargs)

    def default(self, options) -> None:
        if self.rootfs:
            options.rootfs = notnone(options.rootfs, self.rootfs)

    def definition(self, **kwargs):
        kwargs = kwargs.copy()

        # Options that can *not* be updated
        kwargs["prompts"] = self.prompts.copy()
        kwargs["auto_login"] = self.auto_login.copy()
        kwargs["kernel_start_message"] = self.kernel_start_message
        kwargs["support_tests"] = self.support_tests
        kwargs["boot_timeout"] = kwargs["timeouts"].get("boot", self.boot_timeout)

        if not kwargs["timeouts"].get("deploy"):
            kwargs["deploy_timeout"] = self.deploy_timeout + (
                10 if kwargs["tests_timeout"] + kwargs["boot_timeout"] < 15 else 0
            )

        # render the template
        tests = [
            t.render(
                tmpdir=kwargs["tmpdir"],
                parameters=kwargs["parameters"],
                prompts=kwargs["prompts"],
            )
            for t in kwargs["tests"]
        ]
        return (
            templates.jobs().get_template("fvp-morello.yaml.jinja2").render(**kwargs)
            + "\n"
            + "".join(tests)
        )


class FVPMorelloAndroid(MorelloFVPDevice):
    name = "fvp-morello-android"

    prompts = ["console:/ "]
    support_tests = True


class FVPMorelloBusybox(MorelloFVPDevice):
    name = "fvp-morello-busybox"

    prompts = ["/ # "]
    support_tests = True
    virtiop9_path = "/etc"


class FVPMorelloDebian(MorelloFVPDevice):
    name = "fvp-morello-debian"

    prompts = ["morello-deb:~#", "root@morello:~#"]
    support_tests = True
    auto_login = {
        "login_prompt": "login:",
        "username": "root",
        "password_prompt": "Password:",
        "password": "morello",
    }


class FVPMorelloBaremetal(MorelloFVPDevice):
    name = "fvp-morello-baremetal"

    mandatory = ["ap_romfw", "mcp_fw", "mcp_romfw", "scp_fw", "scp_romfw", "fip"]
    prompts = ["hello"]
    kernel_start_message = "Booting Trusted Firmware"


class FVPMorelloOE(MorelloFVPDevice):
    name = "fvp-morello-oe"

    prompts = ["root@morello-fvp:~# "]
    support_tests = True


class FVPMorelloUbuntu(MorelloFVPDevice):
    name = "fvp-morello-ubuntu"

    mandatory = ["ap_romfw", "mcp_fw", "mcp_romfw", "scp_fw", "scp_romfw", "fip"]

    prompts = ["morello@morello-server:"]
    auto_login = {
        "login_prompt": "morello-server login:",
        "username": "morello",
        "password_prompt": "Password:",
        "password": "morello",
    }
    boot_timeout = 60
    rootfs = "https://storage.tuxboot.com/fvp-morello-ubuntu/ubuntu.satadisk.xz"


class FVPMorelloGrub(MorelloFVPDevice):
    name = "fvp-morello-grub"

    kernel_start_message = "Press enter to boot the selected OS"
    prompts = ["highlighted entry will be executed"]
    support_tests = True


class FVPLAVA(FVPDevice):
    name = "fvp-lava"

    def validate(self, job_definition, **kwargs):
        if not job_definition:
            raise InvalidArgument("Missing argument --job-definition")
        parsed_url = urllib.parse.urlparse(job_definition)
        job_definition = urllib.parse.unquote(parsed_url.path)
        with open(job_definition, "r") as job_file:
            try:
                # Load yaml and dump data as string to verify that
                # lava job definition is valid
                yaml_data = yaml.dump(yaml.safe_load(job_file))
                self.job_definition = yaml_data
            except Exception:
                raise InvalidArgument("Unable to load LAVA job definition")
        return

    def default(self, options) -> None:
        ...  # noqa: E704

    def definition(self, **kwargs):
        return self.job_definition
