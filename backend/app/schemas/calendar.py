from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.bill import CalendarEventTone


class CalendarEventBase(BaseModel):
    event_date: date
    event_time: Optional[time] = None
    title: str
    detail: Optional[str] = None
    tone: CalendarEventTone = CalendarEventTone.todo

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title cannot be empty")
        return value

    @field_validator("detail")
    @classmethod
    def detail_clean(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        return value or None


class CalendarEventCreate(CalendarEventBase):
    pass


class CalendarEventUpdate(BaseModel):
    event_date: Optional[date] = None
    event_time: Optional[time] = None
    title: Optional[str] = None
    detail: Optional[str] = None
    tone: Optional[CalendarEventTone] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("title cannot be empty")
        return value

    @field_validator("detail")
    @classmethod
    def detail_clean(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        return value or None


class CalendarEventOut(CalendarEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
