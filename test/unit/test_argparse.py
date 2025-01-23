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
