from datetime import datetime

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    item: str
    qty: int

class OrderOut(OrderCreate):
    id: int = Field(..., description="The unique identifier of the order")
    status: str = Field(..., description="The current status of the order")
    created_at: datetime

    class Config:
        from_attributes = True