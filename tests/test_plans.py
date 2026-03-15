import datetime
from datetime import timezone

import pytest

from models.database import RequestLog, Site
from services.plans import get_plan_config, get_usage_count
from tests.conftest import TestSession


def test_get_plan_config_free():
    cfg = get_plan_config("free")
    assert cfg["limit"] == 20
    assert cfg["resets_monthly"] is False
    assert cfg["unlimited"] is False
    assert cfg["chunk_limit"] == 250


def test_get_plan_config_pro():
    cfg = get_plan_config("pro")
    assert cfg["limit"] == 2000
    assert cfg["resets_monthly"] is True
    assert cfg["unlimited"] is False


def test_get_plan_config_enterprise():
    cfg = get_plan_config("enterprise")
    assert cfg["limit"] is None
    assert cfg["unlimited"] is True


def test_get_plan_config_invalid():
    with pytest.raises(ValueError):
        get_plan_config("nonexistent")


def test_usage_count_free_zero():
    session = TestSession()
    site = Site(name="t", api_key_prefix="aaaaaaaa", api_key_hash="hash1", plan="free", message_limit=20)
    session.add(site)
    session.commit()
    session.refresh(site)
    used, was_reset = get_usage_count(site, session)
    session.close()
    assert used == 0
    assert was_reset is False


def test_usage_count_free_with_logs():
    session = TestSession()
    site = Site(name="t", api_key_prefix="bbbbbbbb", api_key_hash="hash2", plan="free", message_limit=20)
    session.add(site)
    session.commit()
    session.refresh(site)
    for _ in range(5):
        session.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
    session.commit()
    used, was_reset = get_usage_count(site, session)
    session.close()
    assert used == 5
    assert was_reset is False


def test_usage_count_enterprise():
    session = TestSession()
    site = Site(name="t", api_key_prefix="cccccccc", api_key_hash="hash3", plan="enterprise", message_limit=None)
    session.add(site)
    session.commit()
    session.refresh(site)
    for _ in range(10):
        session.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
    session.commit()
    used, was_reset = get_usage_count(site, session)
    session.close()
    assert used == 0
    assert was_reset is False


def test_usage_count_pro_within_period():
    session = TestSession()
    now = datetime.datetime.now(timezone.utc)
    site = Site(
        name="t", api_key_prefix="dddddddd", api_key_hash="hash4",
        plan="pro", message_limit=2000, period_start=now,
    )
    session.add(site)
    session.commit()
    session.refresh(site)
    for _ in range(7):
        session.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200, created_at=now))
    session.commit()
    used, was_reset = get_usage_count(site, session)
    session.close()
    assert used == 7
    assert was_reset is False


def test_usage_count_pro_expired_resets():
    session = TestSession()
    old_date = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=31)
    site = Site(
        name="t", api_key_prefix="eeeeeeee", api_key_hash="hash5",
        plan="pro", message_limit=2000, period_start=old_date,
    )
    session.add(site)
    session.commit()
    session.refresh(site)
    for _ in range(3):
        session.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200, created_at=old_date))
    session.commit()
    used, was_reset = get_usage_count(site, session)
    session.close()
    assert was_reset is True
    assert used == 0
