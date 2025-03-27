# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import os
import re
import sys
import time
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


def __download_and_cache__(
    url: str, progress: ProgressIndicator = NoProgressIndicator()
):
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        return url

    key = re.sub(r"[:/]", "_", url)

    cache_dir = get_cache_dir().resolve() / "assets"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / key
    cache_etag_file = cache_dir / (key + ".etag")

    expired = False
    if cache.exists():
        timestamp = os.stat(cache).st_mtime
        now = time.time()
        timeout = 6 * 60 * 60  # 6 hours

        expired = (now - timestamp) > timeout
        if not expired:
            return str(cache)

    try:
        response = requests_get(url, allow_redirects=True, stream=True)
        response.raise_for_status()
        etag = str(response.headers["ETag"])
    except KeyError:
        print("Missing ETag, continuing without cache", file=sys.stderr)
        return url
    except Exception as e:
        if cache.exists():
            print(e, "Continuing with cached version of the file", file=sys.stderr)
            return str(cache)
        # return url as LAVA will check if it exists and it will show up in the logfile.
        return url

    if cache_etag_file.exists():
        cache_etag = cache_etag_file.read_text()
    else:
        cache_etag = None
    if cache_etag == etag and cache.exists():
        response.close()
        return str(cache)
    else:
        cache_etag_file.write_text(etag)

    size = int(response.headers.get("Content-Length", "0"))
    try:
        with cache.open("wb") as data:
            n = 0
            for chunk in response.iter_content(chunk_size=4096):
                n += data.write(chunk)
                if size:
                    progress.progress(100 * n / size)
    except requests.RequestException as e:
        print(f"Unable to fetch url '{url}': {e}", file=sys.stderr)
        raise

    if size:
        progress.finish()

    return str(cache.resolve())
