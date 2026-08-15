# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import argparse
import os
import re
import shlex
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urlparse

from tuxrun import requests, xdg
from tuxrun.yaml import yaml_dump, yaml_load

DEFAULT_DISPATCHER_DOWNLOAD_DIR = "/var/lib/lava/dispatcher/tmp"
SECRET_MASK = "XXXXXXXX"


class ProgressIndicator(ABC):
    @abstractmethod
    def progress(self, percent):
        """
        This method should display the current percentage to the user
        """

    @abstractmethod
    def finish(self):
        """
        This method should display to the user that the process has finished
        """

    @classmethod
    def get(cls, name: str) -> "ProgressIndicator":
        if sys.stderr.isatty():
            return TTYProgressIndicator(name)
        else:
            return NoProgressIndicator()


class NoProgressIndicator(ProgressIndicator):
    def progress(self, percent):
        pass

    def finish(self):
        pass


class TTYProgressIndicator(ProgressIndicator):
    def __init__(self, name):
        self.name = name

    def progress(self, percent: int) -> None:
        sys.stderr.write(f"\r{self.name} ... %3d%%" % percent)

    def finish(self) -> None:
        sys.stderr.write("\n")


def notnone(value, fallback):
    if value is None:
        return fallback
    return value


def get_new_output_dir(cache_dir):
    base = xdg.get_cache_dir() / "tests"
    if cache_dir:
        base = Path(f"{os.path.abspath(cache_dir)}/tests")
    base.mkdir(parents=True, exist_ok=True)
    existing = [int(f.name) for f in base.glob("[0-9]*")]
    if existing:
        new = max(existing) + 1
    else:
        new = 1
    while True:
        new_dir = base / str(new)
        try:
            new_dir.mkdir()
            break
        except FileExistsError:
            new += 1
    return new_dir


def mask_secrets_reproducer(argv):
    """Mask the values of --secrets in a command line."""

    def mask(keyvalue):
        key, sep, _ = keyvalue.partition("=")
        return key + sep + SECRET_MASK if sep else keyvalue

    masked = []
    in_secrets = False
    for arg in argv:
        if arg.startswith("-") and arg != "-":
            option, sep, value = arg.partition("=")
            in_secrets = option == "--secrets"
            if in_secrets and sep:
                arg = option + sep + mask(value)
                in_secrets = False
        elif in_secrets:
            arg = mask(arg)
        masked.append(arg)
    return masked


def save_reproducer(directory, argv):
    # Write and rename, so a kill mid-write leaves no half written script.
    path = directory / "reproducer.sh"
    tmp = directory / "reproducer.sh.tmp"
    lines = ["tuxrun"]
    for arg in mask_secrets_reproducer(argv[1:]):
        # "-" is a value, it means stdout.
        if arg.startswith("-") and arg != "-":
            lines.append(shlex.quote(arg))
        else:
            lines[-1] += " " + shlex.quote(arg)

    command = " \\\n  ".join(lines)
    header = "#!/bin/sh\nset -eu\n"
    if SECRET_MASK in command:
        header += "# Secrets are masked, put the real values back before running.\n"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o700)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(header + "exec " + command + "\n")
    tmp.chmod(0o700)
    os.replace(tmp, path)


def slugify(s):
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s


def pathurlnone(string):
    if string is None:
        return None
    url = urlparse(string)
    if url.scheme in ["http", "https"]:
        return string
    if url.scheme not in ["", "file"]:
        raise argparse.ArgumentTypeError(f"Invalid scheme '{url.scheme}'")

    path = Path(string if url.scheme == "" else url.path)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"{path} no such file or directory")
    return f"file://{path.expanduser().resolve()}"


def callback(dataset=None, header=None, method=None, token=None, url=None, **kwargs):
    if dataset and header and method and token and url:
        s = requests.get_session(retries=3)
        s.headers.update({header: token})
        if method == "POST":
            s.post(url=url)
        if method == "GET":
            s.get(url=url)


def notify(notify):
    if not notify:
        return
    if "callbacks" in notify:
        for cb in notify.get("callbacks"):
            callback(**cb)


def mask_secrets(jobdef: str) -> str:
    data = yaml_load(jobdef)

    def replace_headers(d):
        if isinstance(d, dict):
            for key, value in d.items():
                # 'UrlRepoAction' adds 'url' as an alias to 'repository' for
                # reusing the 'HttpDownloadAction'.
                if key in ["url", "repository"] and isinstance(d.get("headers"), dict):
                    for header_key in d["headers"]:
                        d["headers"][header_key] = SECRET_MASK
                else:
                    replace_headers(value)
        elif isinstance(d, list):
            for item in d:
                replace_headers(item)

    # Mask secrets if they exist
    if "secrets" in data:
        for secret in data["secrets"]:
            data["secrets"][secret] = SECRET_MASK

    # Mask headers anywhere in the structure
    replace_headers(data)

    return yaml_dump(data)
