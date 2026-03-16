import bcrypt
import datetime
import pytest
from datetime import timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.database import Base, Site, RequestLog

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, expire_on_commit=False)

# All module-level SessionLocal names that need patching
_SESSION_TARGETS = [
    "models.database.SessionLocal",
    "middleware.auth.SessionLocal",
    "routers.admin.SessionLocal",
    "routers.chat.SessionLocal",
    "routers.usage.SessionLocal",
]


@pytest.fixture(autouse=True)
def reset_db(monkeypatch):
    Base.metadata.create_all(TEST_ENGINE)
    for target in _SESSION_TARGETS:
        monkeypatch.setattr(target, TestSession)
    monkeypatch.setattr("api.init_db", lambda: None)
    monkeypatch.setenv("ADMIN_SECRET", "test-secret")
    yield
    Base.metadata.drop_all(TEST_ENGINE)


@pytest.fixture
def client():
    from api import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def free_site():
    raw_key = "freesiteapikey0123456789abcdef"  # 30 chars, prefix "freesite"
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    session = TestSession()
    site = Site(
        name="free-test",
        api_key_prefix=raw_key[:8],
        api_key_hash=key_hash,
        plan="free",
        message_limit=20,
    )
    session.add(site)
    session.commit()
    session.refresh(site)
    session.close()
    return site, raw_key


@pytest.fixture
def plus_site():
    import datetime
    raw_key = "prositea0123456789abcdefghijkl"  # 30 chars, prefix "prositea"
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    session = TestSession()
    site = Site(
        name="plus-test",
        api_key_prefix=raw_key[:8],
        api_key_hash=key_hash,
        plan="plus",
        message_limit=2000,
        period_start=datetime.datetime.now(timezone.utc),
    )
    session.add(site)
    session.commit()
    session.refresh(site)
    session.close()
    return site, raw_key


@pytest.fixture
def enterprise_site():
    raw_key = "entsitea0123456789abcdefghijkl"  # 30 chars, prefix "entsitea"
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    session = TestSession()
    site = Site(
        name="enterprise-test",
        api_key_prefix=raw_key[:8],
        api_key_hash=key_hash,
        plan="enterprise",
        message_limit=None,
    )
    session.add(site)
    session.commit()
    session.refresh(site)
    session.close()
    return site, raw_key
