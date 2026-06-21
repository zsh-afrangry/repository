from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bill import RecordType
from app.schemas.bill import BillCreate, BillUpdate, BillOut, BillListResponse
from app import crud

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post("/", response_model=BillOut, status_code=201)
def create(data: BillCreate, db: Session = Depends(get_db)):
    return crud.create_bill(db, data)


@router.get("/", response_model=BillListResponse)
def list_bills(
    record_type: Optional[RecordType] = None,
    category_id: Optional[int] = None,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total, items = crud.list_bills(
        db,
        record_type=record_type,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return {"total": total, "items": items}


@router.get("/summary/monthly")
def monthly_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    return crud.monthly_summary(db, year, month)


@router.get("/{bill_id}", response_model=BillOut)
def get(bill_id: int, db: Session = Depends(get_db)):
    bill = crud.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill


@router.patch("/{bill_id}", response_model=BillOut)
def update(bill_id: int, data: BillUpdate, db: Session = Depends(get_db)):
    bill = crud.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return crud.update_bill(db, bill, data)


@router.delete("/{bill_id}", status_code=204)
def delete(bill_id: int, db: Session = Depends(get_db)):
    bill = crud.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    crud.delete_bill(db, bill)
