from datetime import date, datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.tradesim.db.models import SimulationRecord
from app.tradesim.db.session import mongo_collection
from app.tradesim.schemas.record import (
    RecordBriefResponse,
    RecordDetailResponse,
    SaveRecordRequest,
)


router = APIRouter()


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"日期格式无效: {value}") from exc


@router.post("/save-favorite", summary="持久化并收藏该次成功的组合与参数", response_model=dict)
async def save_record(
    payload: SaveRecordRequest,
    db: Session = Depends(get_db),
):
    """Save lightweight indexes in MySQL and large arrays in MongoDB."""
    mongo_id = None
    try:
        large_doc = {
            "equity_curve": [item.model_dump() for item in payload.response.equity_curve],
            "execution_records": [item.model_dump() for item in payload.response.execution_records],
            "saved_at_node": datetime.now().isoformat(),
        }
        mongo_result = await mongo_collection.insert_one(large_doc)
        mongo_id = str(mongo_result.inserted_id)

        db_record = SimulationRecord(
            mongo_log_id=mongo_id,
            strategy_name=payload.request.strategy_name,
            symbol=payload.request.symbol,
            start_date=_parse_date(payload.request.start_date),
            end_date=_parse_date(payload.request.end_date),
            data_frequency=payload.request.data_frequency,
            strategy_params=payload.request.strategy_params,
            total_return=payload.response.metrics.total_return,
            annualized_return=payload.response.metrics.annualized_return,
            max_drawdown=payload.response.metrics.max_drawdown,
            win_rate=payload.response.metrics.win_rate,
            total_trades=payload.response.metrics.total_trades,
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        return {"message": "存证成功！", "record_id": db_record.id, "log_id": mongo_id}
    except HTTPException:
        db.rollback()
        if mongo_id and ObjectId.is_valid(mongo_id):
            await mongo_collection.delete_one({"_id": ObjectId(mongo_id)})
        raise
    except Exception as exc:
        db.rollback()
        if mongo_id and ObjectId.is_valid(mongo_id):
            await mongo_collection.delete_one({"_id": ObjectId(mongo_id)})
        raise HTTPException(status_code=500, detail="TradeSim 存储层写入异常") from exc


@router.get(
    "/list",
    summary="查阅所有已收藏的回测（极速返回轻对象）",
    response_model=List[RecordBriefResponse],
)
def get_favorites(db: Session = Depends(get_db)):
    records = (
        db.query(SimulationRecord)
        .order_by(SimulationRecord.total_return.desc())
        .limit(100)
        .all()
    )
    return [
        RecordBriefResponse(
            id=record.id,
            symbol=record.symbol,
            strategy_name=record.strategy_name,
            total_return=float(record.total_return),
            max_drawdown=float(record.max_drawdown),
            win_rate=float(record.win_rate),
            total_trades=record.total_trades,
            created_at=(
                record.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if record.created_at
                else ""
            ),
            data_frequency=getattr(record, "data_frequency", "daily") or "daily",
        )
        for record in records
    ]


@router.get(
    "/detail/{record_id}",
    summary="联表查询某次跑分详情图表数据",
    response_model=RecordDetailResponse,
)
async def get_record_detail(
    record_id: int,
    db: Session = Depends(get_db),
):
    record = (
        db.query(SimulationRecord)
        .filter(SimulationRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="未找到该回测记录")
    if not record.mongo_log_id or not ObjectId.is_valid(record.mongo_log_id):
        raise HTTPException(status_code=500, detail="数据撕裂，详情凭证已遗失")

    log_doc = await mongo_collection.find_one({"_id": ObjectId(record.mongo_log_id)})
    if not log_doc:
        raise HTTPException(status_code=404, detail="MongoDB 大对象已被清理或不存在")

    return RecordDetailResponse(
        id=record.id,
        symbol=record.symbol,
        strategy_name=record.strategy_name,
        total_return=float(record.total_return),
        max_drawdown=float(record.max_drawdown),
        win_rate=float(record.win_rate),
        total_trades=record.total_trades,
        created_at=(
            record.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if record.created_at
            else ""
        ),
        data_frequency=getattr(record, "data_frequency", "daily") or "daily",
        start_date=record.start_date.strftime("%Y-%m-%d"),
        end_date=record.end_date.strftime("%Y-%m-%d"),
        strategy_params=record.strategy_params or {},
        equity_curve=log_doc.get("equity_curve", []),
        execution_records=log_doc.get("execution_records", []),
    )
