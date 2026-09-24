from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models.models import WorkOrder


def _due(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _payload(store_id: int, **over) -> dict:
    body = {
        "store_id": store_id,
        "ticket_code": "T-0001",
        "garment_name": "羊毛大衣",
        "length_cm": 40,
        "due_at": _due(),
    }
    body.update(over)
    return body


def test_create_order_ready_then_hang(api: tuple[TestClient, object, object, sessionmaker]):
    client, store, rail, Session = api
    r = client.post("/api/orders", json=_payload(store.id))
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["status"] == "ready"
    assert order["hung_at"] is None
    assert order["ticket_code"] == "T-0001"

    # 列表立即出现，且排在最前
    rows = client.get("/api/orders").json()
    assert rows[0]["id"] == order["id"]

    # ready 工单可走现有上杆流程
    h = client.post("/api/hang", json={"order_id": order["id"]})
    assert h.status_code == 200, h.text
    hung = h.json()
    assert hung["status"] == "hung"
    assert hung["hung_at"] is not None

    # 库里确实生成了占位，而不是只改了状态
    db = Session()
    try:
        rec = db.get(WorkOrder, order["id"])
        assert rec.status == "hung"
        assert len(rec.ticket_code) > 0
    finally:
        db.close()


def test_duplicate_ticket_conflicts(api: tuple[TestClient, object, object, sessionmaker]):
    client, store, _rail, _Session = api
    r1 = client.post("/api/orders", json=_payload(store.id))
    assert r1.status_code == 201, r1.text
    r2 = client.post("/api/orders", json=_payload(store.id, garment_name="西装"))
    assert r2.status_code == 409, r2.text
    assert "票号" in r2.json()["detail"]


def test_invalid_length_rejected(api: tuple[TestClient, object, object, sessionmaker]):
    client, store, _rail, _Session = api
    for bad in (0, -10):
        r = client.post("/api/orders", json=_payload(store.id, ticket_code=f"L-{bad}", length_cm=bad))
        assert r.status_code == 422, r.text
        assert "衣长" in r.text
    # 状态保持 ready 工单数量为 0：非法数据未落库
    assert client.get("/api/orders").json() == []


def test_due_before_now_rejected(api: tuple[TestClient, object, object, sessionmaker]):
    client, store, _rail, _Session = api
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    r = client.post("/api/orders", json=_payload(store.id, due_at=past))
    assert r.status_code == 422, r.text
    assert "到期" in r.text


def test_naive_due_treated_as_utc(api: tuple[TestClient, object, object, sessionmaker]):
    client, store, _rail, _Session = api
    future_naive = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    r = client.post("/api/orders", json=_payload(store.id, due_at=future_naive))
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "ready"


def test_create_never_hung_even_if_status_forged(api: tuple[TestClient, object, object, sessionmaker]):
    client, store, _rail, _Session = api
    # 请求体里伪造 status=hung：schema 直接忽略，落库必须是 ready
    r = client.post("/api/orders", json=_payload(store.id, status="hung", hung_at=datetime.utcnow().isoformat()))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "ready"
    assert body["hung_at"] is None


def test_unknown_store_404(api: tuple[TestClient, object, object, sessionmaker]):
    client, _store, _rail, _Session = api
    r = client.post("/api/orders", json=_payload(9999))
    assert r.status_code == 404, r.text
