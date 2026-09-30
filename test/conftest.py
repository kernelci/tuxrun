import pytest
import sys

sys.path.append("/usr/share/tuxlava")


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def response(mocker):
    return mocker.MagicMock()


@pytest.fixture(autouse=True)
def get(mocker, response):
    f = mocker.patch("requests.Session.get")
    f.return_value = response
    return f


@pytest.fixture
def elf(tmp_path):
    def __elf__(machine, bits, order):
        header = b"\x7fELF" + bytes(
            [2 if bits == 64 else 1, 2 if order == "big" else 1]
        )
        path = tmp_path / "vmlinux"
        path.write_bytes(header.ljust(18, b"\0") + machine.to_bytes(2, order))
        return path

    return __elf__
