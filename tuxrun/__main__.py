#!/usr/bin/python3
# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import contextlib
import json
import logging
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from os.path import commonprefix
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from tuxrun import templates
from tuxrun.argparse import filter_artefacts, filter_options, pathurlnone, setup_parser
from tuxrun.assets import get_rootfs, get_test_definitions
from tuxrun.devices import Device
from tuxrun.exceptions import InvalidArgument
from tuxrun.results import Results
from tuxrun.runtimes import Runtime
from tuxrun.templates import wrappers
from tuxrun.tests import Test
from tuxrun.utils import (
    ProgressIndicator,
    get_new_output_dir,
    mask_secrets,
    notify,
    DEFAULT_DISPATCHER_DOWNLOAD_DIR,
)
from tuxrun.writer import Writer
from tuxrun.yaml import yaml_load

###########
# GLobals #
###########
LOG = logging.getLogger("tuxrun")


###########
# Helpers #
###########
def overlay_qemu(qemu_binary, tmpdir, runtime):
    """
    Overlay an external QEMU into the container, taking care to also
    include the libraries needed and the environment tweaks.
    """

    # we want to collect a unique set() of paths
    host_lib_paths = set()

    # work out the loader
    interp = subprocess.check_output(["readelf", "-p", ".interp", qemu_binary]).decode(
        "utf-8"
    )

    search = re.search(r"(\/\S+)", interp)
    if search and search.group(1):
        loader = Path(search.group(1)).resolve().absolute()
        if loader:
            host_lib_paths.add(loader.parents[0])

    ldd_re = re.compile(r"(?:\S+ \=\> )(\S*) \(:?0x[0-9a-f]+\)")
    try:
        ldd_output = subprocess.check_output(["ldd", qemu_binary]).decode("utf-8")
        for line in ldd_output.split("\n"):
            search = ldd_re.search(line)
            if search and search.group(1):
                lib = Path(search.group(1))
                if lib.parents[0].absolute():
                    host_lib_paths.add(lib.parents[0])
                else:
                    print(f"skipping {lib.parents[0]}")
    except subprocess.CalledProcessError:
        print(f"{qemu_binary} had no associated libraries (static build?)")

    # only unique
    dest_lib_search = []

    for hl in host_lib_paths:
        dst_lib = Path("/opt/host/", hl.relative_to("/"))
        runtime.bind(hl, dst=dst_lib, ro=True)
        dest_lib_search.append(dst_lib)

    # Also account for firmware
    firmware = subprocess.check_output([qemu_binary, "-L", "help"]).decode("utf-8")
    fw_dirs = [
        Path(p)
        for p in firmware.split("\n")
        if Path(p).exists() and Path(p).is_absolute()
    ]

    # The search path can point to a directory of symlinks to the real
    # firmware so we need to resolve the path of each file in the
    # search path to find the real set of directories we need
    unique_fw_dirs = set()
    for d in fw_dirs:
        for f in d.glob("*"):
            if f.exists() and f.is_file():
                unique_fw_dirs.add(f.resolve().parent)

    common_prefix = commonprefix([str(p) for p in unique_fw_dirs])
    dest_fw_search = []

    for p in unique_fw_dirs:
        fw_path = p.relative_to(common_prefix)
        cont_fw_path = Path("/opt/host/firmware", fw_path)
        runtime.bind(p, cont_fw_path, ro=True)
        dest_fw_search.append(cont_fw_path)

    # write out a wrapper to call QEMU with the appropriate setting
    # of search_path.
    search_path = ":".join(map(str, dest_lib_search))
    fw_paths = " -L ".join(map(str, dest_fw_search))
    loader = Path("/opt/host/", loader.relative_to("/"))
    # Render and bind the docker wrapper
    wrap = (
        wrappers()
        .get_template("host-qemu.jinja2")
        .render(search_path=search_path, loader=loader, fw_paths=fw_paths)
    )
    LOG.debug("overlay_qemu wrapper")
    LOG.debug(wrap)
    basename = qemu_binary.name
    (tmpdir / f"{basename}").write_text(wrap, encoding="utf-8")
    (tmpdir / f"{basename}").chmod(0o755)

    # Substitute the container's binary with host's wrapper
    runtime.bind(Path(tmpdir, basename), Path("/usr/bin/", basename), ro=True)

    # Finally map QEMU itself where the wrapper can find it
    dest_path = Path("/opt/host/qemu.real")
    runtime.bind(qemu_binary, dst=dest_path, ro=True)


