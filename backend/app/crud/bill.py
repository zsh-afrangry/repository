from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, selectinload

from app.models.bill import Bill, RecordType
from app.schemas.bill import BillCreate, BillUpdate


def _with_tags(q):
    return q.options(
        selectinload(Bill.category),
        selectinload(Bill.subcategory),
        selectinload(Bill.payment_platform),
        selectinload(Bill.payment_channel),
        selectinload(Bill.fund_type),
    )


def create_bill(db: Session, data: BillCreate) -> Bill:
    bill = Bill(**data.model_dump())
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return db.scalar(_with_tags(select(Bill).where(Bill.id == bill.id)))


def get_bill(db: Session, bill_id: int) -> Bill | None:
    return db.scalar(_with_tags(select(Bill).where(Bill.id == bill_id)))


def list_bills(
    db: Session,
    *,
    record_type: Optional[RecordType] = None,
    category_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[int, list[Bill]]:
    conditions = []
    if record_type:
        conditions.append(Bill.record_type == record_type)
    if category_id:
        conditions.append(Bill.category_id == category_id)
    if date_from:
        conditions.append(Bill.expense_date >= date_from)
    if date_to:
        conditions.append(Bill.expense_date <= date_to)

    where = and_(*conditions) if conditions else True

    total = db.scalar(select(func.count()).select_from(Bill).where(where)) or 0
    items = db.scalars(
        _with_tags(
            select(Bill)
            .where(where)
            .order_by(Bill.expense_date.desc(), Bill.expense_time.desc())
            .offset(skip)
            .limit(limit)
        )
    ).all()
    return total, list(items)


def update_bill(db: Session, bill: Bill, data: BillUpdate) -> Bill:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(bill, field, value)
    db.commit()
    return db.scalar(_with_tags(select(Bill).where(Bill.id == bill.id)))


def delete_bill(db: Session, bill: Bill) -> None:
    db.delete(bill)
    db.commit()


def monthly_summary(db: Session, year: int, month: int) -> dict:
    """Return total income and expense for a given month. Uses MySQL YEAR()/MONTH()."""
    rows = db.execute(
        select(Bill.record_type, func.sum(Bill.amount))
        .where(
            func.year(Bill.expense_date) == year,
            func.month(Bill.expense_date) == month,
        )
        .group_by(Bill.record_type)
    ).all()

    result = {RecordType.income: Decimal(0), RecordType.expense: Decimal(0)}
    for record_type, total in rows:
        result[record_type] = total or Decimal(0)

    return {
        "year": year,
        "month": month,
        "income": result[RecordType.income],
        "expense": result[RecordType.expense],
        "net": result[RecordType.income] - result[RecordType.expense],
    }
