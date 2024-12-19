# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import contextlib
import logging
import os
import signal
import subprocess
import time
from pathlib import Path

from tuxrun.templates import wrappers

BASE = (Path(__file__) / "..").resolve()
LOG = logging.getLogger("tuxrun")


class Runtime:
    binary = ""
    container = False
    prefix = [""]

    def __init__(self, dispatcher_download_dir):
        self.dispatcher_download_dir = dispatcher_download_dir
        self.__bindings__ = []
        self.__image__ = None
        self.__name__ = None
        self.__pre_proc__ = None
        self.__proc__ = None
        self.__sub_procs__ = []
        self.__ret__ = None

    @classmethod
    def select(cls, name):
        if name == "docker":
            return DockerRuntime
        if name == "podman":
            return PodmanRuntime
        return NullRuntime

    def bind(self, src, dst=None, ro=False, device=False):
        if dst is None:
            dst = src
        self.__bindings__.append((str(src), dst, ro, device))

    def image(self, image):
        self.__image__ = image

    def name(self, name):
        self.__name__ = name

    def pre_run(self, tmpdir):
        pass

    def post_run(self):
        pass

    def cmd(self, args):
        raise NotImplementedError()  # pragma: no cover

    @contextlib.contextmanager
    def run(self, args):
        args = self.cmd(args)
        LOG.debug("Calling %s", " ".join(args))
        try:
            self.__proc__ = subprocess.Popen(
                args,
                bufsize=1,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setpgrp,
            )
            yield
        except FileNotFoundError as exc:
            LOG.error("File not found '%s'", exc.filename)
            raise
        except Exception as exc:
            LOG.exception(exc)
            if self.__proc__ is not None:
                self.kill()
                _, errs = self.__proc__.communicate()
                for err in [e for e in errs.split("\n") if e]:
                    LOG.error("err: %s", err)
            raise
        finally:
            if self.__proc__ is not None:
                self.__ret__ = self.__proc__.wait()
            for proc in self.__sub_procs__:
                proc.wait()

    def lines(self):
        return self.__proc__.stderr

    def kill(self):
        if self.__proc__:
            self.__proc__.send_signal(signal.SIGTERM)

    def ret(self):
        return self.__ret__


class ContainerRuntime(Runtime):
    bind_guestfs = True
    container = True

    def __init__(self, dispatcher_download_dir):
        super().__init__(dispatcher_download_dir)
        self.bind("/boot", ro=True)
        self.bind("/lib/modules", ro=True)
        # Bind /dev/kvm is available
        if Path("/dev/kvm").exists():
            self.bind("/dev/kvm", device=True)
        # Create /var/tmp/.guestfs-$id
        if self.bind_guestfs:
            guestfs = Path(f"/var/tmp/.guestfs-{os.getuid()}")
            guestfs.mkdir(exist_ok=True)
            self.bind(guestfs, "/var/tmp/.guestfs-0")

    def cmd(self, args):
        prefix = self.prefix.copy()
        srcs = set()
        dsts = set()
        for binding in self.__bindings__:
            (src, dst, ro, device) = binding
            if src in srcs:
                LOG.error("Duplicated mount source %r", src)
                raise Exception("Duplicated mount source %r" % src)
            if dst in dsts:
                LOG.error("Duplicated mount destination %r", dst)
                raise Exception("Duplicated mount destination %r" % dst)
            srcs.add(src)
            dsts.add(dst)
            ro = "ro" if ro else "rw"
            prefix.extend(["--device" if device else "-v", f"{src}:{dst}:{ro}"])
        prefix.extend(["--name", self.__name__])
        return prefix + [self.__image__] + args

    def kill(self):
        args = [self.binary, "stop", "--time", "60", self.__name__]
        with contextlib.suppress(FileNotFoundError):
            proc = subprocess.Popen(
                args,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                preexec_fn=os.setpgrp,
            )
            self.__sub_procs__.append(proc)


class DockerRuntime(ContainerRuntime):
    # Do not bind or libguestfs will fail at runtime
    # "security: cached appliance /var/tmp/.guestfs-0 is not owned by UID 0"
    bind_guestfs = False
    binary = "docker"
    prefix = ["docker", "run", "--rm", "--hostname", "tuxrun"]

    def pre_run(self, tmpdir):
        # Render and bind the docker wrapper
        wrap = (
            wrappers()
            .get_template("docker.jinja2")
            .render(
                runtime="docker",
                volume=str(tmpdir / "dispatcher" / "tmp"),
                dispatcher_download_dir=self.dispatcher_download_dir,
            )
        )
        LOG.debug("docker wrapper")
        LOG.debug(wrap)
        (tmpdir / "docker").write_text(wrap, encoding="utf-8")
        (tmpdir / "docker").chmod(0o755)
        self.bind(str(tmpdir / "docker"), "/usr/local/bin/docker", True)

        # Bind the docker socket
        self.bind("/var/run/docker.sock")


class PodmanRuntime(ContainerRuntime):
    binary = "podman"
    prefix = ["podman", "run", "--log-driver=none", "--rm", "--hostname", "tuxrun"]
    network = None

    def pre_run(self, tmpdir):
        # Render and bind the docker wrapper
        self.network = os.path.basename(tmpdir)
        self.prefix.extend(["--network", self.network])
        subprocess.run(["podman", "network", "create", self.network])
        wrap = (
            wrappers()
            .get_template("docker.jinja2")
            .render(
                runtime="podman",
                volume=str(tmpdir / "dispatcher" / "tmp"),
                network=self.network,
                dispatcher_download_dir=self.dispatcher_download_dir,
            )
        )
        LOG.debug("docker wrapper")
        LOG.debug(wrap)
        (tmpdir / "docker").write_text(wrap, encoding="utf-8")
        (tmpdir / "docker").chmod(0o755)
        self.bind(str(tmpdir / "docker"), "/usr/local/bin/docker", True)

        # Start podman system service and bind the socket
        socket = tmpdir / "podman.sock"
        self.bind(socket, "/run/podman/podman.sock")

        args = [
            self.binary,
            "system",
            "service",
            "--time",
            "0",
            f"unix://{socket}",
        ]
        self.__pre_proc__ = subprocess.Popen(
            args,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            preexec_fn=os.setpgrp,
        )
        # wait for the socket
        for _ in range(60):
            if socket.exists():
                return
            time.sleep(1)
        raise Exception(f"Unable to create podman socket at {socket}")

    def post_run(self):
        if self.network:
            subprocess.run(["podman", "network", "rm", self.network])
        if self.__pre_proc__ is None:
            return
        self.__pre_proc__.kill()
        self.__pre_proc__.wait()


class NullRuntime(Runtime):
    def cmd(self, args):
        return args
