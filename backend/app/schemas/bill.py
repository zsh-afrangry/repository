from __future__ import annotations

from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.bill import ReimbursementStatus, RecordType
from app.schemas.tag import TagOut


class BillBase(BaseModel):
    record_type: RecordType = RecordType.expense

    expense_date: date
    expense_time: Optional[time] = None

    amount: Decimal

    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    payment_platform_id: Optional[int] = None
    payment_channel_id: Optional[int] = None
    fund_type_id: Optional[int] = None

    reimbursement_status: ReimbursementStatus = ReimbursementStatus.na
    reimbursement_amount: Optional[Decimal] = None

    transaction_id: Optional[str] = None
    note: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v

    @field_validator("reimbursement_amount")
    @classmethod
    def reimburse_not_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("reimbursement_amount cannot be negative")
        return v


class BillCreate(BillBase):
    pass


class BillUpdate(BaseModel):
    """All fields optional for PATCH."""
    record_type: Optional[RecordType] = None
    expense_date: Optional[date] = None
    expense_time: Optional[time] = None
    amount: Optional[Decimal] = None
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    payment_platform_id: Optional[int] = None
    payment_channel_id: Optional[int] = None
    fund_type_id: Optional[int] = None
    reimbursement_status: Optional[ReimbursementStatus] = None
    reimbursement_amount: Optional[Decimal] = None
    transaction_id: Optional[str] = None
    note: Optional[str] = None


class BillOut(BillBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    # resolved tag objects for the frontend
    category: Optional[TagOut] = None
    subcategory: Optional[TagOut] = None
    payment_platform: Optional[TagOut] = None
    payment_channel: Optional[TagOut] = None
    fund_type: Optional[TagOut] = None


class BillListResponse(BaseModel):
    total: int
    items: list[BillOut]
