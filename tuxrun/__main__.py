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
import shutil
import signal
import subprocess
import sys
import tempfile
from os.path import commonprefix
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

sys.path.append("/usr/share/tuxlava")

from tuxrun import templates  # noqa: E402
from tuxrun.argparse import filter_artefacts, pathurlnone, setup_parser  # noqa: E402
from tuxrun.assets import get_rootfs, get_test_definitions  # noqa: E402
from tuxrun.results import Results  # noqa: E402
from tuxrun.runtimes import Runtime  # noqa: E402
from tuxrun.templates import wrappers  # noqa: E402
from tuxrun.utils import (  # noqa: E402
    ProgressIndicator,
    get_new_output_dir,
    mask_secrets,
    notify,
    DEFAULT_DISPATCHER_DOWNLOAD_DIR,
)
from tuxrun.writer import Writer  # noqa: E402
from tuxrun.yaml import yaml_load  # noqa: E402

from tuxlava.jobs import Job  # type: ignore  # noqa: E402
from tuxlava.exceptions import TuxLavaException  # type: ignore # noqa: E402

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
    def_arguments = {
        "ap_romfw": options.ap_romfw,
        "bios": options.bios,
        "bl1": options.bl1,
        "boot_args": options.boot_args,
        "cache_dir": cache_dir,
        "commands": options.commands,
        "device": options.device,
        "dtb": options.dtb,
        "enable_kvm": options.enable_kvm,
        "enable_trustzone": options.enable_trustzone,
        "enable_network": options.enable_network,
        "fip": options.fip,
        "job_definition": options.job_definition,
        "kernel": options.kernel,
        "mcp_fw": options.mcp_fw,
        "mcp_romfw": options.mcp_romfw,
        "modules": options.modules,
        "overlays": options.overlays,
        "parameters": options.parameters,
        "prompt": options.prompt,
        "qemu_image": options.qemu_image,
        "qemu_binary": options.qemu_binary,
        "rootfs": options.rootfs,
        "rootfs_partition": options.partition,
        "scp_fw": options.scp_fw,
        "scp_romfw": options.scp_romfw,
        "secrets": options.secrets,
        "shared": options.shared,
        "shell": options.shell,
        "ssh_host": options.ssh_host,
        "ssh_identity_file": options.ssh_identity_file,
        "ssh_prompt": options.ssh_prompt,
        "ssh_port": options.ssh_port,
        "ssh_user": options.ssh_user,
        "tests": options.tests,
        "timeouts": options.timeouts,
        "tmpdir": tmpdir,
        "tuxbuild": options.tuxbuild,
        "tuxmake": options.tuxmake,
        "uefi": options.uefi,
    }
    job = Job(**def_arguments)
    job.initialize()
    # Copy extra assets already collected by TuxLAVA
    # TuxLAVA also collects extra assets from device during job.initialize()
    extra_assets = job.extra_assets.copy()

    # Handle rootfs and test definitions separately
    if job.device.flag_cache_rootfs:
        job.rootfs = pathurlnone(
            get_rootfs(
                job.device,
                job.rootfs,
                ProgressIndicator.get("Downloading root filesystem"),
            )
        )

    test_definitions = None
    if any(t.need_test_definition for t in job.tests):
        test_definitions = get_test_definitions(
            options.test_definitions,
            ProgressIndicator.get("Downloading test definitions"),
        )
        job.test_definitions = test_definitions
        extra_assets.append(test_definitions)

    definition = job.render()
    LOG.debug("job definition")
    LOG.debug(definition)

    job_definition = yaml_load(definition)
    job_timeout = (job_definition["timeouts"]["job"]["minutes"] + 1) * 60
    context = job_definition.get("context", {})
    if options.fvp_ubl_license:
        context["fvp_ubl_license"] = options.fvp_ubl_license

    device_dict = job.device.device_dict(context)
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

    # Use a container runtime
    runtime = Runtime.select(options.runtime)(options.dispatcher_download_dir)
    runtime.name(tmpdir.name)
    runtime.image(options.image)

    runtime.bind(tmpdir)
    for path in [
        job.ap_romfw,
        job.bios,
        job.bl1,
        job.dtb,
        job.fip,
        job.kernel,
        job.mcp_fw,
        job.mcp_romfw,
        job.rootfs,
        job.scp_fw,
        job.scp_romfw,
        job.ssh_identity_file,
        job.uefi,
    ] + extra_assets:
        ro = True
        if isinstance(path, tuple):
            (path, ro) = path
        if not path:
            continue
        if urlparse(path).scheme == "file":
            runtime.bind(path[7:], ro=ro)

    if job.qemu_binary:
        overlay_qemu(job.qemu_binary, tmpdir, runtime)

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
    if job.device.flag_use_pre_run_cmd or job.qemu_image:
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

    results = Results(job.tests, artefacts)
    hacking_session = bool("hacking-session" in t.name for t in job.tests)
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

    if not options.device:
        if not (options.tuxmake or options.tuxbuild):
            parser.error("argument --device is required")

    if "hacking-session" in options.tests:
        options.enable_network = True
        if not options.parameters.get("PUB_KEY"):
            parser.error("argument missing --parameters PUB_KEY='...'")

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

    artefacts = filter_artefacts(options)

    # Create the temp directory
    tmpdir = Path(tempfile.mkdtemp(prefix="tuxrun-"))
    LOG.debug(f"temporary directory: '{tmpdir}'")
    try:
        return run(options, tmpdir, cache_dir, artefacts)
    except TuxLavaException as exc:
        parser.error(str(exc))
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
