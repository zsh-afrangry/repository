"""Atomic topic writes with optimistic concurrency; shared MySQL engine/session."""
import json
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from app.database import get_db
from .aggregates import topic_counts
from .models import NoteTopic, NotesSeed
from .schemas import TopicData, TopicUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


def seed_notes(db: Session):
    if db.get(NotesSeed, "legacy-v1"):
        return
    for raw in json.loads(Path(__file__).with_name("seed.json").read_text(encoding="utf-8")):
        topic_id = raw.pop("id")
        data = TopicData.model_validate(raw).model_dump()
        if db.get(NoteTopic, topic_id) is None:
            db.add(NoteTopic(id=topic_id, version=1, data=data))
    db.add(NotesSeed(id="legacy-v1"))
    db.commit()


def topic_or_404(db, topic_id):
    topic = db.get(NoteTopic, topic_id)
    if not topic:
        raise HTTPException(404, "主题不存在")
    return topic


def output(topic):
    return {"id": topic.id, "version": topic.version, **topic.data}


@router.get("/topics")
def list_topics(db: Session = Depends(get_db)):
    rows = db.scalars(select(NoteTopic)).all()
    # 计数走 aggregates.topic_counts()，与首页统计卡共用同一份实现，
    # 避免"主题列表显示 5 个单元、首页显示别的数"这类口径漂移。
    return sorted([{
        "id": r.id, "version": r.version, "title": r.data["title"],
        "description": r.data["description"], "sortOrder": r.data["sortOrder"],
        **topic_counts(r.data),
    } for r in rows], key=lambda t: (t["sortOrder"], t["id"]))


@router.post("/topics", status_code=201)
def create_topic(data: TopicData, db: Session = Depends(get_db)):
    topic = NoteTopic(id=str(uuid4()), version=1, data=data.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return output(topic)


@router.get("/topics/{topic_id}")
def read_topic(topic_id: str, db: Session = Depends(get_db)):
    return output(topic_or_404(db, topic_id))


@router.put("/topics/{topic_id}")
def save_topic(topic_id: str, data: TopicUpdate, db: Session = Depends(get_db)):
    current = topic_or_404(db, topic_id)
    payload = data.model_dump(exclude={"version"})
    # Reject removing nonempty directories even if a malformed client also drops units.
    removed_sections = {s["id"] for s in current.data["sections"]} - {s["id"] for s in payload["sections"]}
    remaining = {u["id"]: u for u in payload["units"]}
    if any(u["sectionId"] in removed_sections and u["id"] not in remaining for u in current.data["units"]):
        raise HTTPException(409, "请先迁移或单独删除目录内的单元，再删除目录")
    result = db.execute(update(NoteTopic).where(NoteTopic.id == topic_id, NoteTopic.version == data.version)
                        .values(data=payload, version=data.version + 1).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "主题已被其他窗口修改。请保留草稿并重新载入后重试")
    db.commit()
    db.expire_all()
    return output(topic_or_404(db, topic_id))


@router.delete("/topics/{topic_id}", status_code=204)
def delete_topic(topic_id: str, version: int = Query(ge=1), db: Session = Depends(get_db)):
    topic = topic_or_404(db, topic_id)
    if topic.data["sections"] or topic.data["units"]:
        raise HTTPException(409, "主题非空，请先迁移单元并移除空目录")
    result = db.execute(delete(NoteTopic).where(NoteTopic.id == topic_id, NoteTopic.version == version)
                        .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "主题已变化，请刷新后重试")
    db.commit()
