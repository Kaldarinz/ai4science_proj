"""Readiness CLI regression tests without reading project inputs."""

import pytest

from checks import check


@pytest.mark.parametrize(
    "args",
    [
        ["--gold"],
        ["--article", "1", "--gold"],
        ["--analysis", "draft", "--gold"],
    ],
)
def test_removed_scoring_option_is_rejected(args, monkeypatch, capsys):
    monkeypatch.setattr(check.sys, "argv", ["check.py", *args])

    def forbidden(*args):
        pytest.fail("argument parsing must fail before reading project inputs")

    monkeypatch.setattr(check, "check_vocabulary", forbidden)
    monkeypatch.setattr(check, "check_data", forbidden)
    with pytest.raises(SystemExit) as error:
        check.main()
    assert error.value.code == 2
    assert "unrecognized arguments: --gold" in capsys.readouterr().err


def test_help_lists_only_supported_check_modes(monkeypatch, capsys):
    monkeypatch.setattr(check.sys, "argv", ["check.py", "--help"])
    with pytest.raises(SystemExit) as error:
        check.main()
    assert error.value.code == 0
    help_text = capsys.readouterr().out
    assert "--article" in help_text
    assert "--analysis {draft,final}" in help_text
    assert "--gold" not in help_text
