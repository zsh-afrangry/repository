"""Transactional bridge receipts and explicit legacy import; no chat parsing."""
import hashlib
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.assistant.models import AssistantRequest, AssistantTaskOrigin
from app.business_errors import BusinessError
from app.crud.calendar import create_calendar_event
from app.models.bill import CalendarEvent
from app.schemas.calendar import CalendarEventCreate, CalendarEventOut

log = logging.getLogger("knowledgemap.assistant")


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_once(db: Session, key: str, operation: str, payload: dict, work: Callable, run_id: str = "") -> dict:
    digest = hashlib.sha256(canonical({"operation": operation, "payload": payload}).encode()).hexdigest()

    def replay():
        previous = db.get(AssistantRequest, key)
        if previous:
            if previous.payload_hash != digest:
                raise BusinessError("idempotency_conflict", "本次请求已处理其他参数，请用新消息提出下一项", 409)
            return json.loads(previous.result_json)

    previous = replay()
    if previous is not None:
        return previous
    try:
        result = work()
        db.add(AssistantRequest(request_key=key, payload_hash=digest, result_json=canonical(result)))
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = replay()
        if previous is not None:
            return previous
        raise BusinessError("record_conflict", "记录冲突，未提交本次写入，请查询后重试", 409) from None
    except StaleDataError:
        db.rollback()
        # A concurrent retry may lose the version race after the same request
        # already committed. Start a fresh transaction and return its receipt.
        previous = replay()
        if previous is not None:
            return previous
        raise BusinessError("version_conflict", "记录已被另一入口修改，请刷新后重试", 409) from None
    except Exception:
        db.rollback()
        raise
    # Receipt keys are digests of trusted transport identities, not chat bodies.
    log.info("assistant_write operation=%s request=%s run=%s item=%s", operation, key, run_id, result.get("item", {}).get("id"))
    return result


def import_legacy(db: Session, rows: list[dict], *, apply: bool) -> dict:
    planned = []
    # Snapshot pre-existing target titles, excluding previously imported rows.
    # Two distinct source rows can legitimately share a title; never merge them.
    imported_ids = select(AssistantTaskOrigin.event_id)
    existing_titles = set(db.scalars(select(CalendarEvent.title).where(CalendarEvent.id.not_in(imported_ids))).all())
    local_stamp = lambda ms: datetime.fromtimestamp(ms / 1000, ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
    for row in rows:
        source_id = "kurumi-list-v1:" + row["id"]
        prior = db.get(AssistantTaskOrigin, source_id)
        if prior:
            if prior.source_json != canonical(row):
                raise BusinessError("migration_source_changed", "来源记录变化，请先核对迁移映射", 409)
            planned.append({"sourceId": row["id"], "eventId": prior.event_id, "result": "already_imported"})
            continue
        ddl = row.get("ddl")
        fields = CalendarEventCreate(title=row["title"], detail=row.get("content"), note=row.get("note"),
                                     event_date=ddl[:10] if ddl else None, event_time=ddl[11:] if ddl and len(ddl) > 10 else None)
        if row["title"] in existing_titles:
            # Similar titles are not proof of identity. Never silently merge an existing row.
            raise BusinessError("migration_target_conflict", "网站已有同标题事项，需要人工核对后再导入", 409)
        event = None
        if apply:
            event = create_calendar_event(db, fields, commit=False)
            stamp = local_stamp(row["updated_ms"])
            if row["status"] == "completed": event.completed_at = stamp
            if row["status"] in {"void", "expired"}: event.archived_at = stamp
            event.created_at = local_stamp(row["created_ms"])
            event.updated_at = stamp
            db.flush()
            db.add(AssistantTaskOrigin(source_id=source_id, event_id=event.id, source_json=canonical(row)))
            db.flush()
        planned.append({"sourceId": row["id"], "eventId": event.id if event else None,
                        "result": "imported" if apply else "would_import", "sourceStatus": row["status"]})
    return {"ok": True, "applied": apply, "count": len(planned), "mapping": planned}
