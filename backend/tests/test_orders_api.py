from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import HangRail, Store, WorkOrder

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    store = Store(name="测试门店")
    db.add(store)
    db.flush()
    db.add(HangRail(store_id=store.id, label="A 杆", length_cm=200))
    db.commit()
    db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def future_due(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def create_payload(**over):
    payload = {
        "ticket_code": "HR-9001",
        "garment_name": "羊毛大衣",
        "length_cm": 45,
        "due_at": future_due(),
    }
    payload.update(over)
    return payload


def test_create_order_success_is_ready(client):
    r = client.post("/api/orders", json=create_payload())
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["ticket_code"] == "HR-9001"
    assert o["status"] == "ready"
    assert o["hung_at"] is None

    # 列表立即出现
    rows = client.get("/api/orders").json()
    assert any(x["ticket_code"] == "HR-9001" and x["status"] == "ready" for x in rows)


def test_create_duplicate_ticket_conflict(client):
    assert client.post("/api/orders", json=create_payload()).status_code == 201
    r = client.post("/api/orders", json=create_payload(garment_name="另一件"))
    assert r.status_code == 409
    assert "票号" in r.json()["detail"]


def test_duplicate_against_existing_row(client):
    db = TestingSessionLocal()
    db.add(
        WorkOrder(
            store_id=1,
            ticket_code="HR-7777",
            garment_name="存量单",
            length_cm=40,
            status="ready",
            due_at=datetime.utcnow() + timedelta(days=1),
        )
    )
    db.commit()
    db.close()
    r = client.post("/api/orders", json=create_payload(ticket_code="HR-7777"))
    assert r.status_code == 409


def test_length_must_be_positive(client):
    r = client.post("/api/orders", json=create_payload(length_cm=0))
    assert r.status_code == 422
    r = client.post("/api/orders", json=create_payload(length_cm=-10))
    assert r.status_code == 422


def test_due_in_the_past_rejected(client):
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    r = client.post("/api/orders", json=create_payload(due_at=past))
    assert r.status_code == 400
    assert "到期" in r.json()["detail"]


def test_created_ready_order_can_hang(client):
    r = client.post("/api/orders", json=create_payload())
    order_id = r.json()["id"]
    hung = client.post("/api/hang", json={"order_id": order_id})
    assert hung.status_code == 200, hung.text
    assert hung.json()["status"] == "hung"
    assert hung.json()["hung_at"] is not None


def test_create_cannot_bypass_hang_as_hung(client):
    # 入参即便携带 status 也不能把工单直接建成 hung
    r = client.post("/api/orders", json=create_payload(status="hung"))
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "ready"

    order_id = r.json()["id"]
    # 未上杆前不能取件
    pickup = client.post("/api/pickup", json={"ticket_code": "HR-9001"})
    assert pickup.status_code == 400
    # 且挂杆上没有该工单的占位
    occ = client.get("/api/occupancy/1").json()
    assert all(s["order_id"] != order_id for s in occ["segments"])
