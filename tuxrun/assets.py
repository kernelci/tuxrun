# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from tuxrun.requests import requests_get
from tuxrun.utils import NoProgressIndicator, ProgressIndicator, pathurlnone
from tuxrun.xdg import get_cache_dir
from tuxlava.jobs import TEST_DEFINITIONS  # type: ignore


def get_rootfs(
    device, rootfs: str = "", progress: ProgressIndicator = NoProgressIndicator()
) -> str:
    return __download_and_cache__(rootfs or device.rootfs, progress)


def get_test_definitions(
    test_definitions: str = "", progress: ProgressIndicator = NoProgressIndicator()
):
    return pathurlnone(
        __download_and_cache__(test_definitions or TEST_DEFINITIONS, progress)
    )


def __cache_dir__():
    cache_dir = get_cache_dir().resolve() / "assets"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def __cache_key__(url):
    return re.sub(r"[:/]", "_", url)


def __temp_file__(path):
    return path.with_name(f"{path.name}.{os.getpid()}.tmp")


def __cache_is_fresh__(cache):
    timeout = 6 * 60 * 60
    return cache.exists() and (time.time() - os.stat(cache).st_mtime) <= timeout


def __get__(url):
    response = requests_get(url, allow_redirects=True, stream=True)
    response.raise_for_status()
    return response


def __save__(response, url, cache, progress):
    etag_file = cache.with_name(cache.name + ".etag")
    etag = response.headers.get("ETag")
    if etag is not None:
        etag = str(etag)
        cached = cache.exists() and etag_file.exists()
        if cached and etag_file.read_text() == etag:
            response.close()
            return cache

    size = int(response.headers.get("Content-Length", "0"))
    tmp = __temp_file__(cache)
    try:
        with tmp.open("wb") as data:
            n = 0
            for chunk in response.iter_content(chunk_size=4096):
                n += data.write(chunk)
                if size:
                    progress.progress(100 * n / size)
        tmp.replace(cache)
    except requests.RequestException as e:
        print(f"Unable to fetch url '{url}': {e}", file=sys.stderr)
        raise
    finally:
        tmp.unlink(missing_ok=True)

    if etag is None:
        etag_file.unlink(missing_ok=True)
    else:
        etag_file.write_text(etag)

    if size:
        progress.finish()

    return cache.resolve()


def __download__(url: str, progress: ProgressIndicator = NoProgressIndicator()) -> Path:
    cache = __cache_dir__() / __cache_key__(url)
    if __cache_is_fresh__(cache):
        return cache

    try:
        response = __get__(url)
    except requests.RequestException as e:
        if cache.exists():
            print(e, "Continuing with cached version of the file", file=sys.stderr)
            return cache
        raise

    return __save__(response, url, cache, progress)


def __download_and_cache__(
    url: str, progress: ProgressIndicator = NoProgressIndicator()
):
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        return url

    cache = __cache_dir__() / __cache_key__(url)
    if __cache_is_fresh__(cache):
        return str(cache)

    try:
        response = __get__(url)
    except Exception as e:
        if cache.exists():
            print(e, "Continuing with cached version of the file", file=sys.stderr)
            return str(cache)
        # return url as LAVA will check if it exists and it will show up in the logfile.
        return url

    if response.headers.get("ETag") is None:
        response.close()
        print("Missing ETag, continuing without cache", file=sys.stderr)
        return url

    return str(__save__(response, url, cache, progress))
