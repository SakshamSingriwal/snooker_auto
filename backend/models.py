from pydantic import BaseModel
from typing import List, Optional

class OrderItem(BaseModel):
    product_id: int
    quantity: int

class CreateOrderRequest(BaseModel):
    table_id: int
    customer_type: str
    items: List[OrderItem]
    special_requests: Optional[str] = None

class StopSessionRequest(BaseModel):
    customer_name: str

class SettingsUpdate(BaseModel):
    cafe_name: Optional[str] = None
    currency_symbol: Optional[str] = None
    default_min_minutes: Optional[int] = None
    default_rate_per_minute: Optional[float] = None