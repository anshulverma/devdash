"""M0 smoke test — package imports and exposes its contract version."""

import devdash


def test_version_is_a_string() -> None:
    assert isinstance(devdash.__version__, str)


def test_contract_version_is_int() -> None:
    assert isinstance(devdash.CONTRACT_VERSION, int)
    assert devdash.CONTRACT_VERSION >= 1
