from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.bill import CalendarEventTone


class CalendarEventBase(BaseModel):
    event_date: Optional[date] = None
    event_time: Optional[time] = None
    title: str = Field(min_length=1, max_length=128)
    detail: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=4000)
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
    @model_validator(mode="after")
    def time_needs_date(self):
        if self.event_time is not None and self.event_date is None:
            raise ValueError("有时刻必须同时提供日期")
        return self


class CalendarEventUpdate(BaseModel):
    event_date: Optional[date] = None
    event_time: Optional[time] = None
    title: Optional[str] = None
    detail: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=4000)
    expected_version: Optional[int] = Field(default=None, ge=1)
    tone: Optional[CalendarEventTone] = None
    # 完成时间戳。前端勾选/取消勾选走这个字段：
    #   勾选   -> 传具体时间（通常由后端填 now()，见 router）
    #   取消   -> 传 null
    # 因为 `exclude_unset=True` 会被 crud 使用，所以"传 null"与"不传"能区分开：
    # 不传 = 不动该字段；传 null = 清空（撤销完成）。
    completed_at: Optional[datetime] = None

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
    version: int
    completed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CalendarEventComplete(BaseModel):
    """勾选/取消勾选完成状态的专用请求体。

    刻意独立于 `CalendarEventUpdate`：勾选是个高频、单一的意图，
    让前端自己算时间戳会造成客户端时钟与服务端不一致。
    传 `done=true` 时由**服务端**填 `completed_at`。
    """

    done: bool
    expected_version: Optional[int] = Field(default=None, ge=1)


class CalendarEventArchive(BaseModel):
    """作废/恢复的专用请求体（2026-10-07 新增）。

    与 `CalendarEventComplete` 同样的设计：只传意图（要不要作废），
    时间戳由**服务端**填，避免客户端时钟偏差。

    语义：`archived=true` = 我决定不做了（可恢复）；`false` = 恢复。
    这与"完成"是两件事——作废 ≠ 做到了。
    """

    archived: bool
    expected_version: Optional[int] = Field(default=None, ge=1)
