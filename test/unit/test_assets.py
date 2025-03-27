import subprocess
import time
from hashlib import sha1
from pathlib import Path

import pytest

from tuxrun.assets import get_rootfs
from tuxlava.devices import Device  # type: ignore

seven_hours = 7 * 60 * 60


def rewind_timestamp(filename, interval):
    past = time.time() - interval
    subprocess.check_call(["touch", "-d", f"@{past}", str(filename)])


class TestGetRootfs:
    def test_local_file(self):
        assert (
            get_rootfs(Device.select("qemu-arm64"), "/path/to/file") == "/path/to/file"
        )

    def test_default(self):
        rootfs = get_rootfs(Device.select("qemu-arm64"))
        assert Path(rootfs).exists()

    def test_downloads_remote_file(self, get, mocker):
        rootfs = get_rootfs(
            Device.select("qemu-arm64"), "https://example.com/rootfs.img"
        )
        assert Path(rootfs).exists()
        get.assert_called()
        assert get.call_args[0][0] == "https://example.com/rootfs.img"

    def test_caches_downloads(self, get):
        get_rootfs(Device.select("qemu-arm64"))
        get_rootfs(Device.select("qemu-arm64"))
        assert get.call_count == 1

    def test_writes_data_to_disk(self, response):
        response.iter_content.return_value = [b"123"]
        rootfs = get_rootfs(Device.select("qemu-x86_64"))
        assert Path(rootfs).read_text() == "123"

    @pytest.fixture
    def build_response(self, mocker):
        def __build_response__(data):
            r = mocker.MagicMock()
            r.iter_content.return_value = [data]
            data_hash = sha1(data).hexdigest()
            r.headers = {"ETag": f'"{data_hash}"', "Content-Length": str(len(data))}
            return r

        return __build_response__

    def test_update_after_6h_if_etag_changed(self, get, build_response):
        response1 = build_response(b"123")
        response2 = build_response(b"456")
        get.side_effect = [response1, response2]

        rootfs = get_rootfs(Device.select("qemu-x86_64"))
        rewind_timestamp(rootfs, seven_hours)

        rootfs = get_rootfs(Device.select("qemu-x86_64"))
        assert Path(rootfs).read_text() == "456"

    def test_uses_cache_after_6h_with_same_etag(self, response):
        rootfs = get_rootfs(Device.select("qemu-x86_64"))
        rewind_timestamp(rootfs, seven_hours)
        response.iter_content.assert_called()

        response.reset_mock()
        get_rootfs(Device.select("qemu-x86_64"))
        response.iter_content.assert_not_called()

    def test_uses_cached_version_when_download_fails(self, get, response):
        get.side_effect = [response, RuntimeError("BOOM")]
        r1 = get_rootfs(Device.select("qemu-x86_64"))
        rewind_timestamp(r1, seven_hours)
        r2 = get_rootfs(Device.select("qemu-x86_64"))
        assert r1 == r2

    def test_pass_without_cache_when_download_fails(self, get, response):
        get.side_effect = RuntimeError("BOOM")
        assert (
            get_rootfs(Device.select("qemu-x86_64"))
            == "https://storage.tuxboot.com/buildroot/x86_64/rootfs.ext4.zst"
        )


if __name__ == "__main__":
    rootfs = get_rootfs(Device.select("qemu-x86_64"))
    print(rootfs)
