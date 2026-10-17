"""Only weather, tasks and first-round bills; all writes use business services."""
from datetime import date, datetime
from typing import Annotated, Any, Literal
import re
import hashlib
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.assistant.auth import require_assistant
from app.assistant.service import import_legacy, write_once
from app.business_errors import BusinessError
from app.database import get_db
from app.crud import bill as bills, calendar as calendar
from app.models.bill import CalendarEvent, Tag, RecordType
from app.schemas.bill import BillCreate, BillUpdate, BillOut, MonthlySummaryOut
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate, CalendarEventOut
from app.routers import weather

router = APIRouter(prefix="/assistant", tags=["assistant"], dependencies=[Depends(require_assistant)])
Db = Annotated[Session, Depends(get_db)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCommand(StrictModel):
    action: Literal["add", "update", "complete", "void", "reopen"]
    id: int | None = Field(default=None, ge=1)
    expected_version: int | None = Field(default=None, ge=1)
    fields: dict[str, Any] = Field(default_factory=dict)


class BillCommand(StrictModel):
    action: Literal["update", "delete"]
    id: int = Field(ge=1)
    expected_version: int = Field(ge=1)
    fields: dict[str, Any] = Field(default_factory=dict)


class LegacyItem(StrictModel):
    id: str = Field(pattern=r"^[a-f0-9]{12}$")
    title: str = Field(min_length=1, max_length=128)
    content: str | None = Field(default=None, max_length=800)
    note: str | None = Field(default=None, max_length=400)
    ddl: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?$")
    deadline_ms: int | None = None
    status: Literal["active", "completed", "void", "expired"]
    version: int = Field(ge=1)
    created_ms: int
    updated_ms: int


class ImportCommand(StrictModel):
    apply: bool = False
    items: list[LegacyItem] = Field(max_length=10000)


def key_header(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9:_-]{16,128}", value):
        raise BusinessError("invalid_request_key", "需要有效的幂等请求键")
    return value


@router.get("/status")
def status(db: Db):
    db.execute(text("SELECT 1"))
    db.execute(text("SELECT id,event_date,note,version FROM calendar_events LIMIT 0"))
    db.execute(text("SELECT request_key FROM assistant_requests LIMIT 0"))
    db.execute(text("SELECT version FROM bills LIMIT 0"))
    db.execute(text("SELECT source_id FROM assistant_task_origins LIMIT 0"))
    return {"ok": True, "contract": 1, "domains": ["weather", "tasks", "bills"], "billWrites": ["create", "update", "delete"]}


@router.get("/tasks")
def tasks(db: Db, history: bool = False, query: str = Query(default="", max_length=200),
          skip: int = Query(default=0, ge=0), limit: int = Query(default=200, ge=1, le=200),
          snapshot: str = Query(default="", max_length=64)):
    if history:
        rows = calendar.list_calendar_events(db)
    else:
        rows, _ = calendar.pending_events(db, limit=1_000_000)
    rows = [e for e in rows if not query or query.casefold() in e.title.casefold() or str(e.id) == query]
    actual_snapshot = hashlib.sha256(",".join(f"{e.id}:{e.version}" for e in rows).encode()).hexdigest()
    if snapshot and snapshot != actual_snapshot:
        raise BusinessError("list_changed", "列表在分页期间变化，请重新查询", 409)
    return {"ok": True, "total": len(rows), "skip": skip, "snapshot": actual_snapshot, "truncated": skip + limit < len(rows),
            "items": [CalendarEventOut.model_validate(e).model_dump(mode="json") for e in rows[skip:skip + limit]]}


@router.post("/tasks")
def manage_task(data: TaskCommand, db: Db, idempotency_key: str = Header(default=""),
                x_kurumi_run_id: str = Header(default="", max_length=96)):
    key = key_header(idempotency_key)
    def work():
        if data.action == "add":
            if data.id is not None or data.expected_version is not None:
                raise BusinessError("invalid_fields", "新增不能指定已有ID或版本")
            allowed = set(CalendarEventCreate.model_fields)
            if set(data.fields) - allowed:
                raise BusinessError("invalid_fields", "新增包含未知字段")
            event = calendar.create_calendar_event(db, CalendarEventCreate.model_validate(data.fields), commit=False)
        else:
            if data.id is None or data.expected_version is None:
                raise BusinessError("version_required", "先查询真实ID和版本再维护")
            event = calendar.get_calendar_event(db, data.id)
            if event is None:
                raise BusinessError("not_found", "未找到事项", 404)
            calendar.check_calendar_version(event, data.expected_version)
            if data.action == "update":
                allowed = set(CalendarEventCreate.model_fields)
                if not data.fields or set(data.fields) - allowed:
                    raise BusinessError("invalid_fields", "请仅提供要修改的业务字段")
                event = calendar.update_calendar_event(db, event, CalendarEventUpdate(**data.fields, expected_version=data.expected_version), commit=False)
            else:
                if data.fields and data.action != "reopen":
                    raise BusinessError("invalid_fields", "状态操作不接受字段修改")
                if data.action == "complete": event.completed_at = datetime.now()
                if data.action == "void": event.archived_at = datetime.now()
                if data.action == "reopen":
                    if data.fields:
                        allowed = set(CalendarEventCreate.model_fields)
                        if set(data.fields) - allowed:
                            raise BusinessError("invalid_fields", "恢复包含未知字段")
                        event = calendar.update_calendar_event(db, event, CalendarEventUpdate(**data.fields, expected_version=data.expected_version), commit=False)
                    event.completed_at = None
                    event.archived_at = None
                db.flush()
        return {"ok": True, "action": data.action, "item": CalendarEventOut.model_validate(event).model_dump(mode="json")}
    return write_once(db, key, "tasks", data.model_dump(mode="json"), work, x_kurumi_run_id)


@router.post("/tasks/import")
def import_tasks(data: ImportCommand, db: Db, idempotency_key: str = Header(default="")):
    rows = [row.model_dump(mode="json") for row in data.items]
    if len({r["id"] for r in rows}) != len(rows):
        raise BusinessError("duplicate_source", "迁移来源ID重复")
    if not data.apply:
        return import_legacy(db, rows, apply=False)
    return write_once(db, key_header(idempotency_key), "tasks-import", {"items": rows}, lambda: import_legacy(db, rows, apply=True))


@router.get("/tags")
def tags(db: Db):
    return {"ok": True, "items": [{"id": t.id, "name": t.name, "type": t.type.value, "parent_id": t.parent_id}
                                  for t in db.scalars(select(Tag).order_by(Tag.sort_order, Tag.id)).all()]}


@router.get("/bills")
def list_bills(db: Db, record_type: RecordType | None = None, category_id: int | None = None,
               date_from: date | None = None, date_to: date | None = None,
               query: str = Query(default="", max_length=200), id: int | None = Query(default=None, ge=1),
               skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    if date_from and date_to and date_from > date_to:
        raise BusinessError("invalid_date_range", "起始日期不能晚于结束日期")
    total, rows = bills.list_bills(db, record_type=record_type, category_id=category_id,
                                 date_from=date_from, date_to=date_to, query=query, bill_id=id, skip=skip, limit=limit)
    return {"ok": True, "total": total, "skip": skip, "truncated": skip + len(rows) < total,
            "items": [BillOut.model_validate(row).model_dump(mode="json") for row in rows]}


@router.get("/bills/monthly")
def monthly(db: Db, year: int = Query(ge=2000, le=2100), month: int = Query(ge=1, le=12)):
    result = bills.monthly_summary(db, year, month)
    # Keep the website's numeric response intact; assistant contract uses exact decimals.
    return {"ok": True, **result, **{key: f"{result[key]:.2f}" for key in ['income', 'expense', 'net']}}


@router.post("/bills", status_code=201)
def create_bill(data: BillCreate, db: Db, idempotency_key: str = Header(default=""),
                x_kurumi_run_id: str = Header(default="", max_length=96)):
    def work():
        row = bills.create_bill(db, data, commit=False)
        return {"ok": True, "action": "create", "item": BillOut.model_validate(row).model_dump(mode="json")}
    return write_once(db, key_header(idempotency_key), "bills", data.model_dump(mode="json"), work, x_kurumi_run_id)


@router.post("/bills/manage")
def manage_bill(data: BillCommand, db: Db, idempotency_key: str = Header(default=""),
                x_kurumi_run_id: str = Header(default="", max_length=96)):
    def work():
        row = bills.get_bill(db, data.id)
        if row is None:
            raise BusinessError("not_found", "未找到账单，请重新查询", 404)
        bills.check_bill_version(row, data.expected_version)
        before = BillOut.model_validate(row).model_dump(mode="json")
        if data.action == "delete":
            if data.fields:
                raise BusinessError("invalid_fields", "删除不接受字段修改")
            bills.delete_bill(db, row, expected_version=data.expected_version, commit=False)
            return {"ok": True, "action": "delete", "item": {"id": data.id, "version": before["version"], "deleted": True}, "before": before}
        if not data.fields or set(data.fields) - set(BillCreate.model_fields):
            raise BusinessError("invalid_fields", "只提供要修改的账单字段")
        row = bills.update_bill(db, row, BillUpdate(**data.fields, expected_version=data.expected_version), commit=False)
        return {"ok": True, "action": "update", "item": BillOut.model_validate(row).model_dump(mode="json"), "before": before}
    return write_once(db, key_header(idempotency_key), "bills-manage", data.model_dump(mode="json"), work, x_kurumi_run_id)


@router.get("/weather/{component}")
def weather_component(component: Literal["current", "daily", "hourly", "alerts", "lookup"],
                      latitude: float | None = Query(default=None, ge=-90, le=90),
                      longitude: float | None = Query(default=None, ge=-180, le=180),
                      location: str = Query(default="", max_length=80), adm: str = Query(default="", max_length=80)):
    # A closed operation table, never an arbitrary upstream path or URL.
    if component == "lookup":
        if not location.strip():
            raise BusinessError("invalid_location", "请提供要查询的地点")
        query = {"location": location, "range": "cn", "number": "5", "lang": "zh"}
        if adm: query["adm"] = adm
        path = "/geo/v2/city/lookup?" + urlencode(query)
    else:
        if latitude is None or longitude is None:
            raise BusinessError("coordinates_required", "天气查询需要真实经纬度")
        precision = 2 if component == "alerts" else 4
        coords = f"{latitude:.{precision}f}/{longitude:.{precision}f}"
        prefix = "/weatheralert/v1/current" if component == "alerts" else f"/weather/v1/{component}"
        query = {"localTime": "true", "lang": "zh"}
        if component == "daily": query["days"] = "3"
        if component == "hourly": query["hours"] = "24"
        path = prefix + "/" + coords + "?" + urlencode(query)
    return weather._request_qweather(path)
