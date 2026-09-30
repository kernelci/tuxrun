import lzma
import os
import subprocess
import time
from hashlib import sha1
from pathlib import Path

import pytest
import requests

from tuxrun.assets import __download__, get_rootfs, get_vmlinux
from tuxrun.exceptions import InvalidArgument
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

    def test_rootfs_without_etag_is_not_cached(self, response):
        response.headers = {}
        url = "https://example.com/rootfs.img"
        assert get_rootfs(Device.select("qemu-arm64"), url) == url

    @pytest.mark.parametrize("error", [requests.ConnectionError, KeyboardInterrupt])
    def test_broken_download_is_not_cached(self, response, home, error):
        response.iter_content.side_effect = error
        with pytest.raises(error):
            get_rootfs(Device.select("qemu-arm64"), "https://example.com/rootfs.img")
        assert not list((home / ".cache" / "tuxrun" / "assets").iterdir())

    def test_cached_file_follows_the_umask(self, response):
        response.iter_content.return_value = [b"data"]
        old = os.umask(0o022)
        try:
            rootfs = get_rootfs(Device.select("qemu-arm64"), "https://e.com/r.img")
        finally:
            os.umask(old)
        assert Path(rootfs).stat().st_mode & 0o777 == 0o644

    def test_pass_without_cache_when_download_fails(self, get, response):
        get.side_effect = RuntimeError("BOOM")
        assert (
            get_rootfs(Device.select("qemu-x86_64"))
            == "https://storage.tuxboot.com/buildroot/x86_64/rootfs.ext4.zst"
        )


class TestDownload:
    url = "https://example.com/vmlinux"

    def test_caches_without_etag(self, response):
        response.headers = {}
        response.iter_content.return_value = [b"data"]
        path = __download__(self.url)
        assert path.read_bytes() == b"data"
        assert not path.with_name(path.name + ".etag").exists()

    def test_raises_when_the_request_fails(self, get):
        get.side_effect = requests.ConnectionError("boom")
        with pytest.raises(requests.ConnectionError):
            __download__(self.url)

    def test_uses_the_cache_when_the_request_fails(self, get, response):
        response.iter_content.return_value = [b"data"]
        get.side_effect = [response, requests.ConnectionError("boom")]
        path = __download__(self.url)
        rewind_timestamp(path, seven_hours)
        assert __download__(self.url) == path


class TestGetVmlinux:
    @pytest.mark.parametrize("name", ["vmlinux", "vmlinux.xz"])
    def test_local(self, tmp_path, name):
        vmlinux = tmp_path / name
        vmlinux.write_bytes(lzma.compress(b"elf") if name.endswith(".xz") else b"elf")
        assert get_vmlinux(str(vmlinux)).read_bytes() == b"elf"

    @pytest.mark.parametrize(
        "name,headers",
        [
            ("vmlinux", None),
            ("vmlinux.xz", None),
            ("vmlinux", {}),
            ("vmlinux.xz?token=abc", None),
        ],
    )
    def test_url(self, response, name, headers):
        if headers is not None:
            response.headers = headers
        data = lzma.compress(b"elf") if ".xz" in name else b"elf"
        response.iter_content.return_value = [data]
        vmlinux = get_vmlinux(f"https://example.com/{name}")
        assert vmlinux.read_bytes() == b"elf"

    def test_xz_does_not_replace_the_plain_download(self, response):
        response.iter_content.return_value = [b"plain"]
        plain = get_vmlinux("https://example.com/vmlinux")
        response.iter_content.return_value = [lzma.compress(b"unxz")]
        unxz = get_vmlinux("https://example.com/vmlinux.xz")
        assert (plain.read_bytes(), unxz.read_bytes()) == (b"plain", b"unxz")

    def test_truncated_xz(self, tmp_path, home):
        vmlinux = tmp_path / "vmlinux.xz"
        vmlinux.write_bytes(lzma.compress(b"elf" * 1000)[:-10])
        with pytest.raises(InvalidArgument, match="vmlinux.xz"):
            get_vmlinux(str(vmlinux))
        assert not list(home.rglob("*.tmp"))

    def test_download_breaks(self, response):
        response.iter_content.side_effect = requests.ConnectionError("reset")
        with pytest.raises(InvalidArgument, match="unable to download: reset"):
            get_vmlinux("https://example.com/vmlinux")

    def test_local_xz_with_an_older_mtime(self, tmp_path):
        vmlinux = tmp_path / "vmlinux.xz"
        vmlinux.write_bytes(lzma.compress(b"old"))
        assert get_vmlinux(str(vmlinux)).read_bytes() == b"old"
        vmlinux.write_bytes(lzma.compress(b"new"))
        os.utime(vmlinux, (0, 0))
        assert get_vmlinux(str(vmlinux)).read_bytes() == b"new"

    def test_not_a_file(self, tmp_path):
        with pytest.raises(InvalidArgument, match="not a file"):
            get_vmlinux(str(tmp_path))

    def test_download_fails(self, get):
        get.side_effect = requests.ConnectionError("boom")
        with pytest.raises(InvalidArgument, match="unable to download"):
            get_vmlinux("https://example.com/vmlinux")


if __name__ == "__main__":
    rootfs = get_rootfs(Device.select("qemu-x86_64"))
    print(rootfs)
