from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas.calendar import (
    CalendarEventArchive,
    CalendarEventComplete,
    CalendarEventCreate,
    CalendarEventOut,
    CalendarEventUpdate,
)

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


@router.patch("/{event_id}/completion", response_model=CalendarEventOut)
def set_completion(event_id: int, data: CalendarEventComplete, db: Session = Depends(get_db)):
    """勾选 / 取消勾选完成状态。

    刻意与通用 `PATCH /{event_id}` 分开（而不是让前端传 `completed_at`）：
    勾选是高频、意图单一的操做，若由前端算时间戳，客户端时钟与服务端不一致时
    会写进错误的时间；这里由**服务端**取 `now()`。

    取消勾选把 `completed_at` 置回 `NULL`（而不是存哨兵值），
    这样"是否完成"永远只需判断 `IS NULL`。
    """
    event = crud.get_calendar_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    event.completed_at = datetime.now() if data.done else None
    db.commit()
    db.refresh(event)
    return event


@router.patch("/{event_id}/archive", response_model=CalendarEventOut)
def set_archived(event_id: int, data: CalendarEventArchive, db: Session = Depends(get_db)):
    """作废 / 恢复一条事项（废纸篓语义）。

    与 `completion` 同样的理由：只接受布尔意图，**时间戳由服务端填**。

    与"完成"的区别（这是本功能的核心语义）：
      - 完成 = 做到了；作废 = **我决定不做了**（主动放弃提醒）。
      - 两者互不影响：一条已完成的事项也可以被作废，反之亦然。
      - 作废后不再出现在「待做事项」清单里，但**日历仍照常显示它**
        （它确实占用过那天，抹掉会让日历与实际不符）。

    时间戳由服务端填的另一个好处：前端可以据此做「撤销」，只需把 `archived`
    再传一次 `false`，不必自己记原值。
    """
    event = crud.get_calendar_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    event.archived_at = datetime.now() if data.archived else None
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
def delete(event_id: int, db: Session = Depends(get_db)):
    event = crud.get_calendar_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    crud.delete_calendar_event(db, event)
