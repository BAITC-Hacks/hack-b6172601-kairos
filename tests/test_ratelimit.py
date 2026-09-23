"""Rate limiter tests. Pure logic, no clock dependency."""
import pytest

from app.core.ratelimit import RateLimited, check, reset


def setup_function():
    reset()


def test_disabled_by_default():
    for _ in range(100):
        check("1.2.3.4", limit=0, now=1000.0)


def test_allows_up_to_the_limit():
    for i in range(3):
        check("1.2.3.4", limit=3, now=1000.0 + i)


def test_blocks_past_the_limit():
    for i in range(3):
        check("1.2.3.4", limit=3, now=1000.0 + i)
    with pytest.raises(RateLimited) as excinfo:
        check("1.2.3.4", limit=3, now=1003.0)
    assert excinfo.value.status_code == 429
    assert excinfo.value.retry_after > 0


def test_window_slides():
    for i in range(3):
        check("1.2.3.4", limit=3, now=1000.0 + i)
    check("1.2.3.4", limit=3, now=1061.0)  # first hit has aged out


def test_clients_are_independent():
    for i in range(3):
        check("1.1.1.1", limit=3, now=1000.0 + i)
    check("2.2.2.2", limit=3, now=1000.0)
