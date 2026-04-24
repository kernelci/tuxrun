import pytest

from tuxrun.argparse import filter_artefacts, setup_parser


def test_timeouts_parser():
    assert setup_parser().parse_args(["--timeouts", "boot=1"]).timeouts == {"boot": 1}
    assert setup_parser().parse_args(
        ["--timeouts", "boot=1", "deploy=42"]
    ).timeouts == {"boot": 1, "deploy": 42}

    with pytest.raises(SystemExit):
        setup_parser().parse_args(["--timeouts", "boot=a"])

    with pytest.raises(SystemExit):
        setup_parser().parse_args(["--timeouts", "booting=1"])


def test_uboot_argument():
    options = setup_parser().parse_args(
        ["--device", "qemu-arm64", "--uboot", "https://example.com/u-boot.bin"]
    )
    assert options.uboot == "https://example.com/u-boot.bin"
    assert filter_artefacts(options)["uboot"] == "https://example.com/u-boot.bin"
