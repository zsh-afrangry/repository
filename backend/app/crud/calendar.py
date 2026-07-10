from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bill import CalendarEvent
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate


def create_calendar_event(db: Session, data: CalendarEventCreate) -> CalendarEvent:
    event = CalendarEvent(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_calendar_event(db: Session, event_id: int) -> CalendarEvent | None:
    return db.get(CalendarEvent, event_id)


def list_calendar_events(
    db: Session,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[CalendarEvent]:
    query = select(CalendarEvent)
    if date_from is not None:
        query = query.where(CalendarEvent.event_date >= date_from)
    if date_to is not None:
        query = query.where(CalendarEvent.event_date <= date_to)

    return list(
        db.scalars(
            query.order_by(
                CalendarEvent.event_date.asc(),
                CalendarEvent.event_time.asc(),
                CalendarEvent.id.asc(),
            )
        ).all()
    )


def update_calendar_event(
    db: Session,
    event: CalendarEvent,
    data: CalendarEventUpdate,
) -> CalendarEvent:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


def delete_calendar_event(db: Session, event: CalendarEvent) -> None:
    db.delete(event)
    db.commit()
