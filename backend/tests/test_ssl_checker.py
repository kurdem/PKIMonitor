import pytest

from app.services.ssl_checker import parse_target
from app.utils import cert_status


@pytest.mark.parametrize(
    "value,expected",
    [
        ("https://example.com", ("example.com", 443)),
        ("example.com", ("example.com", 443)),
        ("example.com:8443", ("example.com", 8443)),
        ("https://example.com:9443/path", ("example.com", 9443)),
        ("ldaps://dc.corp.local:636", ("dc.corp.local", 636)),
    ],
)
def test_parse_target(value, expected):
    assert parse_target(value) == expected


def test_parse_target_invalid():
    with pytest.raises(ValueError):
        parse_target("")


@pytest.mark.parametrize(
    "days,expected",
    [
        (-1, "expired"),
        (10, "critical"),
        (29, "critical"),
        (30, "warning"),
        (59, "warning"),
        (60, "ok"),
        (365, "ok"),
        (None, "unknown"),
    ],
)
def test_cert_status(days, expected):
    assert cert_status(days) == expected
