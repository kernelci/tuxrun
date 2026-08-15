import os
import shlex
from argparse import ArgumentTypeError
from pathlib import Path

import pytest

from tuxrun.utils import (
    NoProgressIndicator,
    ProgressIndicator,
    TTYProgressIndicator,
    mask_secrets,
    notify,
    notnone,
    pathurlnone,
    mask_secrets_reproducer,
    save_reproducer,
)
from tuxrun.yaml import yaml_load


def test_progress_class(mocker):
    mocker.patch("sys.stderr.isatty", return_value=True)
    assert isinstance(ProgressIndicator.get("test"), TTYProgressIndicator)

    mocker.patch("sys.stderr.isatty", return_value=False)
    assert isinstance(ProgressIndicator.get("test"), NoProgressIndicator)


def test_notnone():
    assert notnone(None, "fallback") == "fallback"
    assert notnone("", "fallback") == ""
    assert notnone("hello", "fallback") == "hello"


def test_pathurlnone():
    assert pathurlnone(None) is None
    assert pathurlnone("https://example.com/kernel") == "https://example.com/kernel"
    assert pathurlnone(__file__) == f"file://{Path(__file__).expanduser().resolve()}"

    with pytest.raises(ArgumentTypeError) as exc:
        pathurlnone("ftp://example.com/kernel")
    assert exc.match("Invalid scheme 'ftp'")

    with pytest.raises(ArgumentTypeError) as exc:
        pathurlnone("file:///should-not-exists")
    assert exc.match("/should-not-exists no such file or directory")


def test_notify(mocker):
    mock_get = mocker.patch("requests.Session.get")
    mock_post = mocker.patch("requests.Session.post")
    notify_list = {
        "callbacks": [
            {
                "dataset": "MINIMAL",
                "header": "PRIVATE-TOKEN",
                "method": "POST",
                "token": "test",
                "url": "https://callback_url.com",
            },
            {
                "dataset": "MINIMAL",
                "header": "PRIVATE-TOKEN",
                "method": "GET",
                "token": "test",
                "url": "https://callback_url.com",
            },
            {
                "dataset": "MINIMAL",
                "header": "PRIVATE-TOKEN",
                "method": "POST",
                "token": "",
                "url": "https://callback_url.com",
            },
            {},
        ]
    }
    notify(notify_list)
    assert mock_get.call_count == 1
    assert mock_post.call_count == 1


def test_mask_secrets():
    jobdef = """
device_type: "avh"
secrets:
  avh_api_token: avhapitoken
  another_secret: anothersecret
"""

    masked_jobdef = mask_secrets(jobdef)
    assert "avhapitoken" not in masked_jobdef
    assert "anothersecret" not in masked_jobdef

    jobdef = yaml_load(masked_jobdef)
    assert jobdef["secrets"]["avh_api_token"] == "XXXXXXXX"
    assert jobdef["secrets"]["another_secret"] == "XXXXXXXX"


def test_save_reproducer(tmp_path):
    argv = [
        "/usr/bin/tuxrun",
        "--device",
        "qemu-arm64",
        "--log-file",
        "-",
        "--parameters",
        "KEY=a b c",
    ]
    save_reproducer(tmp_path, argv)

    script = tmp_path / "reproducer.sh"
    text = script.read_text()
    assert text.startswith("#!/bin/sh\n")
    assert os.access(script, os.X_OK)

    command = text.split("\nexec ", 1)[1].replace("\\\n", "")
    assert shlex.split(command) == ["tuxrun"] + argv[1:]
    assert "--log-file -" in text
    assert script.stat().st_mode & 0o777 == 0o700


def test_mask_secrets_reproducer():
    # only the values of --secrets, and both spellings of it
    assert mask_secrets_reproducer(["--secrets", "a=1", "b=2"]) == [
        "--secrets",
        "a=XXXXXXXX",
        "b=XXXXXXXX",
    ]
    assert mask_secrets_reproducer(["--secrets=a=1"]) == ["--secrets=a=XXXXXXXX"]

    # an argument that only looks like the value is kept
    assert mask_secrets_reproducer(
        ["--device", "qemu-arm64", "--secrets", "a=arm64"]
    ) == ["--device", "qemu-arm64", "--secrets", "a=XXXXXXXX"]

    # nothing to mask
    assert mask_secrets_reproducer(["--device", "qemu-arm64", "--log-file", "-"]) == [
        "--device",
        "qemu-arm64",
        "--log-file",
        "-",
    ]


def test_mask_secrets_keeps_a_foreign_token():
    # The definition can come from --job-definition, then tuxrun never saw
    # the values. mask_secrets() finds them by structure.
    jobdef = """
actions:
- deploy:
    images:
      kernel:
        url: "https://example.com/Image"
        headers:
          Authorization: "Bearer foreigntoken"
"""
    assert "foreigntoken" not in mask_secrets(jobdef)


@pytest.mark.parametrize(
    "argv_secrets",
    [
        ["--secrets", "avh_api_token=s3cr3t"],
        ["--secrets=avh_api_token=s3cr3t"],
    ],
)
def test_save_reproducer_masks_secrets(tmp_path, argv_secrets):
    argv = ["/usr/bin/tuxrun", "--device", "avh-imx93"] + argv_secrets
    save_reproducer(tmp_path, argv)

    text = (tmp_path / "reproducer.sh").read_text()
    assert "s3cr3t" not in text
    assert "avh_api_token=XXXXXXXX" in text
    assert "Secrets are masked" in text


def test_save_reproducer_masks_secret_with_a_quote(tmp_path):
    token = "s3c'ret"
    argv = ["/usr/bin/tuxrun", "--secrets", f"avh_api_token={token}"]
    save_reproducer(tmp_path, argv)

    text = (tmp_path / "reproducer.sh").read_text()
    assert token not in text
    assert "s3c" not in text


def test_save_reproducer_masks_only_secrets(tmp_path):
    argv = [
        "/usr/bin/tuxrun",
        "--secrets",
        "avh_api_token=s3cr3t",
        "--parameters",
        "KEY=value",
    ]
    save_reproducer(tmp_path, argv)

    text = (tmp_path / "reproducer.sh").read_text()
    assert "KEY=value" in text
    assert "s3cr3t" not in text


def test_save_reproducer_stale_tmp_file(tmp_path):
    tmp = tmp_path / "reproducer.sh.tmp"
    tmp.write_text("old\n")
    tmp.chmod(0o666)

    save_reproducer(tmp_path, ["/usr/bin/tuxrun", "--device", "qemu-arm64"])

    script = tmp_path / "reproducer.sh"
    assert script.stat().st_mode & 0o777 == 0o700
    assert "old" not in script.read_text()
    assert not tmp.exists()
