"""Transactional bridge receipts and explicit legacy/bill import; no chat parsing."""
import hashlib
import json
import logging
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.assistant.models import (
    AssistantBillImportBatch,
    AssistantBillOrigin,
    AssistantRequest,
    AssistantTaskOrigin,
)
from app.business_errors import BusinessError
from app.crud.bill import validate_bill_tags
from app.crud.calendar import create_calendar_event
from app.models.bill import Bill, CalendarEvent, RecordType, ReimbursementStatus, Tag, TagType
from app.schemas.calendar import CalendarEventCreate

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
    item_id = result.get("item", {}).get("id") or result.get("batch_id")
    log.info("assistant_write operation=%s request=%s run=%s item=%s", operation, key, run_id, item_id)
    return result


def read_bill_receipt(db: Session, key: str) -> dict:
    receipt = db.get(AssistantRequest, key)
    if receipt:
        result = json.loads(receipt.result_json)
        action = result.get("action")
        item = result.get("item", {})
        bill = result.get("before", {}) if action == "delete" else item
        if (result.get("ok") is True and action in ("create", "update", "delete")
                and type(item.get("id")) is int and type(item.get("version")) is int
                and (action != "delete" or item.get("deleted") is True)
                and bill.get("id") == item["id"] and isinstance(bill.get("expense_date"), str)
                and isinstance(bill.get("amount"), str)):
            return {
                "ok": True,
                "action": action,
                "item": {
                    "id": item["id"], "version": item["version"],
                    "expense_date": bill["expense_date"], "amount": bill["amount"],
                    **({"deleted": True} if action == "delete" else {}),
                },
            }
    raise BusinessError("bill_receipt_not_found", "未查到该请求的账单提交回执", 404)


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


