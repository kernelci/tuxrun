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
