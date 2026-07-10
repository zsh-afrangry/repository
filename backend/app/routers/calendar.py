from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas.calendar import CalendarEventCreate, CalendarEventOut, CalendarEventUpdate

router = APIRouter(prefix="/calendar-events", tags=["calendar-events"])


@router.post("/", response_model=CalendarEventOut, status_code=201)
def create(data: CalendarEventCreate, db: Session = Depends(get_db)):
    return crud.create_calendar_event(db, data)


@router.get("/", response_model=list[CalendarEventOut])
def list_events(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    return crud.list_calendar_events(db, date_from=date_from, date_to=date_to)


@router.patch("/{event_id}", response_model=CalendarEventOut)
def update(event_id: int, data: CalendarEventUpdate, db: Session = Depends(get_db)):
    event = crud.get_calendar_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return crud.update_calendar_event(db, event, data)


@router.delete("/{event_id}", status_code=204)
def delete(event_id: int, db: Session = Depends(get_db)):
    event = crud.get_calendar_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    crud.delete_calendar_event(db, event)