def run_hooks(hooks, cwd):
    if not hooks:
        return 0
    for hook in hooks:
        try:
            print(hook)
            subprocess.check_call(["sh", "-c", hook], cwd=str(cwd))
        except subprocess.CalledProcessError as e:
            sys.stderr.write(f"hook `{hook}` failed with exit code {e.returncode}\n")
            return 2
    return 0


def run_hacking_sesson(definition, case, test):
    if definition == "hacking-session" and case == "tmate" and "reference" in test:
        if sys.stdout.isatty():
            subprocess.Popen(
                [
                    "xterm",
                    "-e",
                    "bash",
                    "-c",
                    f"ssh {test['reference']}",
                ]
            )


##############
# Entrypoint #
##############
def run(options, tmpdir: Path, cache_dir: Optional[Path], artefacts: dict) -> int:
    # Render the job definition and device dictionary
    extra_assets = []
    overlays = []

    if options.modules:
        overlays.append(("modules", options.modules[0], options.modules[1]))
        extra_assets.append(options.modules[0])

    # When using --shared without any arguments, point to cache_dir
    if options.shared is not None:
        if not options.shared:
            assert cache_dir
            options.shared = [str(cache_dir), "/mnt/tuxrun"]
        extra_assets.append(("file://" + options.shared[0], False))

    for index, item in enumerate(options.overlays):
        overlays.append((f"overlay-{index:02}", item[0], item[1]))
        extra_assets.append(item[0])

    # Add test definitions only when needed
    test_definitions = None
    if any(t.need_test_definition for t in options.tests):
        test_definitions = get_test_definitions(
            options.test_definitions,
            ProgressIndicator.get("Downloading test definitions"),
        )
        extra_assets.append(test_definitions)

    # Add extra assets from parameters
    for k, v in options.parameters.items():
        if v.startswith("file://"):
            extra_assets.append(v)

    commands = " ".join([shlex.quote(s) for s in options.commands])

    def_arguments = {
        "bios": options.bios,
        "bl1": options.bl1,
        "commands": commands,
        "device": options.device,
        "qemu_image": options.qemu_image,
        "dtb": options.dtb,
        "kernel": options.kernel,
        "ap_romfw": options.ap_romfw,
        "mcp_fw": options.mcp_fw,
        "mcp_romfw": options.mcp_romfw,
        "fip": options.fip,
        "enable_kvm": options.enable_kvm,
        "enable_trustzone": options.enable_trustzone,
        "enable_network": options.enable_network,
        "overlays": overlays,
        "prompt": options.prompt,
        "rootfs": options.rootfs,
        "rootfs_partition": options.partition,
        "shared": options.shared,
        "scp_fw": options.scp_fw,
        "scp_romfw": options.scp_romfw,
        "ssh_host": options.ssh_host,
        "ssh_prompt": options.ssh_prompt,
        "ssh_port": options.ssh_port,
        "ssh_user": options.ssh_user,
        "tests": options.tests,
        "test_definitions": test_definitions,
        "tests_timeout": sum(t.timeout for t in options.tests),
        "timeouts": options.timeouts,
        "tmpdir": tmpdir,
        "tux_boot_args": (
            " ".join(shlex.split(options.boot_args)) if options.boot_args else None
        ),
        "tux_prompt": options.prompt,
        "parameters": options.parameters,
        "uefi": options.uefi,
        "boot_args": options.boot_args,
        "secrets": options.secrets,
    }
    definition = options.device.definition(**def_arguments)
    LOG.debug("job definition")
    LOG.debug(definition)

    job_definition = yaml_load(definition)
    job_timeout = (job_definition["timeouts"]["job"]["minutes"] + 1) * 60
    context = job_definition.get("context", {})
    if options.fvp_ubl_license:
        context["fvp_ubl_license"] = options.fvp_ubl_license

    device_dict = options.device.device_dict(context)
    LOG.debug("device dictionary")
    LOG.debug(device_dict)

    (tmpdir / "definition.yaml").write_text(definition, encoding="utf-8")
    (tmpdir / "device.yaml").write_text(device_dict, encoding="utf-8")

    # Render the dispatcher.yaml
    (tmpdir / "dispatcher").mkdir()
    dispatcher = (
        templates.dispatchers()
        .get_template("dispatcher.yaml.jinja2")
        .render(
            dispatcher_download_dir=options.dispatcher_download_dir, prefix=tmpdir.name
        )
    )
    LOG.debug("dispatcher config")
    LOG.debug(dispatcher)
    (tmpdir / "dispatcher.yaml").write_text(dispatcher, encoding="utf-8")

    # Add extra assets from device
    extra_assets.extend(options.device.extra_assets(**def_arguments))

    # Use a container runtime
    runtime = Runtime.select(options.runtime)(options.dispatcher_download_dir)
    runtime.name(tmpdir.name)
    runtime.image(options.image)

    runtime.bind(tmpdir)
    for path in [
        options.ap_romfw,
        options.bios,
        options.bl1,
        options.dtb,
        options.fip,
        options.kernel,
        options.mcp_fw,
        options.mcp_romfw,
        options.rootfs,
        options.scp_fw,
        options.scp_romfw,
        options.ssh_identity_file,
        options.uefi,
    ] + extra_assets:
        ro = True
        if isinstance(path, tuple):
            (path, ro) = path
        if not path:
            continue
        if urlparse(path).scheme == "file":
            runtime.bind(path[7:], ro=ro)

    if options.qemu_binary:
        overlay_qemu(options.qemu_binary, tmpdir, runtime)

    # Forward the signal to the runtime
    def handler(*_):
        LOG.debug("Signal received")
        runtime.kill()

    signal.signal(signal.SIGHUP, handler)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGQUIT, handler)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGUSR1, handler)
    signal.signal(signal.SIGUSR2, handler)

    # Set the overall timeout
    signal.signal(signal.SIGALRM, handler)
    LOG.debug("Job timeout %ds", job_timeout)
    signal.alarm(job_timeout)

    # start the pre_run command
    if options.device.flag_use_pre_run_cmd or options.qemu_image:
        LOG.debug("Pre run command")
        runtime.bind(
            tmpdir / "dispatcher" / "tmp",
            options.dispatcher_download_dir,
        )
        (tmpdir / "dispatcher" / "tmp").mkdir()
        runtime.pre_run(tmpdir)

    # Build the lava-run arguments list
    args = [
        "lava-run",
        "--device",
        str(tmpdir / "device.yaml"),
        "--dispatcher",
        str(tmpdir / "dispatcher.yaml"),
        "--job-id",
        "1",
        "--output-dir",
        "output",
        str(tmpdir / "definition.yaml"),
    ]

    if options.dispatcher_download_dir != Path(DEFAULT_DISPATCHER_DOWNLOAD_DIR):
        args.append("--skip-sudo-warning")

    results = Results(options.tests, artefacts)
    hacking_session = bool("hacking-session" in t.name for t in options.tests)
    # Start the writer (stdout or log-file)
    with Writer(
        options.log_file,
        options.log_file_html,
        options.log_file_text,
        options.log_file_yaml,
    ) as writer:
        # Start the runtime
        with runtime.run(args):
            for line in runtime.lines():
                writer.write(line)
                res = results.parse(line)
                # Start an xterm if an hacking session url is available
                if hacking_session and res:
                    run_hacking_sesson(*res)

    runtime.post_run()
    if options.results:
        if str(options.results) == "-":
            sys.stdout.write(json.dumps(results.data) + "\n")
        else:
            options.results.write_text(json.dumps(results.data))
    if options.metadata:
        if str(options.metadata) == "-":
            sys.stdout.write(json.dumps(results.metadata) + "\n")
        else:
            options.metadata.write_text(json.dumps(results.metadata))

    if options.lava_definition and cache_dir:
        (cache_dir / "definition.yaml").write_text(
            mask_secrets(definition), encoding="utf-8"
        )

    notify(job_definition.get("notify", {}))

    # Run results-hooks only if everything was successful
    if cache_dir:
        print(f"TuxRun outputs saved to {cache_dir}")
    return max([runtime.ret(), results.ret()]) or run_hooks(
        options.results_hooks, cache_dir
    )


