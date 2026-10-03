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

    # PATCH keeps omitted/None fields optional while validating supplied amounts.

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("amount must be positive")
        return v

    @field_validator("reimbursement_amount")
    @classmethod
    def reimburse_not_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("reimbursement_amount cannot be negative")
        return v


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


class MonthlySummaryOut(BaseModel):
    """`GET /api/bills/summary/monthly` 的返回契约。

    三个金额字段**显式声明为 `float`**，原因有二：

    1. 该路由此前没有 `response_model`，走的是 FastAPI 的 `jsonable_encoder`。它对
       `Decimal` 的处理是"整数值返回 int、带小数返回 float"，于是同一个字段的类型会在
       `0` 与 `644.71` 之间摇摆（实测 2026-06：`income` 是 int 0、`expense` 是 float
       644.71）。声明成 float 后类型恒定。
    2. **不要**把它们声明成 `Decimal`：Pydantic v2 在 JSON 模式下会把 Decimal 序列化成
       **字符串**（如 `"644.71"`），前端的金额格式化与加减会因此出错。
    """

    year: int
    month: int
    income: float
    expense: float
    net: float