def _load_existing_origins(db: Session, source_keys: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for start in range(0, len(source_keys), 400):
        chunk = source_keys[start:start + 400]
        rows = db.execute(
            select(AssistantBillOrigin.source_key, AssistantBillOrigin.row_hash)
            .where(AssistantBillOrigin.source_key.in_(chunk))
        ).all()
        for source_key, row_hash in rows:
            found[source_key] = row_hash
    return found


def _resolve_bill_import_plan(
    db: Session,
    *,
    file_name: str,
    file_sha256: str,
    rows: list[dict],
    category_overrides: dict[str, str],
    prior_origins: dict[str, str] | None = None,
    prior_tags: set[tuple[str | None, str]] | None = None,
) -> dict:
    source_keys = [row["source_key"] for row in rows]
    if len(set(source_keys)) != len(source_keys):
        raise BusinessError("duplicate_import_source_key", "导入明细中存在重复来源键", 422)

    normalized_overrides = {}
    for raw_k, raw_v in category_overrides.items():
        k = raw_k.strip()
        v = raw_v.strip()
        if not k or not v or len(k) > 64 or len(v) > 64:
            raise BusinessError("invalid_fields", "分类映射名称不合法", 422)
        normalized_overrides[k] = v

    existing_origins = _load_existing_origins(db, source_keys)

    insert_rows = []
    skipped_keys = []
    source_expense = Decimal("0.00")
    source_income = Decimal("0.00")
    insert_expense = Decimal("0.00")
    insert_income = Decimal("0.00")

    for row in rows:
        amt = Decimal(row["amount"])
        if row["record_type"] == RecordType.expense.value or row["record_type"] == RecordType.expense:
            source_expense += amt
        else:
            source_income += amt

        prior_hash = existing_origins.get(row["source_key"])
        if prior_hash is None and prior_origins is not None:
            prior_hash = prior_origins.get(row["source_key"])
        if prior_hash is not None:
            if prior_hash != row["row_hash"]:
                raise BusinessError("import_source_changed", "已导入账单记录指纹冲突，请核对源文件", 409)
            skipped_keys.append(row["source_key"])
            continue

        raw_cat = row["category_name"].strip()
        effective_cat = normalized_overrides.get(raw_cat, raw_cat)
        raw_sub = (row.get("subcategory_name") or "").strip()
        effective_sub = None if not raw_sub or raw_sub == effective_cat else raw_sub
        if not effective_cat or len(effective_cat) > 64 or (effective_sub and len(effective_sub) > 64):
            raise BusinessError("invalid_fields", "账单分类名称长度不合法", 422)

        if row["record_type"] == RecordType.expense.value or row["record_type"] == RecordType.expense:
            insert_expense += amt
        else:
            insert_income += amt

        insert_rows.append({
            **row,
            "effective_cat": effective_cat,
            "effective_sub": effective_sub,
        })

    all_tags = db.scalars(
        select(Tag)
        .where(Tag.type.in_([TagType.category, TagType.subcategory]))
        .order_by(Tag.sort_order, Tag.id)
    ).all()
    existing_categories = {t.name: t for t in all_tags if t.type == TagType.category}
    existing_subcategories = {(t.parent_id, t.name): t for t in all_tags if t.type == TagType.subcategory}
    tag_snapshot = hashlib.sha256(
        canonical([[t.id, t.name, t.type.value, t.parent_id] for t in all_tags]).encode()
    ).hexdigest()

    planned_new_tags = []
    pending_tags = set() if prior_tags is None else prior_tags
    for row in insert_rows:
        cat_name = row["effective_cat"]
        sub_name = row["effective_sub"]
        cat_obj = existing_categories.get(cat_name)
        if cat_obj is None and (None, cat_name) not in pending_tags:
            pending_tags.add((None, cat_name))
            planned_new_tags.append({"type": "category", "name": cat_name, "parent_name": None})
        if sub_name is not None:
            has_existing_sub = cat_obj is not None and (cat_obj.id, sub_name) in existing_subcategories
            if not has_existing_sub and (cat_name, sub_name) not in pending_tags:
                pending_tags.add((cat_name, sub_name))
                planned_new_tags.append({"type": "subcategory", "name": sub_name, "parent_name": cat_name})

    manual_overlap_hints = []
    if insert_rows:
        insert_dates = [datetime.strptime(str(r["expense_date"]), "%Y-%m-%d").date() for r in insert_rows]
        d_min, d_max = min(insert_dates), max(insert_dates)
        insert_signatures = {
            (
                str(r["expense_date"]),
                r["record_type"].value if isinstance(r["record_type"], RecordType) else str(r["record_type"]),
                f"{Decimal(r['amount']):.2f}",
            )
            for r in insert_rows
        }
        imported_bill_ids = select(AssistantBillOrigin.bill_id).where(AssistantBillOrigin.bill_id.is_not(None))
        candidates = db.scalars(
            select(Bill)
            .where(
                Bill.expense_date >= d_min,
                Bill.expense_date <= d_max,
                Bill.id.not_in(imported_bill_ids),
            )
            .order_by(Bill.expense_date.asc(), Bill.id.asc())
        ).all()
        for b in candidates:
            sig = (b.expense_date.isoformat(), b.record_type.value, f"{b.amount:.2f}")
            if sig in insert_signatures:
                manual_overlap_hints.append({
                    "bill_id": b.id,
                    "expense_date": sig[0],
                    "record_type": sig[1],
                    "amount": sig[2],
                })
                if len(manual_overlap_hints) >= 20:
                    break

    all_dates = [str(r["expense_date"]) for r in rows]
    date_from = min(all_dates, default=None)
    date_to = max(all_dates, default=None)

    preview_hash = hashlib.sha256(
        canonical({
            "file_sha256": file_sha256,
            "inserts": [
                [r["source_key"], r["row_hash"], r["effective_cat"], r["effective_sub"]]
                for r in insert_rows
            ],
            "skipped": skipped_keys,
            "planned_new_tags": planned_new_tags,
            "category_overrides": normalized_overrides,
            "tag_snapshot": tag_snapshot,
        }).encode()
    ).hexdigest()

    return {
        "file_name": file_name,
        "file_sha256": file_sha256,
        "total_rows": len(rows),
        "insert_count": len(insert_rows),
        "skipped_count": len(skipped_keys),
        "total_expense": f"{insert_expense:.2f}",
        "total_income": f"{insert_income:.2f}",
        "source_total_expense": f"{source_expense:.2f}",
        "source_total_income": f"{source_income:.2f}",
        "date_from": date_from,
        "date_to": date_to,
        "planned_new_tags": planned_new_tags,
        "manual_overlap_hints": manual_overlap_hints,
        "preview_hash": preview_hash,
        "_insert_rows": insert_rows,
        "_existing_categories": existing_categories,
        "_existing_subcategories": existing_subcategories,
    }


def _bill_import_preview(plan: dict) -> dict:
    return {
        "ok": True,
        "file_name": plan["file_name"],
        "file_sha256": plan["file_sha256"],
        "total_rows": plan["total_rows"],
        "insert_count": plan["insert_count"],
        "skipped_count": plan["skipped_count"],
        "total_expense": plan["total_expense"],
        "total_income": plan["total_income"],
        "source_total_expense": plan["source_total_expense"],
        "source_total_income": plan["source_total_income"],
        "date_from": plan["date_from"],
        "date_to": plan["date_to"],
        "planned_new_tags": plan["planned_new_tags"],
        "manual_overlap_hints": plan["manual_overlap_hints"],
        "preview_hash": plan["preview_hash"],
    }


def preview_bill_import(db: Session, *, file_name: str, file_sha256: str, rows: list[dict], category_overrides: dict[str, str]) -> dict:
    return _bill_import_preview(_resolve_bill_import_plan(
        db, file_name=file_name, file_sha256=file_sha256, rows=rows, category_overrides=category_overrides,
    ))


def _write_bill_import_plan(db: Session, plan: dict, key: str, run_id: str,
                            categories: dict, subcategories: dict) -> dict:
    file_name, file_sha256 = plan["file_name"], plan["file_sha256"]

    max_cat_order = db.scalar(select(func.coalesce(func.max(Tag.sort_order), 0)).where(Tag.type == TagType.category)) or 0
    for item in plan["planned_new_tags"]:
        if item["type"] == "category":
            max_cat_order += 1
            tag = Tag(name=item["name"], type=TagType.category, sort_order=max_cat_order)
            db.add(tag)
            categories[item["name"]] = tag
    db.flush()

    for item in plan["planned_new_tags"]:
        if item["type"] == "subcategory":
            parent = categories[item["parent_name"]]
            max_sub_order = db.scalar(
                select(func.coalesce(func.max(Tag.sort_order), 0))
                .where(Tag.type == TagType.subcategory, Tag.parent_id == parent.id)
            ) or 0
            sub = Tag(
                name=item["name"],
                type=TagType.subcategory,
                parent_id=parent.id,
                sort_order=max_sub_order + 1,
            )
            db.add(sub)
            subcategories[(parent.id, item["name"])] = sub
    db.flush()

    validated_pairs: set[tuple[int, int | None]] = set()
    bill_objs: list[Bill] = []
    insert_rows = plan["_insert_rows"]
    for row in insert_rows:
        cat_id = categories[row["effective_cat"]].id
        sub_id = subcategories[(cat_id, row["effective_sub"])].id if row["effective_sub"] else None
        if (cat_id, sub_id) not in validated_pairs:
            validate_bill_tags(db, {"category_id": cat_id, "subcategory_id": sub_id})
            validated_pairs.add((cat_id, sub_id))
        bill_objs.append(
            Bill(
                record_type=RecordType(row["record_type"]),
                expense_date=datetime.strptime(str(row["expense_date"]), "%Y-%m-%d").date(),
                expense_time=datetime.strptime(str(row["expense_time"]), "%H:%M:%S").time() if row.get("expense_time") else None,
                amount=Decimal(row["amount"]),
                category_id=cat_id,
                subcategory_id=sub_id,
                reimbursement_status=ReimbursementStatus.na,
                note=row.get("note"),
            )
        )

    batch_id = "batch_" + uuid4().hex[:24]
    batch = AssistantBillImportBatch(
        batch_id=batch_id,
        source_type="xlsx-v1",
        file_sha256=file_sha256,
        file_name=file_name,
        total_rows=plan["total_rows"],
        inserted_count=plan["insert_count"],
        skipped_count=plan["skipped_count"],
        created_tags_json=canonical(plan["planned_new_tags"]),
        request_key=key,
        run_id=run_id or "",
    )
    db.add(batch)
    db.add_all(bill_objs)
    db.flush()

    origins = [
        AssistantBillOrigin(
            source_key=row["source_key"],
            batch_id=batch_id,
            bill_id=bill.id,
            row_hash=row["row_hash"],
            source_json=canonical({
                "expense_date": str(row["expense_date"]),
                "expense_time": row.get("expense_time"),
                "record_type": row["record_type"],
                "amount": row["amount"],
                "category_name": row["effective_cat"],
                "subcategory_name": row["effective_sub"],
            }),
        )
        for row, bill in zip(insert_rows, bill_objs)
    ]
    db.add_all(origins)
    db.flush()

    return {
        "ok": True,
        "action": "import",
        "batch_id": batch_id,
        "file_name": file_name,
        "file_sha256": file_sha256,
        "total_rows": plan["total_rows"],
        "inserted_count": plan["insert_count"],
        "skipped_count": plan["skipped_count"],
        "total_expense": plan["total_expense"],
        "total_income": plan["total_income"],
        "created_tags": plan["planned_new_tags"],
        "date_from": plan["date_from"],
        "date_to": plan["date_to"],
    }


def commit_bill_import(
    db: Session,
    *,
    key: str,
    run_id: str,
    file_name: str,
    file_sha256: str,
    rows: list[dict],
    category_overrides: dict[str, str],
    expected_preview_hash: str,
) -> dict:
    payload = {
        "file_name": file_name,
        "file_sha256": file_sha256,
        "rows": rows,
        "category_overrides": category_overrides,
        "expected_preview_hash": expected_preview_hash,
    }

    def work() -> dict:
        plan = _resolve_bill_import_plan(
            db,
            file_name=file_name,
            file_sha256=file_sha256,
            rows=rows,
            category_overrides=category_overrides,
        )
        if plan["preview_hash"] != expected_preview_hash:
            raise BusinessError("import_preview_stale", "账单或分类目录在确认前已变化，请重新预览", 409)
        if plan["insert_count"] == 0:
            raise BusinessError("no_new_bills_to_import", "所有账单均已导入，无需重复写入", 422)

        return _write_bill_import_plan(db, plan, key, run_id,
                                       plan["_existing_categories"], plan["_existing_subcategories"])

    return write_once(db, key, "bills-import", payload, work, run_id)


def _plan_bill_import_group(db: Session, files: list[dict]) -> tuple[list[dict], str]:
    if sum(len(file["rows"]) for file in files) > 5000:
        raise BusinessError("too_many_import_rows", "一组账单最多包含 5000 条有效记录", 422)
    origins: dict[str, str] = {}
    tags: set[tuple[str | None, str]] = set()
    plans = []
    for file in files:
        # Simulate the preceding files without creating tags or writing bills.
        plan = _resolve_bill_import_plan(db, **file, prior_origins=origins, prior_tags=tags)
        origins.update((row["source_key"], row["row_hash"]) for row in plan["_insert_rows"])
        plans.append(plan)
    fingerprint = hashlib.sha256(canonical([
        [plan["file_name"], plan["preview_hash"], plan["manual_overlap_hints"]]
        for plan in plans
    ]).encode()).hexdigest()
    return plans, fingerprint


def _group_totals(plans: list[dict]) -> dict:
    return {
        "total_rows": sum(plan["total_rows"] for plan in plans),
        "skipped_count": sum(plan["skipped_count"] for plan in plans),
        "total_expense": f"{sum(Decimal(plan['total_expense']) for plan in plans):.2f}",
        "total_income": f"{sum(Decimal(plan['total_income']) for plan in plans):.2f}",
        "date_from": min((plan["date_from"] for plan in plans if plan["date_from"]), default=None),
        "date_to": max((plan["date_to"] for plan in plans if plan["date_to"]), default=None),
    }


def preview_bill_import_group(db: Session, files: list[dict]) -> dict:
    plans, fingerprint = _plan_bill_import_group(db, files)
    return {
        "ok": True,
        "preview_hash": fingerprint,
        "files": [_bill_import_preview(plan) for plan in plans],
        "insert_count": sum(plan["insert_count"] for plan in plans),
        **_group_totals(plans),
    }


def commit_bill_import_group(db: Session, *, key: str, run_id: str, files: list[dict],
                             expected_preview_hash: str) -> dict:
    def work() -> dict:
        plans, fingerprint = _plan_bill_import_group(db, files)
        if fingerprint != expected_preview_hash:
            raise BusinessError("import_preview_stale", "账单或分类目录在确认前已变化，请重新预览", 409)
        inserted_count = sum(plan["insert_count"] for plan in plans)
        if inserted_count == 0:
            raise BusinessError("no_new_bills_to_import", "所有账单均已导入或无需写入", 422)

        categories = plans[0]["_existing_categories"]
        subcategories = plans[0]["_existing_subcategories"]
        results = []
        group_key = hashlib.sha256(key.encode()).hexdigest()
        for index, plan in enumerate(plans, start=1):
            if plan["insert_count"]:
                result = _write_bill_import_plan(
                    db, plan, f"bills-import-group:{group_key}:{index}", run_id, categories, subcategories,
                )
            else:
                result = {
                    "file_name": plan["file_name"],
                    "batch_id": None,
                    "inserted_count": 0,
                    "created_tags": [],
                    **_group_totals([plan]),
                }
            results.append(result)
        return {
            "ok": True,
            "action": "import_group",
            "inserted_count": inserted_count,
            "files": results,
            **_group_totals(plans),
        }

    # One durable receipt and one transaction for the entire ordered group.
    payload = {"files": files, "expected_preview_hash": expected_preview_hash}
    return write_once(db, key, "bills-import-group", payload, work, run_id)


def read_bill_import_group_receipt(db: Session, key: str) -> dict:
    row = db.get(AssistantRequest, key)
    result = json.loads(row.result_json) if row else {}
    if result.get("ok") is True and result.get("action") == "import_group":
        return result
    raise BusinessError("bill_import_receipt_not_found", "未查到该组账单提交回执", 404)


def list_bill_import_batches(
    db: Session,
    *,
    batch_id: str | None = None,
    request_key: str | None = None,
    limit: int = 20,
) -> list[dict]:
    stmt = select(AssistantBillImportBatch)
    if batch_id:
        stmt = stmt.where(AssistantBillImportBatch.batch_id == batch_id)
    if request_key:
        stmt = stmt.where(AssistantBillImportBatch.request_key == request_key)
    rows = db.scalars(stmt.order_by(AssistantBillImportBatch.created_at.desc(), AssistantBillImportBatch.batch_id.desc()).limit(limit)).all()
    return [
        {
            "batch_id": b.batch_id,
            "source_type": b.source_type,
            "file_sha256": b.file_sha256,
            "file_name": b.file_name,
            "total_rows": b.total_rows,
            "inserted_count": b.inserted_count,
            "skipped_count": b.skipped_count,
            "created_tags": json.loads(b.created_tags_json),
            "request_key": b.request_key,
            "run_id": b.run_id,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in rows
    ]
