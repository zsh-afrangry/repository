from fastapi import APIRouter

from app.tradesim.api.v1 import ai, records, simulate


router = APIRouter()
router.include_router(simulate.router, prefix="/simulate", tags=["TradeSim 回测引擎"])
router.include_router(records.router, prefix="/records", tags=["TradeSim 回测记录"])
router.include_router(ai.router, prefix="/ai", tags=["TradeSim AI 研判"])

