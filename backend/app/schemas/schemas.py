from datetime import datetime, timezone
from pydantic import BaseModel, field_validator


class StoreOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class RailOut(BaseModel):
    id: int
    store_id: int
    label: str
    length_cm: float
    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    store_id: int
    ticket_code: str
    garment_name: str
    length_cm: float
    status: str
    due_at: datetime
    hung_at: datetime | None
    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    store_id: int
    ticket_code: str
    garment_name: str
    length_cm: float
    due_at: datetime

    @field_validator("ticket_code", "garment_name")
    @classmethod
    def _strip_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("不能为空")
        return v

    @field_validator("length_cm")
    @classmethod
    def _positive_length(cls, v: float) -> float:
        if not (v > 0):  # NaN 也一并拒绝
            raise ValueError("衣长须为正数")
        return v

    @field_validator("due_at")
    @classmethod
    def _due_not_in_past(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v < now:
            raise ValueError("到期时间不得早于创建时刻")
        # 落库为 naive UTC，与 utcnow() 体系一致
        return v.astimezone(timezone.utc).replace(tzinfo=None)


class HangRequest(BaseModel):
    order_id: int
    rail_id: int | None = None


class PickupRequest(BaseModel):
    ticket_code: str


class OccupancySeg(BaseModel):
    order_id: int
    ticket_code: str
    garment_name: str
    start_cm: float
    end_cm: float


class OccupancyOut(BaseModel):
    rail_id: int
    label: str
    length_cm: float
    segments: list[OccupancySeg]
