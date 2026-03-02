import os
import datetime
from datetime import timezone
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./sites.db")
engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Site(Base):
    __tablename__ = "sites"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key_prefix = Column(String(8), nullable=True)
    api_key_hash = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    plan = Column(String, default="free")
    message_limit = Column(Integer, default=100)
    period_start = Column(DateTime, nullable=True, default=None)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))


class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, nullable=False)
    endpoint = Column(String)
    status_code = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(engine)