def main() -> int:
    # Parse command line
    parser = setup_parser()
    options = parser.parse_args()

    # Setup logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if options.debug else logging.INFO)

    if options.tuxbuild or options.tuxmake:
        tux = options.tuxbuild or options.tuxmake
        options.kernel = options.kernel or tux.kernel
        options.modules = options.modules or tux.modules
        options.device = options.device or f"qemu-{tux.target_arch}"
        if options.device == "qemu-armv5":
            options.dtb = tux.url + "/dtbs/versatile-pb.dtb"
        if options.parameters:
            if options.modules:
                module, path = options.modules
                modules_path = options.parameters.get("MODULES_PATH", path)
                options.modules = [module, modules_path]

            for k in options.parameters:
                if isinstance(options.parameters[k], str):
                    options.parameters[k] = options.parameters[k].replace(
                        "$BUILD/", tux.url + "/"
                    )

    if options.shell:
        if "hacking-session" not in options.tests:
            options.tests.append("hacking-session")
        if not options.parameters.get("PUB_KEY"):
            keys = list(Path("~/.ssh/").expanduser().glob("id_*.pub"))
            if len(keys) == 0:
                parser.error("no ssh public key in ~/.ssh/")
            options.parameters["PUB_KEY"] = "\n\n".join(
                k.read_text(encoding="utf-8").rstrip() for k in keys
            )

    cache_dir = None
    if options.lava_definition or options.results_hooks or options.shared == []:
        options.save_outputs = True
    if options.save_outputs:
        if any(
            o is None
            for o in [
                options.log_file,
                options.log_file_html,
                options.log_file_text,
                options.log_file_yaml,
                options.results,
            ]
        ):
            cache_dir = get_new_output_dir(options.cache_dir)
            if options.log_file is None:
                options.log_file = cache_dir / "logs"
            if options.log_file_html is None:
                options.log_file_html = cache_dir / "logs.html"
            if options.log_file_text is None:
                options.log_file_text = cache_dir / "logs.txt"
            if options.log_file_yaml is None:
                options.log_file_yaml = cache_dir / "logs.yaml"
            if options.metadata is None:
                options.metadata = cache_dir / "metadata.json"
            if options.results is None:
                options.results = cache_dir / "results.json"
    elif options.log_file is None:
        options.log_file = "-"

    if not options.device:
        parser.error("argument --device is required")

    if options.commands:
        options.tests.append("commands")

    if "hacking-session" in options.tests:
        options.enable_network = True
        if not options.parameters.get("PUB_KEY"):
            parser.error("argument missing --parameters PUB_KEY='...'")

    try:
        options.device = Device.select(options.device)()
        options.tests = [Test.select(t)(options.timeouts.get(t)) for t in options.tests]
        # options.rootfs will be overridden later on by get_rootfs
        options.device.validate(**filter_options(options))
        options.device.default(options)
    except InvalidArgument as exc:
        parser.error(str(exc))

    if options.shared is not None and not options.device.name.startswith("qemu-"):
        parser.error("--shared options is only available for qemu devices")

    if options.tests:
        tests = [t.name for t in options.tests]
        if sorted(list(set(tests))) != sorted(tests):
            parser.error("each test should appears only once")

    artefacts = filter_artefacts(options)

    # Download only after the device has been found
    if options.device.flag_cache_rootfs:
        options.rootfs = pathurlnone(
            get_rootfs(
                options.device,
                options.rootfs,
                ProgressIndicator.get("Downloading root filesystem"),
            )
        )

    # Create the temp directory
    tmpdir = Path(tempfile.mkdtemp(prefix="tuxrun-"))
    LOG.debug(f"temporary directory: '{tmpdir}'")
    try:
        return run(options, tmpdir, cache_dir, artefacts)
    except Exception as exc:
        LOG.error("Raised an exception %s", exc)
        raise
    finally:
        with contextlib.suppress(FileNotFoundError, PermissionError):
            shutil.rmtree(tmpdir)


def start():
    if __name__ == "__main__":
        sys.exit(main())


start()
