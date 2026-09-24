import os
from collections.abc import Iterator
from types import SimpleNamespace

# 本地无 Postgres/psycopg2 时也能跑测试：全局 engine 仅在应用启动时连接，
# 用例自身使用下方的 in-memory SQLite；docker 内由环境变量覆盖回 Postgres。
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import HangRail, Store


@pytest.fixture
def api() -> Iterator[tuple[TestClient, Store, HangRail, sessionmaker]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    db = TestSession()
    store = Store(name="测试干洗店")
    db.add(store)
    db.flush()
    rail = HangRail(store_id=store.id, label="测试杆", length_cm=200)
    db.add(rail)
    db.commit()
    store_id, rail_id = store.id, rail.id
    db.close()

    def override_get_db() -> Iterator[Session]:
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), SimpleNamespace(id=store_id), SimpleNamespace(id=rail_id), TestSession
    finally:
        app.dependency_overrides.clear()
