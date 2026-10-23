import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ChitSchemeCreate(BaseModel):
    """Payload to define a new Chit Scheme template."""
    name: str = Field(..., min_length=2, max_length=100)
    total_value: Decimal = Field(..., gt=0, decimal_places=2)
    duration_months: int = Field(..., gt=0, le=120)
    monthly_installment: Decimal = Field(..., gt=0, decimal_places=2)
    foreman_commission_pct: Decimal = Field(default=Decimal("5.00"), ge=0, le=20, decimal_places=2)
    max_bid_discount_pct: Decimal = Field(default=Decimal("30.00"), ge=0, le=50, decimal_places=2)
    min_bid_discount_pct: Decimal = Field(default=Decimal("5.00"), ge=0, le=20, decimal_places=2)
    foreman_month_one_reserved: bool = True
    is_active: bool = True


class ChitSchemeUpdate(BaseModel):
    """Payload to update scheme details."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None


class ChitSchemeResponse(BaseModel):
    """Public representation of a Chit Scheme."""
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    total_value: Decimal
    duration_months: int
    monthly_installment: Decimal
    foreman_commission_pct: Decimal
    max_bid_discount_pct: Decimal
    min_bid_discount_pct: Decimal
    foreman_month_one_reserved: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
