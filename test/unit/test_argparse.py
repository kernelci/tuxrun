import pytest

from tuxrun.argparse import setup_parser


def test_timeouts_parser():
    assert setup_parser().parse_args(["--timeouts", "boot=1"]).timeouts == {"boot": 1}
    assert setup_parser().parse_args(
        ["--timeouts", "boot=1", "deploy=42"]
    ).timeouts == {"boot": 1, "deploy": 42}

    with pytest.raises(SystemExit):
        setup_parser().parse_args(["--timeouts", "boot=a"])

    with pytest.raises(SystemExit):
        setup_parser().parse_args(["--timeouts", "booting=1"])


def test_downloads_rejects_the_same_name_twice(capsys):
    with pytest.raises(SystemExit):
        setup_parser().parse_args(
            [
                "--device",
                "usbg-bcm2711-rpi-4-b",
                "--downloads",
                "https://e.com/download?id=A",
                "--downloads",
                "https://e.com/download?id=B",
            ]
        )
    assert "downloaded twice" in capsys.readouterr().err


def test_test_yaml_takes_a_local_file(tmp_path):
    paste = tmp_path / "oeqa.yaml"
    paste.write_text("- test:\n", encoding="utf-8")
    options = setup_parser().parse_args(
        ["--device", "qemu-arm64", "--test-yaml", str(paste)]
    )
    assert options.test_yaml == [f"file://{paste}"]


def test_test_yaml_can_be_given_several_times(tmp_path):
    first = tmp_path / "one.yaml"
    second = tmp_path / "two.yaml"
    for path in (first, second):
        path.write_text("- test:\n", encoding="utf-8")
    options = setup_parser().parse_args(
        [
            "--device",
            "qemu-arm64",
            "--test-yaml",
            str(first),
            "--test-yaml",
            str(second),
        ]
    )
    assert options.test_yaml == [f"file://{first}", f"file://{second}"]


def test_test_yaml_with_a_missing_file_is_an_error(capsys):
    with pytest.raises(SystemExit):
        setup_parser().parse_args(
            ["--device", "qemu-arm64", "--test-yaml", "/nope/oeqa.yaml"]
        )
    assert "no such file or directory" in capsys.readouterr().err
